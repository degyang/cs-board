/**
 * Contract checker execution tests (§3E)
 *
 * Uses a controlled HTTP server to test the production checkRealBackend flow.
 * Verifies actual HTTP method/path, response parsing, and violation detection.
 * No source string assertions, no copied algorithms.
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import http from 'node:http'
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { checkRealBackend } from '../scripts/contract-checker-core.mjs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, '..')
const TYPES_FILE = path.join(ROOT, 'src/lib/api/types.ts')
const tsContent = fs.readFileSync(TYPES_FILE, 'utf-8')

// ── Controlled test server ─────────────────────────────────────────────────

type Handler = (req: http.IncomingMessage, body: string) => { status: number; body: unknown }

function createTestServer(handler: Handler) {
  const requests: { method: string; path: string; body: string }[] = []

  const server = http.createServer((req, res) => {
    let body = ''
    req.on('data', chunk => { body += chunk })
    req.on('end', () => {
      const result = handler(req, body)
      requests.push({ method: req.method!, path: req.url!, body })
      res.writeHead(result.status, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify(result.body))
    })
  })

  return {
    server,
    requests,
    start: () => new Promise<void>(resolve => {
      server.listen(0, '127.0.0.1', () => resolve())
    }),
    stop: () => new Promise<void>(resolve => server.close(() => resolve())),
    getBaseUrl: () => {
      const addr = server.address() as { port: number }
      return 'http://127.0.0.1:' + addr.port + '/api/v1'
    },
  }
}

// ── Valid fixtures for success scenario ────────────────────────────────────

const VALID_SERVICE_LIST = {
  items: [{
    schema_version: 1, revision: 1, service_id: 'test-svc', display_name: 'Test',
    capability: 'text_generation', adapter_type: 'openai_compatible',
    endpoint: null, model: null, enabled: true, priority: 0, is_default: false,
    config: {}, required_secrets: [], optional_secrets: [],
    config_status: { configured: true, missing_fields: [], missing_secrets: [] },
    availability: { available: true, checked_at: null, latency_ms: null, component: null, error_code: null, suggestion: null },
    secret_status: { configured: true, required: [], missing: [] },
    created_at: '2025-01-01T00:00:00Z', updated_at: '2025-01-01T00:00:00Z',
  }],
  next_cursor: null,
  total: 1,
}

const VALID_SERVICE_DETAIL = VALID_SERVICE_LIST.items[0]

const VALID_SERVICE_SECRETS = {
  items: [{ secret_key: 'api_key', configured: true, masked_value: '***', updated_at: null }],
  total: 1,
}

const VALID_PROBE = { available: true, checked_at: null, latency_ms: 100, component: null, error_code: null, suggestion: null }

const VALID_STYLE_LIST = {
  items: [{
    style_id: 's1', kind: 'preset', name: 'Test', description: '', engine: null,
    status: 'active', revision: 1, tags: [], prompt_text: null, negative_prompt: null,
    preview_asset_id: null, config: {}, created_at: '', updated_at: '',
  }],
  next_cursor: null, total: 1,
}

const VALID_VOICE_LIST = {
  items: [{
    voice_id: 'v1', name: 'Test', tags: [], duration_ms: 1000,
    sample_rate: null, channels: null, format: null, enabled: true,
    status: 'active', created_at: '', updated_at: '',
  }],
  next_cursor: null, total: 1,
}

const VALID_VOICE_ALIGNMENT = {
  speech_synthesis: {
    service_id: 'tts', display_name: 'TTS', capability: 'speech_synthesis',
    adapter_type: 'openai_compatible', endpoint: null, model: null, timeout: null,
    availability: { available: true, checked_at: null, latency_ms: null, component: null, error_code: null, suggestion: null },
  },
  speech_alignment: {
    service_id: 'align', display_name: 'Align', capability: 'speech_alignment',
    adapter_type: 'whisper', endpoint: null, model: null, timeout: null,
    availability: { available: true, checked_at: null, latency_ms: null, component: null, error_code: null, suggestion: null },
  },
  indextts: { available: false, checked_at: null, latency_ms: null, component: null, error_code: null, suggestion: null },
  whisper: { available: false, checked_at: null, latency_ms: null, component: null, error_code: null, suggestion: null },
}

const VALID_TOOLCHAIN = {
  tools: [{ component: 'python', available: true, version: '3.11', error_code: null, suggestion: null }],
}

const VALID_STORAGE = {
  writable: true, assets_available: true, tasks_available: true, temp_available: true,
  free_bytes: null, used_bytes: null, cleanup_policy: null, error_code: null, suggestion: null,
}

const VALID_DIAGNOSTICS = {
  api: { status: 'ok', endpoint: null, latency_ms: null },
  services: { total: 1, available: 1, unavailable: 0 },
  toolchain: { total: 1, available: 1, missing: 0 },
  storage: { writable: true, free_bytes: null, used_bytes: null },
  telemetry: { enabled: false, endpoint: null },
  logs: { recent_errors: 0, log_path: null },
  recent_errors: [],
}

const VALID_ERROR = { error: { code: 'NOT_FOUND', message: 'not found' } }

function successHandler(req: http.IncomingMessage, _body: string) {
  const url = req.url!

  if (url === '/api/v1/services' || url.startsWith('/api/v1/services?')) {
    return { status: 200, body: VALID_SERVICE_LIST }
  }
  if (url === '/api/v1/services/test-svc') {
    return { status: 200, body: VALID_SERVICE_DETAIL }
  }
  if (url === '/api/v1/services/test-svc/secrets') {
    return { status: 200, body: VALID_SERVICE_SECRETS }
  }
  if (url === '/api/v1/services/test-svc/probe' && req.method === 'POST') {
    return { status: 200, body: VALID_PROBE }
  }
  if (url === '/api/v1/assets/styles' || url.startsWith('/api/v1/assets/styles?')) {
    return { status: 200, body: VALID_STYLE_LIST }
  }
  if (url === '/api/v1/assets/voices' || url.startsWith('/api/v1/assets/voices?')) {
    return { status: 200, body: VALID_VOICE_LIST }
  }
  if (url === '/api/v1/settings/voice-alignment') {
    return { status: 200, body: VALID_VOICE_ALIGNMENT }
  }
  if (url === '/api/v1/settings/toolchain') {
    return { status: 200, body: VALID_TOOLCHAIN }
  }
  if (url === '/api/v1/settings/storage') {
    return { status: 200, body: VALID_STORAGE }
  }
  if (url === '/api/v1/settings/diagnostics') {
    return { status: 200, body: VALID_DIAGNOSTICS }
  }
  if (url === '/api/v1/nonexistent-path-404') {
    return { status: 404, body: VALID_ERROR }
  }

  return { status: 404, body: { error: { code: 'NOT_FOUND', message: 'not found' } } }
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe('contract checker execution: complete success', () => {
  let srv: ReturnType<typeof createTestServer>

  beforeAll(async () => {
    srv = createTestServer(successHandler)
    await srv.start()
  })

  afterAll(async () => { await srv.stop() })

  it('checkRealBackend returns zero violations for valid responses', async () => {
    const violations = await checkRealBackend(tsContent, srv.getBaseUrl(), {
      serviceId: 'test-svc',
      fetchFn: ((url: string, init?: RequestInit) => fetch(url, init)) as typeof fetch,
    })
    expect(violations).toEqual([])
  })

  it('sends GET for service detail', async () => {
    const detailReq = srv.requests.find(r => r.path === '/api/v1/services/test-svc')
    expect(detailReq).toBeDefined()
    expect(detailReq!.method).toBe('GET')
  })

  it('sends GET for service secrets', async () => {
    const secretsReq = srv.requests.find(r => r.path === '/api/v1/services/test-svc/secrets')
    expect(secretsReq).toBeDefined()
    expect(secretsReq!.method).toBe('GET')
  })

  it('sends POST for service probe', async () => {
    const probeReq = srv.requests.find(r => r.path === '/api/v1/services/test-svc/probe')
    expect(probeReq).toBeDefined()
    expect(probeReq!.method).toBe('POST')
  })
})

describe('contract checker execution: probe wrong method', () => {
  it('fails when probe returns data for GET (simulating checker sends GET)', async () => {
    const srv = createTestServer((req, _body) => {
      if (req.url === '/api/v1/services/test-svc/probe' && req.method === 'GET') {
        // Server accepts GET — but checker should send POST
        return { status: 200, body: VALID_PROBE }
      }
      if (req.url === '/api/v1/services/test-svc/probe') {
        return { status: 405, body: { error: { code: 'METHOD_NOT_ALLOWED', message: 'use POST' } } }
      }
      return successHandler(req, _body)
    })
    await srv.start()

    // If we manually call with wrong method, the server returns 405
    const violations = await checkRealBackend(tsContent, srv.getBaseUrl(), {
      serviceId: 'test-svc',
      fetchFn: ((url: string, init?: RequestInit) => fetch(url, init)) as typeof fetch,
    })
    // Checker sends POST; server accepts POST → no violation
    // This test verifies the checker sends POST (verified by request log)
    const probeReq = srv.requests.find(r => r.path === '/api/v1/services/test-svc/probe')
    expect(probeReq?.method).toBe('POST')

    await srv.stop()
  })
})

describe('contract checker execution: missing required fields', () => {
  it('detects missing required fields in ServiceAvailability', async () => {
    const srv = createTestServer((req, _body) => {
      if (req.url === '/api/v1/services/test-svc/probe' && req.method === 'POST') {
        return { status: 200, body: { available: true } } // missing checked_at, latency_ms, etc.
      }
      return successHandler(req, _body)
    })
    await srv.start()

    const violations = await checkRealBackend(tsContent, srv.getBaseUrl(), {
      serviceId: 'test-svc',
      fetchFn: ((url: string, init?: RequestInit) => fetch(url, init)) as typeof fetch,
    })

    expect(violations.some(v => v.includes('checked_at') && v.includes('required'))).toBe(true)
    expect(violations.some(v => v.includes('latency_ms') && v.includes('required'))).toBe(true)

    await srv.stop()
  })
})

describe('contract checker execution: unknown fields', () => {
  it('detects unknown fields in ServiceDefinition', async () => {
    const srv = createTestServer((req, _body) => {
      if (req.url === '/api/v1/services/test-svc') {
        return { status: 200, body: { ...VALID_SERVICE_DETAIL, unknown_field: 'bad' } }
      }
      return successHandler(req, _body)
    })
    await srv.start()

    const violations = await checkRealBackend(tsContent, srv.getBaseUrl(), {
      serviceId: 'test-svc',
      fetchFn: ((url: string, init?: RequestInit) => fetch(url, init)) as typeof fetch,
    })

    expect(violations.some(v => v.includes('unknown_field'))).toBe(true)

    await srv.stop()
  })
})

describe('contract checker execution: optional fields allowed to be missing', () => {
  it('passes when optional ApiError fields are missing', async () => {
    const srv = createTestServer((req, _body) => {
      if (req.url === '/api/v1/nonexistent-path-404') {
        return { status: 404, body: { error: { code: 'NOT_FOUND', message: 'not found' } } }
      }
      return successHandler(req, _body)
    })
    await srv.start()

    const violations = await checkRealBackend(tsContent, srv.getBaseUrl(), {
      serviceId: 'test-svc',
      fetchFn: ((url: string, init?: RequestInit) => fetch(url, init)) as typeof fetch,
    })

    // error.response should pass — retryable/details are optional
    expect(violations.filter(v => v.includes('Unified error'))).toEqual([])

    await srv.stop()
  })
})

describe('contract checker execution: type validation', () => {
  it('detects wrong type in top-level field', async () => {
    const srv = createTestServer((req, _body) => {
      if (req.url === '/api/v1/services/test-svc/probe' && req.method === 'POST') {
        return { status: 200, body: { ...VALID_PROBE, available: 'not-boolean' } }
      }
      return successHandler(req, _body)
    })
    await srv.start()

    const violations = await checkRealBackend(tsContent, srv.getBaseUrl(), {
      serviceId: 'test-svc',
      fetchFn: ((url: string, init?: RequestInit) => fetch(url, init)) as typeof fetch,
    })

    expect(violations.some(v => v.includes('expected boolean'))).toBe(true)

    await srv.stop()
  })

  it('detects wrong type in nested field', async () => {
    const srv = createTestServer((req, _body) => {
      if (req.url === '/api/v1/services/test-svc') {
        return {
          status: 200,
          body: {
            ...VALID_SERVICE_DETAIL,
            config_status: { configured: 'not-boolean', missing_fields: [], missing_secrets: [] },
          },
        }
      }
      return successHandler(req, _body)
    })
    await srv.start()

    const violations = await checkRealBackend(tsContent, srv.getBaseUrl(), {
      serviceId: 'test-svc',
      fetchFn: ((url: string, init?: RequestInit) => fetch(url, init)) as typeof fetch,
    })

    expect(violations.some(v => v.includes('config_status.configured'))).toBe(true)

    await srv.stop()
  })

  it('detects wrong type in array element', async () => {
    const srv = createTestServer((req, _body) => {
      if (req.url === '/api/v1/services/test-svc/secrets') {
        return {
          status: 200,
          body: {
            items: [{ secret_key: 123, configured: true, masked_value: null, updated_at: null }],
            total: 1,
          },
        }
      }
      return successHandler(req, _body)
    })
    await srv.start()

    const violations = await checkRealBackend(tsContent, srv.getBaseUrl(), {
      serviceId: 'test-svc',
      fetchFn: ((url: string, init?: RequestInit) => fetch(url, init)) as typeof fetch,
    })

    expect(violations.some(v => v.includes('items[0]'))).toBe(true)

    await srv.stop()
  })
})

describe('contract checker execution: empty service registry', () => {
  it('fails when no service ID and list is empty', async () => {
    const srv = createTestServer((req, _body) => {
      if (req.url?.startsWith('/api/v1/services?') || req.url === '/api/v1/services') {
        return { status: 200, body: { items: [], next_cursor: null, total: 0 } }
      }
      return successHandler(req, _body)
    })
    await srv.start()

    const violations = await checkRealBackend(tsContent, srv.getBaseUrl(), {
      fetchFn: ((url: string, init?: RequestInit) => fetch(url, init)) as typeof fetch,
    })

    expect(violations.some(v => v.includes('No service ID available'))).toBe(true)

    await srv.stop()
  })
})

describe('contract checker execution: network failure', () => {
  it('fails when server is unreachable', async () => {
    // Use a port that's not listening
    const violations = await checkRealBackend(tsContent, 'http://127.0.0.1:1', {
      serviceId: 'test-svc',
      fetchFn: ((url: string, init?: RequestInit) => fetch(url, init)) as typeof fetch,
    })

    expect(violations.length).toBeGreaterThan(0)
  })
})

describe('contract checker execution: silent backend deadline', () => {
  it('makes the CLI exit non-zero on its own and cleans up the child process', async () => {
    const server = http.createServer(() => {})
    await new Promise<void>(resolve => server.listen(0, '127.0.0.1', () => resolve()))
    const addr = server.address() as { port: number }
    const base = 'http://127.0.0.1:' + addr.port + '/api/v1'
    const script = path.join(ROOT, 'scripts/check-api-contract.mjs')
    let timedOut = false

    const result = await new Promise<{ code: number | null; signal: NodeJS.Signals | null; output: string }>((resolve, reject) => {
      const child = spawn(process.execPath, [script], {
        cwd: ROOT,
        env: {
          ...process.env,
          MOUNTAIN_API_BASE: base,
          MOUNTAIN_CONTRACT_SERVICE_ID: 'test-svc',
          MOUNTAIN_API_REQUEST_TIMEOUT_MS: '25',
        },
        stdio: ['ignore', 'pipe', 'pipe'],
      })
      let output = ''
      child.stdout.on('data', chunk => { output += chunk.toString() })
      child.stderr.on('data', chunk => { output += chunk.toString() })
      const cleanupTimer = setTimeout(() => {
        timedOut = true
        child.kill('SIGKILL')
      }, 3_000)
      child.on('error', error => {
        clearTimeout(cleanupTimer)
        reject(error)
      })
      child.on('close', (code, signal) => {
        clearTimeout(cleanupTimer)
        resolve({ code, signal, output })
      })
    })

    if (typeof server.closeAllConnections === 'function') server.closeAllConnections()
    await new Promise<void>(resolve => server.close(() => resolve()))

    expect(timedOut).toBe(false)
    expect(result.code).not.toBe(0)
    expect(result.signal).toBeNull()
    expect(result.output).toContain('Request timed out after 25ms')
  })
})

describe('contract checker execution: non-JSON 404', () => {
  it('fails when 404 has no JSON body', async () => {
    const server = http.createServer((_req, res) => {
      res.writeHead(404, { 'Content-Type': 'text/plain' })
      res.end('Not Found')
    })
    await new Promise<void>(resolve => server.listen(0, '127.0.0.1', () => resolve()))
    const addr = server.address() as { port: number }
    const base = 'http://127.0.0.1:' + addr.port + '/api/v1'

    const violations = await checkRealBackend(tsContent, base, {
      serviceId: 'test-svc',
      fetchFn: ((url: string, init?: RequestInit) => fetch(url, init)) as typeof fetch,
    })

    expect(violations.some(v => v.includes('no JSON body') || v.includes('Unexpected token') || v.includes('404'))).toBe(true)

    await new Promise<void>(resolve => server.close(() => resolve()))
  })
})

describe('contract checker execution: 404 error response as metadata', () => {
  it('validates error body on 404 without injecting status into body', async () => {
    const srv = createTestServer((req, _body) => {
      if (req.url === '/api/v1/nonexistent-path-404') {
        return { status: 404, body: { error: { code: 'NOT_FOUND', message: 'not found' } } }
      }
      return successHandler(req, _body)
    })
    await srv.start()

    const violations = await checkRealBackend(tsContent, srv.getBaseUrl(), {
      serviceId: 'test-svc',
      fetchFn: ((url: string, init?: RequestInit) => fetch(url, init)) as typeof fetch,
    })

    // Should not have violations about _status field
    expect(violations.filter(v => v.includes('_status'))).toEqual([])
    // ErrorResponse should validate cleanly
    expect(violations.filter(v => v.includes('Unified error'))).toEqual([])

    await srv.stop()
  })
})
