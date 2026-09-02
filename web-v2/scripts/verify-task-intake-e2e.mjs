import fs from 'node:fs/promises'
import path from 'node:path'
import crypto from 'node:crypto'
import { chromium } from '@playwright/test'

const web = process.env.WEBUI_BASE
const api = process.env.MOUNTAIN_API_BASE
const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE
if (!web || !api) throw new Error('WEBUI_BASE and MOUNTAIN_API_BASE are required')

const root = path.resolve(import.meta.dirname, '../..')
const runtime = path.join(root, '.e2e-runtime')
const evidence = path.join(root, 'docs/Mountain/webui-parity-evidence/tasks')
const script = 'Intake verification text for a Mountain task.'
const scriptHash = crypto.createHash('sha256').update(script).digest('hex')
const title = `Intake verification ${Date.now()}`
const errors = []
const requests = []
const created = []
const fail = (message) => { throw new Error(`Task intake assertion failed: ${message}`) }
await fs.mkdir(evidence, { recursive: true })

async function writeWav(file) {
  const sampleRate = 8_000; const samples = 80
  const body = Buffer.alloc(samples * 2)
  body.writeInt16LE(0, 0)
  const header = Buffer.alloc(44)
  header.write('RIFF', 0); header.writeUInt32LE(36 + body.length, 4); header.write('WAVE', 8)
  header.write('fmt ', 12); header.writeUInt32LE(16, 16); header.writeUInt16LE(1, 20)
  header.writeUInt16LE(1, 22); header.writeUInt32LE(sampleRate, 24); header.writeUInt32LE(sampleRate * 2, 28)
  header.writeUInt16LE(2, 32); header.writeUInt16LE(16, 34); header.write('data', 36); header.writeUInt32LE(body.length, 40)
  await fs.mkdir(runtime, { recursive: true }); await fs.writeFile(file, Buffer.concat([header, body]))
}

async function waitAssetTerminal(page, loadingText, terminalPatterns) {
  const loading = page.getByText(loadingText, { exact: true })
  if (await loading.isVisible().catch(() => false)) await loading.waitFor({ state: 'hidden', timeout: 8_000 })
  const terminal = page.locator('body').getByText(new RegExp(terminalPatterns.join('|')))
  const cards = page.locator('.choice-card:visible')
  if ((await terminal.count() === 0 || !await terminal.first().isVisible()) && await cards.count() === 0) fail(`asset did not reach terminal state: ${loadingText}`)
}

const browser = await chromium.launch({ headless: true, executablePath })
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 })
await context.addInitScript(() => localStorage.clear())
const page = await context.newPage()
page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errors.push(`${m.type()}: ${m.text()}`) })
page.on('pageerror', e => errors.push(`pageerror: ${e.message}`))
page.on('requestfailed', r => errors.push(`requestfailed: ${r.method()} ${r.url()}`))
page.on('response', r => { const u = new URL(r.url()); if (u.pathname.startsWith('/api/') && r.status() >= 400) errors.push(`${r.status()} ${r.request().method()} ${u.pathname}`) })
page.on('request', r => { const u = new URL(r.url()); if (u.pathname.startsWith('/api/')) requests.push(`${r.method()} ${u.pathname}`) })

const wav = path.join(runtime, 'reference.wav')
await writeWav(wav)
await page.goto(`${web}/tasks/new`, { waitUntil: 'domcontentloaded' })
await page.getByLabel('任务名称').fill(title)
await page.getByRole('button', { name: '下一步' }).click()
await page.getByLabel('原始文案').fill(script)
await page.getByRole('button', { name: '下一步' }).click()
await waitAssetTerminal(page, '正在加载音色…', ['暂无可用音色', '音色加载失败，请稍后重试', '可用音色'])
await page.getByLabel('参考音频文件').setInputFiles(wav)
await page.getByRole('button', { name: '下一步' }).click()
await page.getByRole('button', { name: '下一步' }).click()
await waitAssetTerminal(page, '正在加载风格…', ['暂无可用风格，将使用标准白板风格', '风格加载失败，暂不可选择资产', '预置', '自定义'])
await page.getByRole('button', { name: '下一步' }).click()

