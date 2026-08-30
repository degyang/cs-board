/**
 * http-contract.test.ts
 *
 * HTTP boundary contract tests — mock global.fetch directly to verify
 * URL paths, HTTP methods, query params, and FormData handling.
 *
 * These complement contract.test.tsx (component-level mocks).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  uploadInputs,
  startRun,
  cancelRun,
  retryRun,
  runStage,
  retryStage,
  fetchEvents,
  fetchLogs,
  getFinalUrl,
  fetchProviders,
  fetchProvider,
  updateProviderConfig,
  fetchProviderSecrets,
  setProviderSecret,
  deleteProviderSecret,
} from '../src/lib/api/client'

// ── Mock global.fetch ───────────────────────────────────────────────────

const mockFetch = vi.fn()

beforeEach(() => {
  vi.clearAllMocks()
  vi.stubGlobal('fetch', mockFetch)
})

afterEach(() => {
  vi.restoreAllMocks()
})

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    headers: new Headers({ 'content-type': 'application/json' }),
  }
}

// ── uploadInputs: FormData, no manual Content-Type ─────────────────────

describe('HTTP contract: uploadInputs', () => {
  it('sends POST to /tasks/{id}/inputs with FormData body', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ ok: true, task_id: 'p1', input_saved: true }))

    const form = new FormData()
    form.set('script', 'test script')
    form.set('style', 'hand-drawn')

    const result = await uploadInputs('p1', form)

    expect(result.ok).toBe(true)
    expect(mockFetch).toHaveBeenCalledTimes(1)

    const [url, opts] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/tasks/p1/inputs')
    expect(opts.method).toBe('POST')
    expect(opts.body).toBeInstanceOf(FormData)
  })

  it('does not set Content-Type header (browser auto-sets with boundary)', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ ok: true, task_id: 'p1', input_saved: true }))

    const form = new FormData()
    form.set('script', 'test')

    await uploadInputs('p1', form)

    const [, opts] = mockFetch.mock.calls[0]
    // No headers should be set — browser handles multipart Content-Type
    expect(opts.headers).toBeUndefined()
  })

  it('encodes taskId in URL path', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ ok: true, task_id: 'a/b', input_saved: true }))

    const form = new FormData()
    form.set('script', 'test')

    await uploadInputs('a/b', form)

    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/tasks/a%2Fb/inputs')
  })
})

// ── startRun / cancelRun / retryRun ────────────────────────────────────

describe('HTTP contract: run actions', () => {
  it('startRun sends POST to /tasks/{id}/runs/{runId}/start', async () => {
    mockFetch.mockResolvedValue(jsonResponse({
      ok: true, command: 'start', task_id: 'p1', run_id: 'r1',
      trace_id: 't1', command_id: 'c1',
    }))

    await startRun('p1', 'r1')

    const [url, opts] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/tasks/p1/runs/r1/start')
    expect(opts.method).toBe('POST')
  })

  it('cancelRun sends POST to /tasks/{id}/runs/{runId}/cancel', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ ok: true, status: 'cancelled' }))

    await cancelRun('p1', 'r1')

    const [url, opts] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/tasks/p1/runs/r1/cancel')
    expect(opts.method).toBe('POST')
  })

  it('retryRun sends POST to /tasks/{id}/runs/{runId}/retry', async () => {
    mockFetch.mockResolvedValue(jsonResponse({
      ok: true, command: 'retry', task_id: 'p1', run_id: 'r1',
      trace_id: 't1', command_id: 'c1',
    }))

    await retryRun('p1', 'r1')

    const [url, opts] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/tasks/p1/runs/r1/retry')
    expect(opts.method).toBe('POST')
  })
})

// ── runStage / retryStage ──────────────────────────────────────────────

describe('HTTP contract: stage actions', () => {
  it('runStage sends POST to /tasks/{id}/runs/{runId}/stages/{stage}/run', async () => {
    mockFetch.mockResolvedValue(jsonResponse({
      ok: true, command: 'run-stage', task_id: 'p1', run_id: 'r1',
      trace_id: 't1', command_id: 'c1', stage: 'clone-voice',
    }))

    await runStage('p1', 'r1', 'clone-voice')

    const [url, opts] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/tasks/p1/runs/r1/stages/clone-voice/run')
    expect(opts.method).toBe('POST')
  })

  it('retryStage sends POST to /tasks/{id}/runs/{runId}/stages/{stage}/retry', async () => {
    mockFetch.mockResolvedValue(jsonResponse({
      ok: true, command: 'retry-stage', task_id: 'p1', run_id: 'r1',
      trace_id: 't1', command_id: 'c1', stage: 'render-visuals',
    }))

    await retryStage('p1', 'r1', 'render-visuals')

    const [url, opts] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/tasks/p1/runs/r1/stages/render-visuals/retry')
    expect(opts.method).toBe('POST')
  })

  it('encodes stage key in URL path', async () => {
    mockFetch.mockResolvedValue(jsonResponse({
      ok: true, command: 'run-stage', task_id: 'p1', run_id: 'r1',
      trace_id: 't1', command_id: 'c1', stage: 'segment-script',
    }))

    await runStage('p1', 'r1', 'segment-script')

    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('/stages/segment-script/run')
  })
})

// ── fetchEvents: cursor pagination ─────────────────────────────────────

describe('HTTP contract: fetchEvents', () => {
  it('sends GET to /tasks/{id}/runs/{runId}/events', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ items: [], next_cursor: 0 }))

    await fetchEvents('p1', 'r1')

    const [url, opts] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/tasks/p1/runs/r1/events')
    expect(opts.method).toBeUndefined() // GET is default
  })

  it('appends after=0 on first request (no cursor)', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ items: [], next_cursor: 0 }))

    await fetchEvents('p1', 'r1', 0)

    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('after=0')
  })

  it('appends after={cursor} for subsequent pages', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ items: [], next_cursor: 42 }))

    await fetchEvents('p1', 'r1', 42)

    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('after=42')
  })
})

// ── fetchLogs: level/component/stage filters ───────────────────────────

describe('HTTP contract: fetchLogs', () => {
  it('sends GET to /tasks/{id}/runs/{runId}/logs', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ items: [] }))

    await fetchLogs('p1', 'r1')

    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/tasks/p1/runs/r1/logs')
  })

  it('appends level query param when filter provided', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ items: [] }))

    await fetchLogs('p1', 'r1', { level: 'ERROR' })

    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('level=ERROR')
  })

  it('appends component query param when filter provided', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ items: [] }))

    await fetchLogs('p1', 'r1', { component: 'segment-script' })

    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('component=segment-script')
  })

  it('appends stage query param when filter provided', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ items: [] }))

    await fetchLogs('p1', 'r1', { stage: 'clone-voice' })

    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('stage=clone-voice')
  })

  it('combines multiple filter params', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ items: [] }))

    await fetchLogs('p1', 'r1', { level: 'WARN', component: 'render', stage: 'render-visuals' })

    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('level=WARN')
    expect(url).toContain('component=render')
    expect(url).toContain('stage=render-visuals')
  })
})

// ── getFinalUrl ────────────────────────────────────────────────────────

describe('HTTP contract: getFinalUrl', () => {
  it('returns URL ending with /tasks/{id}/runs/{runId}/final', () => {
    const url = getFinalUrl('p1', 'r1')
    expect(url).toMatch(/\/api\/v1\/tasks\/p1\/runs\/r1\/final$/)
  })

  it('encodes special characters in projectId', () => {
    const url = getFinalUrl('a/b c', 'r1')
    expect(url).toContain('a%2Fb%20c')
    expect(url).toMatch(/\/runs\/r1\/final$/)
  })

  it('does NOT return /artifacts/final.mp4', () => {
    const url = getFinalUrl('p1', 'r1')
    expect(url).not.toContain('artifacts')
    expect(url).not.toContain('.mp4')
  })
})

// ── Provider endpoints ──────────────────────────────────────────────────

describe('HTTP contract: fetchProviders', () => {
  it('sends GET to /providers', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ providers: {}, all_configured: true, all_available: true }))

    await fetchProviders()

    const [url, opts] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/providers')
    expect(opts.method).toBeUndefined() // GET is default
  })
})

describe('HTTP contract: fetchProvider', () => {
  it('sends GET to /providers/{name}', async () => {
    mockFetch.mockResolvedValue(jsonResponse({
      name: 'text_model', profile: {}, config: {}, config_status: {}, availability: {},
    }))

    await fetchProvider('text_model')

    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/providers/text_model')
  })
})

describe('HTTP contract: updateProviderConfig', () => {
  it('sends PUT to /providers/{name}/config with body', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ ok: true, provider: 'text_model', config: {} }))

    await updateProviderConfig('text_model', { base_url: 'https://example.com', model: 'gpt-4o' })

    const [url, opts] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/providers/text_model/config')
    expect(opts.method).toBe('PUT')
    const body = JSON.parse(opts.body)
    expect(body.base_url).toBe('https://example.com')
    expect(body.model).toBe('gpt-4o')
  })
})

describe('HTTP contract: fetchProviderSecrets', () => {
  it('sends GET to /providers/{name}/secrets', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ provider: 'text_model', secrets: {} }))

    await fetchProviderSecrets('text_model')

    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/providers/text_model/secrets')
  })
})

describe('HTTP contract: setProviderSecret', () => {
  it('sends POST to /providers/{name}/secrets with key and value', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ ok: true, provider: 'text_model', key: 'api_key' }))

    await setProviderSecret('text_model', { key: 'api_key', value: 'sk-test123' })

    const [url, opts] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/providers/text_model/secrets')
    expect(opts.method).toBe('POST')
    const body = JSON.parse(opts.body)
    expect(body.key).toBe('api_key')
    expect(body.value).toBe('sk-test123')
  })
})

describe('HTTP contract: deleteProviderSecret', () => {
  it('sends DELETE to /providers/{name}/secrets/{key}', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ ok: true, provider: 'text_model', key: 'api_key' }))

    await deleteProviderSecret('text_model', 'api_key')

    const [url, opts] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/providers/text_model/secrets/api_key')
    expect(opts.method).toBe('DELETE')
  })
})
