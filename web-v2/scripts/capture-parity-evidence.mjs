import fs from 'node:fs/promises'
import path from 'node:path'
import { chromium } from '@playwright/test'
import { waitForAssetTerminal } from './capture-parity-evidence-helpers.mjs'

const root = path.resolve(import.meta.dirname, '../..')
const evidence = path.join(root, 'docs/Mountain/webui-parity-evidence')
const web = process.env.WEBUI_BASE ?? 'http://127.0.0.1:5173'
const api = process.env.MOUNTAIN_API_BASE ?? 'http://127.0.0.1:8000'
const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE
const consoleIssues = []
const requestIssues = []
const fail = (message) => { throw new Error(`Evidence assertion failed: ${message}`) }

const browser = await chromium.launch({ headless: true, executablePath })
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 })
// The first navigation must prove the app default, never reuse a developer's rail preference.
await context.addInitScript(() => localStorage.clear())
const page = await context.newPage()
page.on('console', message => { if (['error', 'warning'].includes(message.type())) consoleIssues.push(`${message.type()}: ${message.text()}`) })
page.on('pageerror', error => consoleIssues.push(`exception: ${error.message}`))
page.on('requestfailed', request => requestIssues.push(`${request.method()} ${request.url()} — ${request.failure()?.errorText ?? 'failed'}`))
page.on('response', response => {
  const url = new URL(response.url())
  if (url.pathname.startsWith('/api/') && response.status() >= 400) requestIssues.push(`${response.status()} ${response.request().method()} ${response.url()}`)
})

const response = await fetch(`${api}/api/v1/services?limit=100`)
if (!response.ok) fail(`service list returned ${response.status}`)
const services = await response.json()
const serviceId = services.items.find((service) => service.service_id === 'openai-compatible-text')?.service_id
if (!serviceId) fail('real backend does not contain openai-compatible-text')

const shots = [
  ['/settings/models', 'settings/models-list.png'],
  ['/settings/models/new', 'settings/models-create.png'],
  [`/settings/models/${serviceId}`, 'settings/models-detail.png'],
  [`/settings/models/${serviceId}`, 'settings/models-secret.png', null, 'Secret 管理'],
  [`/settings/models/${serviceId}/edit`, 'settings/models-edit.png'],
  ['/settings/voice-alignment', 'settings/voice-alignment.png'],
  ['/settings/toolchain', 'settings/toolchain.png'],
  ['/settings/storage', 'settings/storage.png'],
  ['/settings/diagnostics', 'settings/diagnostics.png'],
  ['/assets', 'assets/preset.png'],
  ['/assets', 'assets/custom.png', '自定义风格'],
  ['/assets', 'assets/voices.png', '音色库'],
  ['/', 'tasks/queue-mixed.png'],
  ['/', 'tasks/queue-filtered.png', '失败'],
  ['/', 'tasks/queue-empty.png', '待执行'],
  ['/tasks/new', 'tasks/create-intro.png'],
  ['/tasks/new', 'tasks/create-script.png', '视频文案'],
  ['/tasks/new', 'tasks/create-voice.png', '声音生成'],
  ['/tasks/new', 'tasks/create-visual.png', '视觉设置'],
  ['/tasks/new', 'tasks/create-final.png', '成片设置'],
  ['/tasks/new', 'tasks/create-validation.png', '成片设置'],
]
await fs.mkdir(path.join(evidence, 'settings'), { recursive: true })
await fs.mkdir(path.join(evidence, 'assets'), { recursive: true })
await fs.mkdir(path.join(evidence, 'tasks'), { recursive: true })

async function assertShell() {
  if (await page.locator('.app-shell.is-pinned').count() !== 1) fail('default shell is not pinned')
  for (const label of ['山野小读', '任务队列', '新建任务', '资产管理', '设置', '帮助']) {
    if (!await page.locator('.sidebar').getByText(label, { exact: true }).isVisible()) fail(`full sidebar text missing: ${label}`)
  }
}

async function assertReady(route) {
  const initialTaskResponse = route === '/'
    ? page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/tasks', { timeout: 8_000 })
    : null
  await page.goto(web + route, { waitUntil: 'domcontentloaded' })
  await assertShell()
  if (route.startsWith('/settings/')) {
    if (!await page.getByRole('link', { name: '模型服务', exact: true }).isVisible()) fail('settings secondary navigation missing')
    await page.waitForTimeout(300)
    if (await page.locator('.loading:visible, .spinner:visible').count()) fail(`loading remains visible on ${route}`)
    if (!await page.locator('h1').first().isVisible()) fail(`page title missing on ${route}`)
  }
  if (route === '/') {
    // The queue is mounted at /; a /tasks navigation is a workbench route/404.
    await page.locator('.task-list, .empty-state, .error-card').first().waitFor({ timeout: 8_000 })
    if (!(await initialTaskResponse).ok()) fail(`initial task list returned ${(await initialTaskResponse).status()}`)
    if (await page.locator('.loading:visible, .spinner:visible').count()) fail('task queue loading remains visible')
  }
}

