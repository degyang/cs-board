/* ==========================================================================
   HTTP Contract Tests — Assets & Services APIs
   ========================================================================== */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MountainApiError, request, getVoiceContentUrl } from '../src/lib/api/http'
import { fetchStyles, createStyle, updateStyle, activateStyle, deactivateStyle, copyStyle, fetchVoices, createVoice, activateVoice, deactivateVoice, uploadAsset } from '../src/lib/api/assets'
import { fetchServices, createService, updateService, deleteService, activateService, deactivateService, probeService, setDefaultService, fetchServiceSecrets, setServiceSecret, deleteServiceSecret } from '../src/lib/api/services'
import { fetchRuntimeSettings, fetchVoiceAlignmentSettings, fetchToolchainSettings, fetchStorageSettings, fetchDiagnosticsSettings } from '../src/lib/api/settings'

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  }))
}

function noContentResponse() {
  return Promise.resolve(new Response(null, { status: 204 }))
}

describe('Assets HTTP contract', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('fetchStyles uses GET /assets/styles with query params', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ items: [] }))
    vi.stubGlobal('fetch', mockFetch)

    await fetchStyles({ kind: 'preset', q: 'test', limit: 10 })
    expect(mockFetch).toHaveBeenCalledOnce()
    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('/assets/styles')
    expect(url).toContain('kind=preset')
    expect(url).toContain('q=test')
    expect(url).toContain('limit=10')
  })

  it('createStyle uses POST /assets/styles with JSON body', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ style_id: 's1', name: 'Test' }))
    vi.stubGlobal('fetch', mockFetch)

    await createStyle({ name: 'Test', description: 'A test style' })

    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toContain('/assets/styles')
    expect(init.method).toBe('POST')
    expect(init.headers?.['Content-Type']).toBe('application/json')
    const body = JSON.parse(init.body)
    expect(body.name).toBe('Test')
  })

  it('activateStyle uses POST /assets/styles/{id}/activate', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ style_id: 's1', status: 'active' }))
    vi.stubGlobal('fetch', mockFetch)

    await activateStyle('s1')
    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toContain('/assets/styles/s1/activate')
    expect(init.method).toBe('POST')
  })

  it('deactivateStyle uses POST /assets/styles/{id}/deactivate', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ style_id: 's1', status: 'inactive' }))
    vi.stubGlobal('fetch', mockFetch)

    await deactivateStyle('s1')
    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toContain('/assets/styles/s1/deactivate')
    expect(init.method).toBe('POST')
  })

  it('copyStyle uses POST /assets/styles/{id}/copy', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ style_id: 's2', name: 'Copy' }))
    vi.stubGlobal('fetch', mockFetch)

    await copyStyle('s1')
    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toContain('/assets/styles/s1/copy')
    expect(init.method).toBe('POST')
  })

  it('fetchVoices uses GET /assets/voices', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ items: [] }))
    vi.stubGlobal('fetch', mockFetch)

    await fetchVoices()
    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('/assets/voices')
  })

  it('createVoice uses POST /assets/voices with FormData', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ voice_id: 'v1', name: 'Test' }))
    vi.stubGlobal('fetch', mockFetch)

    const form = new FormData()
    form.append('name', 'Test')
    await createVoice(form)

    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toContain('/assets/voices')
    expect(init.method).toBe('POST')
    expect(init.body).toBeInstanceOf(FormData)
  })

  it('activateVoice uses POST /assets/voices/{id}/activate', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ voice_id: 'v1', status: 'active' }))
    vi.stubGlobal('fetch', mockFetch)

    await activateVoice('v1')
    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toContain('/assets/voices/v1/activate')
    expect(init.method).toBe('POST')
  })

  it('deactivateVoice uses POST /assets/voices/{id}/deactivate', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ voice_id: 'v1', status: 'inactive' }))
    vi.stubGlobal('fetch', mockFetch)

    await deactivateVoice('v1')
    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toContain('/assets/voices/v1/deactivate')
    expect(init.method).toBe('POST')
  })

  it('getVoiceContentUrl returns correct URL', () => {
    const url = getVoiceContentUrl('v1')
    expect(url).toContain('/assets/voices/v1/content')
  })
})

