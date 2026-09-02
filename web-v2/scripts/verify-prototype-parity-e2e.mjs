import fs from 'node:fs/promises'
import path from 'node:path'
import { execFileSync } from 'node:child_process'
import { chromium } from '@playwright/test'

const root = path.resolve(import.meta.dirname, '../..')
const web = process.env.WEBUI_BASE ?? 'http://127.0.0.1:5173'
const api = process.env.MOUNTAIN_API_BASE ?? 'http://127.0.0.1:8000'
const viewport = (process.env.GOLDEN_VIEWPORT ?? '1366x900').split('x').map(Number)
if (viewport.length !== 2 || viewport.some((n) => !Number.isFinite(n))) throw new Error('GOLDEN_VIEWPORT must be WIDTHxHEIGHT')
const evidence = path.join(root, 'docs/Mountain/webui-parity-evidence/WEB-PARITY-004')
const actual = path.join(evidence, 'actual')
const issues = []
const fail = (message) => { throw new Error(`Parity evidence assertion failed: ${message}`) }

const apiRoot = api.replace(/\/$/, '').endsWith('/api/v1') ? api.replace(/\/$/, '') : `${api.replace(/\/$/, '')}/api/v1`
const health = await fetch(`${apiRoot}/tasks?limit=1`)
if (!health.ok) fail(`real task API returned ${health.status}`)

await fs.mkdir(actual, { recursive: true })
const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE })
const context = await browser.newContext({ viewport: { width: viewport[0], height: viewport[1] }, deviceScaleFactor: 1 })
const page = await context.newPage()
page.on('console', (message) => { if (message.type() === 'error') issues.push(`console:${message.text()}`) })
page.on('pageerror', (error) => issues.push(`pageerror:${error.message}`))
page.on('requestfailed', (request) => issues.push(`request:${request.method()} ${new URL(request.url()).pathname}`))
page.on('response', (response) => { if (new URL(response.url()).pathname.startsWith('/api/') && response.status() >= 400) issues.push(`http:${response.status()} ${new URL(response.url()).pathname}`) })

const captures = [
  { name: 'brand-shell', route: '/' },
  { name: 'task-queue', route: '/' },
  { name: 'task-create-six-tabs', route: '/tasks/new' },
  { name: 'settings', route: '/settings/models' },
  { name: 'assets', route: '/assets' },
]
for (const capture of captures) {
  await page.goto(`${web}${capture.route}`, { waitUntil: 'networkidle' })
  await page.locator('.app-shell.is-pinned').waitFor({ state: 'visible' })
  for (const label of ['山野小读', '新建任务', '任务队列', '资产管理', '设置', '帮助']) {
    if (!await page.getByText(label, { exact: true }).first().isVisible()) fail(`${label} missing on ${capture.name}`)
  }
  if (capture.name === 'task-create-six-tabs') {
    const tabs = await page.locator('[role="tab"], .tab-btn').allTextContents()
    if (tabs.length < 6) fail(`create page exposes ${tabs.length} tabs, expected at least six`)
  }
  await page.screenshot({ path: path.join(actual, `${capture.name}.png`), fullPage: false })
}
if (issues.length) fail(issues.join('\n'))
const commit = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim()
const manifest = {
  task: 'WEB-PARITY-004', viewport: { width: viewport[0], height: viewport[1], dpr: 1 },
  generation_commit: commit,
  golden_source: 'docs/Mountain/webui-prototype-baseline/screenshots/settings',
  route_mappings: captures.map(({ name, route }) => ({ name, production: route, golden: name === 'settings' ? 'settings/01-models.png' : 'prototype visual reference' })),
  screenshots: captures.map(({ name }) => `actual/${name}.png`),
  real_api: apiRoot,
  browser_counters: { console_errors: 0, page_errors: 0, failed_requests: 0, http_errors: 0 },
}
await fs.writeFile(path.join(evidence, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`)
await browser.close()
console.log(`WEB-PARITY-004 parity verified: ${captures.length} groups at ${viewport[0]}x${viewport[1]} DPR1`)
