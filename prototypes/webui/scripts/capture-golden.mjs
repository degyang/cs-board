import { createHash } from 'node:crypto'
import { mkdir, readFile, rm, stat, writeFile } from 'node:fs/promises'
import { spawn, spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, join, relative, resolve } from 'node:path'
import { chromium } from 'playwright'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const prototypeDir = resolve(scriptDir, '..')
const repoDir = resolve(prototypeDir, '..', '..')
const outputDir = join(repoDir, 'docs/Mountain/webui-prototype-baseline/screenshots/WEB-PARITY-004/golden')
const manifestPath = join(repoDir, 'docs/Mountain/webui-prototype-baseline/WEB-PARITY-004-manifest.json')
const port = 5182
const origin = `http://127.0.0.1:${port}`
const sourceCommit = git(['rev-parse', '0f56e824c0d49ab5c090e7ea07086dc9d47f47a9'])
const pages = [
  { id: '01-brand-shell', route: '/help', purpose: '品牌壳' },
  { id: '02-task-queue', route: '/projects', purpose: '任务队列（历史 Project 路由的视觉映射；正式产品对应 /tasks）' },
  { id: '03-create-six-tabs', route: '/create', purpose: '六 Tab 新建任务映射（历史 Project 创建页的视觉映射；正式产品对应 /tasks/new）' },
  { id: '04-settings', route: '/settings', purpose: '设置' },
  { id: '05-assets', route: '/assets', purpose: '资产' },
]

function git(args) {
  const result = spawnSync('git', args, { cwd: repoDir, encoding: 'utf8' })
  if (result.status !== 0) throw new Error(`git ${args.join(' ')} failed: ${result.stderr}`)
  return result.stdout.trim()
}

function pngSize(buffer) {
  if (buffer.toString('ascii', 1, 4) !== 'PNG') throw new Error('screenshot is not PNG')
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) }
}

async function waitForServer(child) {
  const deadline = Date.now() + 20_000
  while (Date.now() < deadline) {
    try {
      const response = await fetch(origin)
      if (response.ok) return
    } catch {}
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 100))
  }
  throw new Error('Vite did not become reachable on loopback within 20 seconds')
}

async function stop(child) {
  if (child.exitCode !== null) return
  child.kill('SIGTERM')
  await new Promise((resolveStop) => {
    const timer = setTimeout(() => {
      child.kill('SIGKILL')
      resolveStop()
    }, 5_000)
    child.once('exit', () => {
      clearTimeout(timer)
      resolveStop()
    })
  })
}

let server
let browser
try {
  await mkdir(outputDir, { recursive: true })
  for (const page of pages) await rm(join(outputDir, `${page.id}.png`), { force: true })

  server = spawn(join(prototypeDir, 'node_modules/.bin/vite'), ['preview', '--host', '127.0.0.1', '--port', String(port), '--strictPort'], {
    cwd: prototypeDir,
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  let serverOutput = ''
  server.stdout.on('data', (chunk) => { serverOutput += chunk })
  server.stderr.on('data', (chunk) => { serverOutput += chunk })
  server.once('exit', (code) => { if (code !== 0) serverOutput += `\npreview exited ${code}` })
  await waitForServer(server)

  browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 }, deviceScaleFactor: 1 })
  await context.addInitScript(() => {
    const fixedTime = 1_777_777_777_000
    const NativeDate = Date
    class FrozenDate extends NativeDate {
      constructor(...args) {
        super(...(args.length ? args : [fixedTime]))
      }
      static now() { return fixedTime }
    }
    globalThis.Date = FrozenDate
  })
  const issues = []
  const captured = []
  for (const pageSpec of pages) {
    const page = await context.newPage()
    page.on('console', (message) => { if (message.type() === 'error') issues.push(`${pageSpec.route}: console error: ${message.text()}`) })
    page.on('pageerror', (error) => issues.push(`${pageSpec.route}: pageerror: ${error.message}`))
    page.on('requestfailed', (request) => issues.push(`${pageSpec.route}: failed request: ${request.url()} (${request.failure()?.errorText ?? 'unknown'})`))
    page.on('response', (response) => { if (response.status() >= 400) issues.push(`${pageSpec.route}: HTTP ${response.status()}: ${response.url()}`) })
    const response = await page.goto(`${origin}${pageSpec.route}`, { waitUntil: 'networkidle' })
    if (!response?.ok()) throw new Error(`${pageSpec.route} returned HTTP ${response?.status() ?? 'no response'}`)
    await page.screenshot({ path: join(outputDir, `${pageSpec.id}.png`), fullPage: false })
    await page.close()
  }
  await context.close()
  if (issues.length) throw new Error(`browser evidence failed:\n${issues.join('\n')}`)

  for (const pageSpec of pages) {
    const absoluteFile = join(outputDir, `${pageSpec.id}.png`)
    const content = await readFile(absoluteFile)
    const dimensions = pngSize(content)
    if (dimensions.width !== 1366 || dimensions.height !== 900) throw new Error(`${pageSpec.id} dimensions are ${dimensions.width}x${dimensions.height}, expected 1366x900`)
    captured.push({
      id: pageSpec.id,
      purpose: pageSpec.purpose,
      prototype_route: pageSpec.route,
      golden_file: relative(repoDir, absoluteFile),
      width: dimensions.width,
      height: dimensions.height,
      dpr: 1,
      sha256: createHash('sha256').update(content).digest('hex'),
      bytes: (await stat(absoluteFile)).size,
    })
  }
  const manifest = {
    schema_version: 1,
    source: { kind: 'git-tracked prototype', commit: sourceCommit, path: 'prototypes/webui', origin, mode: 'loopback read-only preview' },
    capture: { viewport: { width: 1366, height: 900 }, dpr: 1, zoom: '100%', browser: 'Playwright Chromium', browser_issues: { console_error: 0, pageerror: 0, failed_request: 0, http_gte_400: 0 } },
    goldens: captured,
  }
  await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`)
  process.stdout.write(`captured ${captured.length} browser goldens from ${sourceCommit}\n`)
} finally {
  if (browser) await browser.close()
  if (server) await stop(server)
}