describe('Services HTTP contract', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('fetchServices uses GET /services', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ items: [] }))
    vi.stubGlobal('fetch', mockFetch)

    await fetchServices({ capability: 'text_generation', enabled: true })
    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('/services')
    expect(url).toContain('capability=text_generation')
    expect(url).toContain('enabled=true')
  })

  it('createService uses POST /services', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ service_id: 's1' }))
    vi.stubGlobal('fetch', mockFetch)

    await createService({ display_name: 'Test', capability: 'text_generation' })
    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toContain('/services')
    expect(init.method).toBe('POST')
  })

  it('updateService uses PATCH /services/{id}', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ service_id: 's1' }))
    vi.stubGlobal('fetch', mockFetch)

    await updateService('s1', { display_name: 'Updated' })
    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toContain('/services/s1')
    expect(init.method).toBe('PATCH')
  })

  it('deleteService uses DELETE /services/{id} with 204', async () => {
    const mockFetch = vi.fn().mockImplementation(() => noContentResponse())
    vi.stubGlobal('fetch', mockFetch)

    await deleteService('s1')
    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toContain('/services/s1')
    expect(init.method).toBe('DELETE')
  })

  it('activateService uses POST /services/{id}/activate', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ service_id: 's1', enabled: true }))
    vi.stubGlobal('fetch', mockFetch)

    await activateService('s1')
    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toContain('/services/s1/activate')
    expect(init.method).toBe('POST')
  })

  it('deactivateService uses POST /services/{id}/deactivate', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ service_id: 's1', enabled: false }))
    vi.stubGlobal('fetch', mockFetch)

    await deactivateService('s1')
    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toContain('/services/s1/deactivate')
    expect(init.method).toBe('POST')
  })

  it('probeService uses POST /services/{id}/probe', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ service_id: 's1' }))
    vi.stubGlobal('fetch', mockFetch)

    await probeService('s1')
    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toContain('/services/s1/probe')
    expect(init.method).toBe('POST')
  })

  it('setDefaultService uses POST /services/{id}/default', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ service_id: 's1', is_default: true }))
    vi.stubGlobal('fetch', mockFetch)

    await setDefaultService('s1')
    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toContain('/services/s1/default')
    expect(init.method).toBe('POST')
  })

  it('fetchServiceSecrets uses GET /services/{id}/secrets', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse([]))
    vi.stubGlobal('fetch', mockFetch)

    await fetchServiceSecrets('s1')
    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('/services/s1/secrets')
  })

  it('setServiceSecret uses POST /services/{id}/secrets', async () => {
    const mockFetch = vi.fn().mockImplementation(() => noContentResponse())
    vi.stubGlobal('fetch', mockFetch)

    await setServiceSecret('s1', { key: 'api_key', value: 'secret' })
    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toContain('/services/s1/secrets')
    expect(init.method).toBe('POST')
  })

  it('deleteServiceSecret uses DELETE /services/{id}/secrets/{key}', async () => {
    const mockFetch = vi.fn().mockImplementation(() => noContentResponse())
    vi.stubGlobal('fetch', mockFetch)

    await deleteServiceSecret('s1', 'api_key')
    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toContain('/services/s1/secrets/api_key')
    expect(init.method).toBe('DELETE')
  })
})

describe('Settings HTTP contract', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('fetchRuntimeSettings uses GET /settings/runtime', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ task_runner: { enabled: true, max_concurrent_tasks: 3 } }))
    vi.stubGlobal('fetch', mockFetch)

    await fetchRuntimeSettings()
    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('/settings/runtime')
  })

  it('fetchVoiceAlignmentSettings uses GET /settings/voice-alignment', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ speech_synthesis: null, speech_alignment: null, indextts: null, whisper: null }))
    vi.stubGlobal('fetch', mockFetch)

    await fetchVoiceAlignmentSettings()
    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('/settings/voice-alignment')
  })

  it('fetchToolchainSettings uses GET /settings/toolchain', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ tools: [] }))
    vi.stubGlobal('fetch', mockFetch)

    await fetchToolchainSettings()
    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('/settings/toolchain')
  })

  it('fetchStorageSettings uses GET /settings/storage', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ writable: true, assets_available: true, tasks_available: true, temp_available: true }))
    vi.stubGlobal('fetch', mockFetch)

    await fetchStorageSettings()
    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('/settings/storage')
  })

  it('fetchDiagnosticsSettings uses GET /settings/diagnostics', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({
      api: { status: 'ok' },
      services: { total: 0, available: 0, unavailable: 0 },
      toolchain: { total: 0, available: 0, missing: 0 },
      storage: { writable: true },
      telemetry: null,
      logs: null,
      recent_errors: [],
    }))
    vi.stubGlobal('fetch', mockFetch)

    await fetchDiagnosticsSettings()
    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('/settings/diagnostics')
  })
})