for (const [route, file, tab, scrollTo] of shots) {
  console.log(`Capturing ${file}`)
  await assertReady(route)
  if (tab) {
    const tabButton = page.locator('[role="tab"]').filter({ hasText: tab }).first()
    if (await tabButton.count() !== 1) fail(`asset tab missing: ${tab}`)
    const expectedStatus = file === 'tasks/queue-filtered.png' ? 'failed' : file === 'tasks/queue-empty.png' ? 'pending' : null
    const taskResponse = expectedStatus
      ? page.waitForResponse((response) => {
          const url = new URL(response.url())
          return url.pathname === '/api/v1/tasks' && url.searchParams.get('status') === expectedStatus
        }, { timeout: 8_000 })
      : null
    await tabButton.evaluate((element) => (element).click())
    if (taskResponse) {
      const response = await taskResponse
      if (!response.ok()) fail(`task filter ${expectedStatus} returned ${response.status()}`)
      if (!await tabButton.evaluate((element) => element.getAttribute('aria-selected') === 'true')) fail(`task filter ${expectedStatus} is not active`)
    }
    await page.locator('.loading, .spinner').waitFor({ state: 'hidden', timeout: 5_000 }).catch(() => {})
  }
  if (file === 'tasks/create-voice.png') await waitForAssetTerminal(page, 'voice')
  if (file === 'tasks/create-visual.png') await waitForAssetTerminal(page, 'visual')
  if (route === '/tasks/new' && file === 'tasks/create-validation.png') {
    await page.getByRole('button', { name: '创建并保存' }).click()
    if (!await page.locator('[role="alert"]').first().isVisible()) fail('create validation message missing')
  }
  // Scroll to a specific section heading if requested (e.g. "Secret 管理")
  if (scrollTo) {
    const heading = page.locator(`text=${scrollTo}`).first()
    if (await heading.isVisible({ timeout: 2000 }).catch(() => false)) {
      await heading.scrollIntoViewIfNeeded()
      await page.waitForTimeout(200)
    }
  }
  if (file === 'settings/models-list.png') {
    const cards = page.locator('.mp-card')
    if (await cards.count() < 6) fail('models list has fewer than six service cards')
    const columns = await page.locator('.mp-list').evaluate((el) => getComputedStyle(el).gridTemplateColumns.trim().split(/\s+/).length)
    if (columns !== 2) fail(`models grid has ${columns} columns, expected 2`)
  }
  if (file === 'settings/models-detail.png') {
    if (await page.getByText('openai-compatible-text', { exact: true }).count() === 0) fail('detail is not openai-compatible-text')
    if (!await page.getByText('Secret 管理', { exact: true }).isVisible()) fail('detail Secret region missing')
  }
  if (file === 'settings/models-secret.png') {
    // Must show masked secret values or empty password input; must NOT show real API keys
    if (!await page.getByText('Secret 管理', { exact: true }).isVisible()) fail('Secret section not visible in secret screenshot')
    const secretInputs = page.locator('input[type="password"]')
    if (await secretInputs.count() === 0) fail('no password inputs found in Secret section')
    for (let index = 0; index < await secretInputs.count(); index += 1) {
      if (await secretInputs.nth(index).inputValue() !== '') fail('Secret password input is not empty')
    }
    if (/(sk-[A-Za-z0-9]|AKIA[0-9A-Z]{16}|Bearer\s+[A-Za-z0-9])/i.test(await page.locator('body').innerText())) fail('Secret screenshot contains a key-like plaintext value')
  }
  if (file === 'settings/models-edit.png' && !await page.getByText('编辑服务', { exact: true }).isVisible()) fail('edit form title missing')
  if (file === 'tasks/queue-mixed.png') {
    if (!await page.getByRole('heading', { name: '任务队列', exact: true }).isVisible()) fail('task queue title missing')
    if (!await page.getByText('暂无任务', { exact: true }).isVisible() && !await page.locator('.task-card').first().isVisible()) fail('task queue has no terminal list state')
  }
  if (file === 'tasks/queue-filtered.png' && !await page.getByRole('tab', { name: '失败', exact: true }).evaluate((element) => element.getAttribute('aria-selected') === 'true')) fail('failed tab is not active')
  if (file === 'tasks/queue-empty.png') {
    const emptyMsg = page.getByText('暂无任务')
    const filteredMsg = page.getByText('当前筛选下没有任务')
    if (!await emptyMsg.isVisible({ timeout: 3000 }).catch(() => false) && !await filteredMsg.isVisible({ timeout: 1000 }).catch(() => false)) fail('empty state not visible on queue-empty shot')
  }
  if (file === 'assets/preset.png') {
    if (await page.getByRole('tab').count() !== 3) fail('asset tabs are not all visible')
    const first = page.locator('.am-item').first()
    if (await page.locator('.am-item').count() < 13) fail('preset list has fewer than 13 items')
    await first.click()
    if (!await first.evaluate((el) => el.classList.contains('on'))) fail('first preset was not selected')
    const detail = page.locator('.am-detail-name').first()
    if (!await detail.isVisible() || await detail.textContent() === '暂无数据') fail('preset detail is empty')
  } else if (file.startsWith('assets/')) {
    const first = page.locator('.am-item').first()
    if (await page.locator('.am-item').count() > 0) await first.click()
  }
  if (await page.locator('.loading:visible, .spinner:visible').count()) fail(`loading remains before screenshot ${file}`)
  await page.screenshot({ path: path.join(evidence, file), fullPage: false })
}
await context.close()
await browser.close()
if (consoleIssues.length || requestIssues.length) {
  console.error(JSON.stringify({ consoleIssues, requestIssues }, null, 2))
  process.exit(1)
}
console.log(`Captured ${shots.length} real-backend screenshots; console errors/warnings: 0; failed API requests: 0`)