const createResponse = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/tasks' && r.request().method() === 'POST')
const inputResponsePromise = createResponse.then(async response => {
  const payload = await response.json()
  if (!payload.task_id) fail('create response has no task_id')
  const inputResponse = await page.waitForResponse(r => new URL(r.url()).pathname.endsWith(`/tasks/${encodeURIComponent(payload.task_id)}/inputs`) && r.request().method() === 'POST')
  return { response, payload, inputResponse }
})
await page.getByRole('button', { name: '创建并保存' }).click()
const { response: create, payload: createJson, inputResponse } = await Promise.race([
  inputResponsePromise,
  new Promise((_, reject) => setTimeout(async () => reject(new Error(`create/inputs response timeout; requests=${requests.join(',')}; alerts=${JSON.stringify(await page.locator('[role="alert"]').allTextContents().catch(() => []))}`)), 10_000)),
])
if (!create.ok()) fail(`create returned ${create.status()}`)
created.push(createJson.task_id)
if (!inputResponse.ok()) fail(`inputs returned ${inputResponse.status()}`)
await page.waitForURL(new RegExp(`/tasks/${createJson.task_id.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\$&')}$`), { timeout: 8_000 })
if (created.length !== 1) fail(`created ${created.length} tasks`)

const readbackRes = await fetch(`${api}/api/v1/tasks/${encodeURIComponent(createJson.task_id)}/inputs`)
if (!readbackRes.ok) fail(`inputs readback returned ${readbackRes.status}`)
const readback = await readbackRes.json()
if (readback.inputs?.script !== script) fail('readback script differs')
if (crypto.createHash('sha256').update(readback.inputs.script).digest('hex') !== scriptHash) fail('readback script hash differs')
if (readback.inputs?.style !== '极简粗线简笔白板风') fail('style did not round-trip')
if (readback.inputs?.include_subtitles !== true) fail('subtitle setting did not round-trip')
if (readback.inputs?.pen_text !== '' || readback.inputs?.stroke_detail !== 'detailed') fail('pen/stroke did not round-trip')
if (readback.visual_anchor_enabled !== true) fail('anchor setting did not round-trip')
if (readback.rules?.min_chars !== 35 || readback.rules?.target_chars !== 80 || readback.rules?.max_chars !== 140) fail('character rules did not round-trip')
if (!readback.reference_audio?.uploaded || readback.reference_audio.size_bytes !== 204) fail('reference metadata did not round-trip')

await page.screenshot({ path: path.join(evidence, 'intake-created.png'), fullPage: false })
const queueResponse = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/tasks' && r.request().method() === 'GET')
await page.getByRole('link', { name: '返回任务队列' }).click()
await page.waitForURL(`${web}/`)
await page.getByPlaceholder('搜索任务名…').fill(title)
await page.getByPlaceholder('搜索任务名…').press('Enter')
await queueResponse
await page.getByText(title, { exact: true }).waitFor({ state: 'visible', timeout: 8_000 })
if (await page.getByText(title, { exact: true }).count() !== 1) fail('queue shows task more than once')
await page.screenshot({ path: path.join(evidence, 'intake-queue.png'), fullPage: false })
await page.getByRole('button', { name: '进入工作台' }).click()
await page.waitForURL(new RegExp(`/tasks/${createJson.task_id}$`))
await page.getByText('制作输入', { exact: true }).waitFor({ state: 'visible', timeout: 8_000 })
if (await page.getByLabel('视频文案').inputValue() !== script) fail('workbench did not restore script')
if (!await page.getByText(/已保存参考音频/).isVisible()) fail('workbench did not restore reference metadata')
if (await page.getByLabel('风格').inputValue() !== '极简粗线简笔白板风') fail('workbench did not restore style')
await page.screenshot({ path: path.join(evidence, 'intake-workbench.png'), fullPage: false })

if (created.length !== 1) fail('more than one task created')
if (requests.some(r => /\/start|\/pipeline\/|\/stages\/.*\/(run|retry)/.test(r))) fail(`pre-run request leaked: ${requests.join(', ')}`)
if (errors.length) fail(`browser issues: ${errors.join('; ')}`)

await fs.mkdir(evidence, { recursive: true })
const manifest = { task_id_sha256: crypto.createHash('sha256').update(createJson.task_id).digest('hex'), title_sha256: crypto.createHash('sha256').update(title).digest('hex'), script_sha256: scriptHash, script_length: script.length, screenshots: [] }
for (const file of ['intake-created.png', 'intake-queue.png', 'intake-workbench.png']) {
  const data = await fs.readFile(path.join(evidence, file)); manifest.screenshots.push({ file, sha256: crypto.createHash('sha256').update(data).digest('hex'), bytes: data.length })
}
await fs.writeFile(path.join(evidence, 'intake-manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`)
await context.close(); await browser.close(); await fs.rm(runtime, { recursive: true, force: true })
console.log(JSON.stringify({ task_id_sha256: manifest.task_id_sha256, script_sha256: scriptHash, script_length: script.length, screenshots: manifest.screenshots, requests, browser_issues: 0 }, null, 2))
