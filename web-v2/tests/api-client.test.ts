import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MountainApiError } from '../src/lib/api/client'

// Mock fetch globally
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

// Import after mock setup
const { fetchHealth, fetchProviders, fetchProvider, createTask, updateProviderConfig } = await import('../src/lib/api/client')

describe('API Client', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  describe('fetchHealth', () => {
    it('returns health response on success', async () => {
      const mockResponse = {
        status: 'ok',
        providers: { all_available: true, providers: {}, unavailable: [] },
      }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })

      const result = await fetchHealth()
      expect(result).toEqual(mockResponse)
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/health'),
        expect.objectContaining({ headers: expect.any(Object) }),
      )
    })

    it('throws MountainApiError on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ detail: 'Internal error' }),
      })

      await expect(fetchHealth()).rejects.toThrow(MountainApiError)
    })
  })

  describe('fetchProviders', () => {
    it('returns provider list', async () => {
      const mockResponse = {
        providers: {
          text_model: {
            profile: { provider_type: 'text_model', name: 'Text Model', description: '', required_secrets: ['api_key'], optional_secrets: [], config: {} },
            config_status: { configured: false, missing_secrets: ['api_key'], configured_secrets: [], is_encrypted: false },
            availability: { available: false },
          },
        },
        all_configured: false,
        all_available: false,
      }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })

      const result = await fetchProviders()
      expect(result.providers.text_model.profile.name).toBe('Text Model')
    })
  })

  describe('createTask', () => {
    it('sends POST with title and returns task_id', async () => {
      const mockResponse = {
        task_id: 'proj-123',
        run_id: 'run-456',
        trace_id: 'trace-789',
        command_id: 'cmd-012',
      }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })

      const result = await createTask({ title: '测试任务' })
      expect(result.task_id).toBe('proj-123')
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/tasks'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ title: '测试任务' }),
        }),
      )
    })
  })

  describe('updateProviderConfig', () => {
    it('sends PUT with config payload', async () => {
      const mockResponse = { ok: true, provider: 'text_model', config: { model: 'gpt-4o-mini' } }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })

      const result = await updateProviderConfig('text_model', { model: 'gpt-4o-mini' })
      expect(result.ok).toBe(true)
      expect(result.config.model).toBe('gpt-4o-mini')
    })

    it('throws on sensitive field rejection', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ detail: '不允许更新敏感字段: api_key' }),
      })

      await expect(
        updateProviderConfig('text_model', { api_key: 'secret' }),
      ).rejects.toThrow()
    })
  })

  describe('Error handling', () => {
    it('parses CAPABILITY_NOT_AVAILABLE error', async () => {
      const errorDetail = {
        code: 'CAPABILITY_NOT_AVAILABLE',
        message: 'Provider 服务不可用',
        unavailable: ['tts'],
        details: [{ provider: 'tts', error_code: 'CONNECTION_FAILED', suggestion: '检查服务是否启动' }],
      }
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ detail: errorDetail }),
      })

      try {
        await fetchHealth()
      } catch (e) {
        expect(e).toBeInstanceOf(MountainApiError)
        const err = e as MountainApiError
        expect(err.apiError?.code).toBe('CAPABILITY_NOT_AVAILABLE')
        expect(err.apiError?.details?.[0].provider).toBe('tts')
      }
    })
  })
})
