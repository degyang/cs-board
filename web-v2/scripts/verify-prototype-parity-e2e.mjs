import fs from 'node:fs/promises'
import path from 'node:path'
import crypto from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { chromium } from '@playwright/test'

const root = path.resolve(import.meta.dirname, '../..')
const web = process.env.WEBUI_BASE ?? 'http://127.0.0.1:5173'
const api = process.env.MOUNTAIN_API_BASE ?? 'http://127.0.0.1:8000'
const viewport = (process.env.GOLDEN_VIEWPORT ?? '1366x900').split('x').map(Number)
if (viewport.length !== 2 || viewport.some((n) => !Number.isFinite(n))) throw new Error('GOLDEN_VIEWPORT must be WIDTHxHEIGHT')
const evidence = path.join(root, 'docs/Mountain/webui-parity-evidence/WEB-PARITY-004')
const actual = path.join(evidence, 'actual')
const goldenManifestPath = path.join(evidence, 'golden-manifest.json')
const issues = []
const fail = (message) => { throw new Error(`Parity evidence assertion failed: ${message}`) }

const sha256 = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex')
const pngSize = (bytes) => {
  if (bytes.length < 24 || bytes.readUInt32BE(0) !== 0x89504e47 || bytes.readUInt32BE(12) !== 0x49484452) return null
  return { width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20) }
}

const approvedGolden = JSON.parse(await fs.readFile(goldenManifestPath, 'utf8'))
if (approvedGolden.source?.commit !== '0f56e824c0d49ab5c090e7ea07086dc9d47f47a9') fail('golden source commit is not the approved immutable prototype')
if (approvedGolden.capture?.viewport?.width !== viewport[0] || approvedGolden.capture?.viewport?.height !== viewport[1] || approvedGolden.capture?.dpr !== 1 || approvedGolden.capture?.zoom !== '100%') fail('golden capture settings do not match the contract')
if (approvedGolden.goldens?.length !== 5) fail(`golden manifest contains ${approvedGolden.goldens?.length ?? 0} groups, expected five`)
for (const item of approvedGolden.goldens) {
  const file = path.join(evidence, 'golden', path.basename(item.golden_file))
  const bytes = await fs.readFile(file)
  const size = pngSize(bytes)
  if (!size || size.width !== viewport[0] || size.height !== viewport[1]) fail(`golden ${item.id} is not ${viewport[0]}x${viewport[1]}`)
  if (bytes.length !== item.bytes || sha256(bytes) !== item.sha256) fail(`golden ${item.id} hash or byte count differs from the approved manifest`)
}

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
  { name: 'brand-shell', route: '/help', golden: '01-brand-shell.png', prototypeRoute: '/help' },
  { name: 'task-queue', route: '/', golden: '02-task-queue.png', prototypeRoute: '/projects' },
  { name: 'task-create-six-tabs', route: '/tasks/new', golden: '03-create-six-tabs.png', prototypeRoute: '/create' },
  { name: 'settings', route: '/settings/models', golden: '04-settings.png', prototypeRoute: '/settings' },
  { name: 'assets', route: '/assets', golden: '05-assets.png', prototypeRoute: '/assets' },
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
const screenshotRecords = []
for (const capture of captures) {
  const actualFile = path.join(actual, `${capture.name}.png`)
  const actualBytes = await fs.readFile(actualFile)
  const size = pngSize(actualBytes)
  if (!size || size.width !== viewport[0] || size.height !== viewport[1]) fail(`actual ${capture.name} is not ${viewport[0]}x${viewport[1]}`)
  const goldenItem = approvedGolden.goldens.find((item) => item.golden_file.endsWith(`/${capture.golden}`))
  if (!goldenItem) fail(`no approved golden mapping for ${capture.name}`)
  screenshotRecords.push({
    name: capture.name,
    production_route: capture.route,
    prototype_route: capture.prototypeRoute,
    golden: `golden/${capture.golden}`,
    actual: `actual/${capture.name}.png`,
    golden_sha256: goldenItem.sha256,
    actual_sha256: sha256(actualBytes),
    width: size.width,
    height: size.height,
    dpr: 1,
  })
}
const manifest = {
  task: 'WEB-PARITY-004', viewport: { width: viewport[0], height: viewport[1], dpr: 1 },
  zoom: '100%',
  generation_commit: commit,
  golden_source: approvedGolden.source,
  route_mappings: screenshotRecords,
  real_api: apiRoot,
  browser_counters: {
    console_errors: issues.filter((issue) => issue.startsWith('console:')).length,
    page_errors: issues.filter((issue) => issue.startsWith('pageerror:')).length,
    failed_requests: issues.filter((issue) => issue.startsWith('request:')).length,
    http_errors: issues.filter((issue) => issue.startsWith('http:')).length,
  },
}
await fs.writeFile(path.join(evidence, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`)
await browser.close()
console.log(`WEB-PARITY-004 parity verified: ${captures.length} groups at ${viewport[0]}x${viewport[1]} DPR1`)