describe('HTTP error handling', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('parses body.error for structured errors', async () => {
    const errorBody = {
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Invalid input',
        retryable: false,
        details: [{ provider: 'test', error_code: 'E001' }],
      },
    }
    const mockFetch = vi.fn().mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify(errorBody), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      }))
    )
    vi.stubGlobal('fetch', mockFetch)

    try {
      await fetchStyles()
      expect.fail('Should have thrown')
    } catch (err) {
      expect(err).toBeInstanceOf(MountainApiError)
      const apiErr = err as MountainApiError
      expect(apiErr.status).toBe(400)
      expect(apiErr.code).toBe('VALIDATION_ERROR')
      expect(apiErr.message).toBe('Invalid input')
      expect(apiErr.retryable).toBe(false)
      expect(apiErr.details).toEqual([{ provider: 'test', error_code: 'E001' }])
    }
  })

  it('falls back to body.detail for FastAPI errors', async () => {
    const errorBody = {
      detail: {
        code: 'NOT_FOUND',
        message: 'Resource not found',
        retryable: false,
      },
    }
    const mockFetch = vi.fn().mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify(errorBody), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      }))
    )
    vi.stubGlobal('fetch', mockFetch)

    try {
      await fetchStyles()
      expect.fail('Should have thrown')
    } catch (err) {
      expect(err).toBeInstanceOf(MountainApiError)
      const apiErr = err as MountainApiError
      expect(apiErr.status).toBe(404)
      expect(apiErr.code).toBe('NOT_FOUND')
      expect(apiErr.message).toBe('Resource not found')
    }
  })

  it('handles 204 No Content without JSON parse', async () => {
    const mockFetch = vi.fn().mockImplementation(() => noContentResponse())
    vi.stubGlobal('fetch', mockFetch)

    const result = await deleteService('s1')
    expect(result).toBeUndefined()
  })

  it('handles network errors as MountainApiError', async () => {
    const mockFetch = vi.fn().mockImplementation(() => Promise.reject(new TypeError('Failed to fetch')))
    vi.stubGlobal('fetch', mockFetch)

    try {
      await fetchStyles()
      expect.fail('Should have thrown')
    } catch (err) {
      expect(err).toBeInstanceOf(MountainApiError)
      const apiErr = err as MountainApiError
      expect(apiErr.status).toBe(0)
      expect(apiErr.code).toBe('NETWORK_ERROR')
      expect(apiErr.retryable).toBe(true)
    }
  })

  it('GET requests do not send Content-Type header', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ items: [] }))
    vi.stubGlobal('fetch', mockFetch)

    await fetchStyles()
    const [, init] = mockFetch.mock.calls[0]
    expect(init.headers?.['Content-Type']).toBeUndefined()
  })

  it('FormData requests do not send Content-Type header', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ voice_id: 'v1' }))
    vi.stubGlobal('fetch', mockFetch)

    const form = new FormData()
    form.append('name', 'Test')
    await createVoice(form)

    const [, init] = mockFetch.mock.calls[0]
    expect(init.headers?.['Content-Type']).toBeUndefined()
  })

  it('FormData removes caller Content-Type header (Title-Case)', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', mockFetch)

    const form = new FormData()
    form.append('file', new Blob(['test']), 'test.txt')
    await request('/test', {
      method: 'POST',
      body: form,
      headers: { 'Content-Type': 'application/octet-stream' },
    })

    const [, init] = mockFetch.mock.calls[0]
    expect(init.headers?.['Content-Type']).toBeUndefined()
  })

  it('FormData removes caller content-type header (lowercase)', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', mockFetch)

    const form = new FormData()
    form.append('file', new Blob(['test']), 'test.txt')
    await request('/test', {
      method: 'POST',
      body: form,
      headers: { 'content-type': 'application/octet-stream' },
    })

    const [, init] = mockFetch.mock.calls[0]
    expect(init.headers?.['content-type']).toBeUndefined()
    expect(init.headers?.['Content-Type']).toBeUndefined()
  })

  it('FormData removes caller CONTENT-TYPE header (UPPERCASE)', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', mockFetch)

    const form = new FormData()
    form.append('file', new Blob(['test']), 'test.txt')
    await request('/test', {
      method: 'POST',
      body: form,
      headers: { 'CONTENT-TYPE': 'application/octet-stream' },
    })

    const [, init] = mockFetch.mock.calls[0]
    expect(init.headers?.['CONTENT-TYPE']).toBeUndefined()
    expect(init.headers?.['Content-Type']).toBeUndefined()
  })
})

