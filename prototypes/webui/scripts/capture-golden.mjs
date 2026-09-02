import { createHash } from 'node:crypto'
import { mkdtemp, mkdir, readFile, rm, stat, writeFile } from 'node:fs/promises'
import { spawn, spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, join, relative, resolve } from 'node:path'
import { tmpdir } from 'node:os'
import { chromium } from 'playwright'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const prototypeDir = resolve(scriptDir, '..')
const repoDir = resolve(prototypeDir, '..', '..')
const outputDir = join(repoDir, 'docs/Mountain/webui-prototype-baseline/screenshots/WEB-PARITY-004/golden')
const manifestPath = join(repoDir, 'docs/Mountain/webui-prototype-baseline/WEB-PARITY-004-manifest.json')
const port = 5182
const origin = `http://127.0.0.1:${port}`
const update = process.argv.slice(2).join(' ') === '--update'
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

function manifestFor(captured) {
  return {
    schema_version: 1,
    source: { kind: 'git-tracked prototype', commit: sourceCommit, path: 'prototypes/webui', origin, mode: 'loopback read-only preview' },
    capture: { viewport: { width: 1366, height: 900 }, dpr: 1, zoom: '100%', browser: 'Playwright Chromium', browser_issues: { console_error: 0, pageerror: 0, failed_request: 0, http_gte_400: 0 } },
    goldens: captured,
  }
}

async function freezeMotion(page) {
  await page.evaluate(() => new Promise((resolveFrame) => requestAnimationFrame(() => requestAnimationFrame(resolveFrame))))
}

async function verifyFrozenCapture(captured, manifestText) {
  const frozenManifest = await readFile(manifestPath, 'utf8').catch(() => {
    throw new Error('frozen manifest is missing; rerun with --update to explicitly generate the baseline')
  })
  if (manifestText !== frozenManifest) throw new Error('captured manifest differs from the frozen manifest; refusing to overwrite baseline')
  for (const pageSpec of captured) {
    const frozenFile = join(repoDir, pageSpec.golden_file)
    const frozenContent = await readFile(frozenFile).catch(() => {
      throw new Error(`frozen golden is missing: ${pageSpec.golden_file}`)
    })
    const frozenHash = createHash('sha256').update(frozenContent).digest('hex')
    if (frozenHash !== pageSpec.sha256 || frozenContent.length !== pageSpec.bytes) {
      throw new Error(`captured ${pageSpec.id} differs from its frozen golden; refusing to overwrite baseline`)
    }
  }
}

let server
let browser
let captureDir
try {
  captureDir = await mkdtemp(join(tmpdir(), 'prototype-golden-'))

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
    const style = document.createElement('style')
    style.textContent = `
      *, *::before, *::after {
        animation: none !important;
        transition: none !important;
        caret-color: transparent !important;
      }
    `
    const applyFreeze = () => {
      if (!document.documentElement) return false
      document.documentElement.append(style)
      return true
    }
    if (!applyFreeze()) {
      const observer = new MutationObserver(() => {
        if (applyFreeze()) observer.disconnect()
      })
      observer.observe(document, { childList: true })
    }
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
    await freezeMotion(page)
    await page.screenshot({ path: join(captureDir, `${pageSpec.id}.png`), fullPage: false })
    await page.close()
  }
  await context.close()
  if (issues.length) throw new Error(`browser evidence failed:\n${issues.join('\n')}`)

  for (const pageSpec of pages) {
    const absoluteFile = join(captureDir, `${pageSpec.id}.png`)
    const content = await readFile(absoluteFile)
    const dimensions = pngSize(content)
    if (dimensions.width !== 1366 || dimensions.height !== 900) throw new Error(`${pageSpec.id} dimensions are ${dimensions.width}x${dimensions.height}, expected 1366x900`)
    captured.push({
      id: pageSpec.id,
      purpose: pageSpec.purpose,
      prototype_route: pageSpec.route,
      golden_file: relative(repoDir, join(outputDir, `${pageSpec.id}.png`)),
      width: dimensions.width,
      height: dimensions.height,
      dpr: 1,
      sha256: createHash('sha256').update(content).digest('hex'),
      bytes: (await stat(absoluteFile)).size,
    })
  }
  const manifestText = `${JSON.stringify(manifestFor(captured), null, 2)}\n`
  if (update) {
    await mkdir(outputDir, { recursive: true })
    for (const pageSpec of pages) await writeFile(join(outputDir, `${pageSpec.id}.png`), await readFile(join(captureDir, `${pageSpec.id}.png`)))
    await writeFile(manifestPath, manifestText)
    process.stdout.write(`updated ${captured.length} browser goldens from ${sourceCommit}\n`)
  } else {
    await verifyFrozenCapture(captured, manifestText)
    process.stdout.write(`verified ${captured.length} frozen browser goldens from ${sourceCommit}\n`)
  }
} finally {
  if (browser) await browser.close()
  if (server) await stop(server)
  if (captureDir) await rm(captureDir, { recursive: true, force: true })
}
