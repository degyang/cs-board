import fs from 'node:fs/promises'
import path from 'node:path'
import { chromium } from '@playwright/test'

const root = path.resolve(import.meta.dirname, '../..')
const evidence = path.join(root, 'docs/Mountain/webui-parity-evidence')
const web = process.env.WEBUI_BASE ?? 'http://127.0.0.1:5173'
const api = process.env.MOUNTAIN_API_BASE ?? 'http://127.0.0.1:8000'
const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE
const consoleIssues = []
const requestIssues = []
const browser = await chromium.launch({ headless: true, executablePath })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 })
page.on('console', message => { if (['error', 'warning'].includes(message.type())) consoleIssues.push(`${message.type()}: ${message.text()}`) })
page.on('pageerror', error => consoleIssues.push(`exception: ${error.message}`))
page.on('requestfailed', request => requestIssues.push(`${request.method()} ${request.url()} — ${request.failure()?.errorText ?? 'failed'}`))
// Detect API responses — both direct (url starts with api) and proxied (url contains /api/v1/)
page.on('response', response => {
  const url = response.url()
  const isApi = url.startsWith(api) || url.includes('/api/v1/')
  if (isApi && response.status() >= 400) requestIssues.push(`${response.status()} ${response.request().method()} ${url}`)
})

const services = await (await fetch(`${api}/api/v1/services?limit=1`)).json()
const serviceId = services.items[0]?.service_id
if (!serviceId) throw new Error('Real backend returned no model service for detail evidence')
const shots = [
  ['/settings/models', 'settings/models-list.png'],
  ['/settings/models/new', 'settings/models-create.png'],
  [`/settings/models/${serviceId}`, 'settings/models-detail.png'],
  [`/settings/models/${serviceId}/edit`, 'settings/models-edit.png'],
  ['/settings/voice-alignment', 'settings/voice-alignment.png'],
  ['/settings/toolchain', 'settings/toolchain.png'],
  ['/settings/storage', 'settings/storage.png'],
  ['/settings/diagnostics', 'settings/diagnostics.png'],
  ['/assets', 'assets/preset.png'],
  ['/assets', 'assets/custom.png', '自定义风格'],
  ['/assets', 'assets/voices.png', '音色库'],
]
await fs.mkdir(path.join(evidence, 'settings'), { recursive: true })
await fs.mkdir(path.join(evidence, 'assets'), { recursive: true })
for (const [route, file, tab] of shots) {
  await page.goto(web + route, { waitUntil: 'networkidle' })
  if (tab) await page.getByRole('tab', { name: tab }).click()
  await page.waitForLoadState('networkidle')
  // For asset pages, click the first list item to show detail panel
  if (file.startsWith('assets/')) {
    const firstItem = page.locator('.am-item').first()
    if (await firstItem.isVisible({ timeout: 2000 }).catch(() => false)) {
      await firstItem.click()
      await page.waitForTimeout(300)
    }
  }
  await page.screenshot({ path: path.join(evidence, file), fullPage: false })
}
await browser.close()
if (consoleIssues.length || requestIssues.length) {
  console.error(JSON.stringify({ consoleIssues, requestIssues }, null, 2))
  process.exit(1)
}
console.log(`Captured ${shots.length} real-backend screenshots; console errors/warnings: 0; failed API requests: 0`)