describe('Style preview upload chain', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('uploadAsset returns asset_id, then createStyle sends preview_asset_id', async () => {
    const mockFetch = vi.fn()
      // First call: upload asset
      .mockImplementationOnce(() => jsonResponse({
        asset_id: 'asset-abc123',
        filename: 'preview.png',
        content_type: 'image/png',
        size_bytes: 1024,
      }))
      // Second call: create style
      .mockImplementationOnce(() => jsonResponse({
        style_id: 'style-1',
        name: 'Test Style',
        preview_asset_id: 'asset-abc123',
      }))
    vi.stubGlobal('fetch', mockFetch)

    // Step 1: Upload file
    const file = new File(['preview data'], 'preview.png', { type: 'image/png' })
    const uploadResult = await uploadAsset(file)
    expect(uploadResult.asset_id).toBe('asset-abc123')

    // Step 2: Create style with preview_asset_id
    const styleResult = await createStyle({
      name: 'Test Style',
      preview_asset_id: uploadResult.asset_id,
    })
    expect(styleResult.style_id).toBe('style-1')

    // Verify the createStyle request body contains preview_asset_id
    const [, createInit] = mockFetch.mock.calls[1]
    const body = JSON.parse(createInit.body)
    expect(body.preview_asset_id).toBe('asset-abc123')
  })

  it('uploadAsset returns asset_id, then updateStyle sends preview_asset_id', async () => {
    const mockFetch = vi.fn()
      // First call: upload asset
      .mockImplementationOnce(() => jsonResponse({
        asset_id: 'asset-xyz789',
        filename: 'new-preview.png',
        content_type: 'image/png',
        size_bytes: 2048,
      }))
      // Second call: update style
      .mockImplementationOnce(() => jsonResponse({
        style_id: 'style-1',
        name: 'Updated Style',
        preview_asset_id: 'asset-xyz789',
      }))
    vi.stubGlobal('fetch', mockFetch)

    // Step 1: Upload file
    const file = new File(['new preview data'], 'new-preview.png', { type: 'image/png' })
    const uploadResult = await uploadAsset(file)
    expect(uploadResult.asset_id).toBe('asset-xyz789')

    // Step 2: Update style with preview_asset_id
    const updateResult = await updateStyle('style-1', {
      name: 'Updated Style',
      preview_asset_id: uploadResult.asset_id,
    })
    expect(updateResult.style_id).toBe('style-1')

    // Verify the updateStyle request body contains preview_asset_id
    const [, updateInit] = mockFetch.mock.calls[1]
    const body = JSON.parse(updateInit.body)
    expect(body.preview_asset_id).toBe('asset-xyz789')
  })

  it('upload failure does not proceed to style creation', async () => {
    const mockFetch = vi.fn()
      // First call: upload fails
      .mockImplementationOnce(() => Promise.resolve(new Response(JSON.stringify({
        error: { code: 'UPLOAD_FAILED', message: 'File too large', retryable: false },
      }), { status: 413, headers: { 'Content-Type': 'application/json' } })))
    vi.stubGlobal('fetch', mockFetch)

    const file = new File(['x'.repeat(100000000)], 'huge.png', { type: 'image/png' })

    try {
      await uploadAsset(file)
      expect.fail('Should have thrown')
    } catch (err) {
      expect(err).toBeInstanceOf(MountainApiError)
      const apiErr = err as MountainApiError
      expect(apiErr.status).toBe(413)
      expect(apiErr.code).toBe('UPLOAD_FAILED')
    }

    // Only one fetch call was made (upload), no style creation
    expect(mockFetch).toHaveBeenCalledOnce()
  })
})

describe('Style filtering and cursor pagination', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('fetchStyles sends kind, status, engine, q query params', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ items: [], next_cursor: null, total: 0 }))
    vi.stubGlobal('fetch', mockFetch)

    await fetchStyles({ kind: 'custom', status: 'active', engine: 'whiteboard', q: 'test' })

    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('kind=custom')
    expect(url).toContain('status=active')
    expect(url).toContain('engine=whiteboard')
    expect(url).toContain('q=test')
  })

  it('fetchStyles sends cursor and limit for pagination', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ items: [], next_cursor: 'cursor-abc', total: 50 }))
    vi.stubGlobal('fetch', mockFetch)

    await fetchStyles({ cursor: 'cursor-abc', limit: 20 })

    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('cursor=cursor-abc')
    expect(url).toContain('limit=20')
  })

  it('fetchStyles returns items with next_cursor for next page', async () => {
    const page1Items = [
      { style_id: 's1', name: 'Style 1', kind: 'custom', status: 'active', engine: null, revision: 1, tags: [], prompt_text: null, negative_prompt: null, preview_asset_id: null, config: {}, description: '', created_at: '2025-01-01', updated_at: '2025-01-01' },
      { style_id: 's2', name: 'Style 2', kind: 'custom', status: 'active', engine: null, revision: 1, tags: [], prompt_text: null, negative_prompt: null, preview_asset_id: null, config: {}, description: '', created_at: '2025-01-01', updated_at: '2025-01-01' },
    ]

    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({
      items: page1Items,
      next_cursor: 'page2-cursor',
      total: 5,
    }))
    vi.stubGlobal('fetch', mockFetch)

    const result = await fetchStyles({ limit: 2 })
    expect(result.items).toHaveLength(2)
    expect(result.next_cursor).toBe('page2-cursor')
    expect(result.total).toBe(5)
  })
})

describe('Voice filtering and cursor pagination', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('fetchVoices sends status and q query params', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ items: [], next_cursor: null, total: 0 }))
    vi.stubGlobal('fetch', mockFetch)

    await fetchVoices({ status: 'active', q: 'test-voice' })

    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('status=active')
    expect(url).toContain('q=test-voice')
  })

  it('fetchVoices sends cursor and limit for pagination', async () => {
    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({ items: [], next_cursor: 'voice-cursor', total: 30 }))
    vi.stubGlobal('fetch', mockFetch)

    await fetchVoices({ cursor: 'voice-cursor', limit: 10 })

    const [url] = mockFetch.mock.calls[0]
    expect(url).toContain('cursor=voice-cursor')
    expect(url).toContain('limit=10')
  })

  it('fetchVoices returns items with next_cursor for next page', async () => {
    const voiceItems = [
      { voice_id: 'v1', name: 'Voice 1', tags: [], duration_ms: 5000, sample_rate: 44100, channels: 1, format: 'wav', enabled: true, status: 'active', created_at: '2025-01-01', updated_at: '2025-01-01' },
    ]

    const mockFetch = vi.fn().mockImplementation(() => jsonResponse({
      items: voiceItems,
      next_cursor: 'voice-page2',
      total: 15,
    }))
    vi.stubGlobal('fetch', mockFetch)

    const result = await fetchVoices({ limit: 1 })
    expect(result.items).toHaveLength(1)
    expect(result.next_cursor).toBe('voice-page2')
    expect(result.total).toBe(15)
  })
})
