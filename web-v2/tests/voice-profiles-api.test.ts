import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  createVoiceProfile,
  createPresetVoiceProfile,
  createVoiceStyleProfile,
  fetchVoiceProfiles,
  fetchVoiceStyleProfiles,
  previewVoiceProfile,
  updateVoiceProfile,
} from '../src/lib/api/voiceProfiles'

function response(body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } }))
}

describe('provider-neutral voice profile API', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('queries profile and style catalogs by Provider', async () => {
    const fetchMock = vi.fn().mockImplementation(() => response({ items: [], next_cursor: null, total: 0 }))
    vi.stubGlobal('fetch', fetchMock)
    await fetchVoiceProfiles({ kind: 'provider-preset', provider_id: 'provider/a' })
    await fetchVoiceStyleProfiles({ provider_id: 'provider/a', status: 'active' })
    expect(String(fetchMock.mock.calls[0][0])).toContain('/voice-profiles?provider_id=provider%2Fa')
    expect(String(fetchMock.mock.calls[0][0])).not.toContain('kind=')
    expect(String(fetchMock.mock.calls[1][0])).toContain('/voice-style-profiles?provider_id=provider%2Fa')
    expect(String(fetchMock.mock.calls[1][0])).not.toContain('status=')
  })

  it('posts only the non-sensitive design and style DTO fields', async () => {
    const fetchMock = vi.fn().mockImplementation(() => response({}))
    vi.stubGlobal('fetch', fetchMock)
    await createVoiceProfile({
      name: '设计声', kind: 'provider-designed', provider_id: 'speech-provider',
      model_id: 'design-model', design_prompt: '清晰温暖', tags: ['讲解'],
    })
    await createVoiceStyleProfile({
      name: '叙述风格', provider_id: 'speech-provider', instruction: '自然叙述', tags: ['自然'],
    })
    const design = JSON.parse(fetchMock.mock.calls[0][1].body)
    const style = JSON.parse(fetchMock.mock.calls[1][1].body)
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(fetchMock.mock.calls[1][1].method).toBe('POST')
    expect(design).toEqual({ name: '设计声', kind: 'provider-designed', provider_id: 'speech-provider', model_id: 'design-model', design_prompt: '清晰温暖', tags: ['讲解'] })
    expect(style).toEqual({ name: '叙述风格', provider_id: 'speech-provider', instruction: '自然叙述', tags: ['自然'] })
    expect(`${JSON.stringify(design)}${JSON.stringify(style)}`.toLowerCase()).not.toContain('api_key')
  })

  it('posts preview text to the encoded profile endpoint and consumes the backend audio URL', async () => {
    const payload = { audio_url: '/api/v1/voice-profile-previews/p-1/content', content_type: 'audio/wav', duration_ms: 8405 }
    const fetchMock = vi.fn().mockImplementation(() => response(payload))
    vi.stubGlobal('fetch', fetchMock)

    await expect(previewVoiceProfile('mimo/冰糖', '真实预览文本')).resolves.toEqual(payload)
    expect(String(fetchMock.mock.calls[0][0])).toContain('/voice-profiles/mimo%2F%E5%86%B0%E7%B3%96/preview')
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ text: '真实预览文本' })
  })

  it('creates presets and PATCHes only server-editable metadata fields', async () => {
    const fetchMock = vi.fn().mockImplementation(() => response({}))
    vi.stubGlobal('fetch', fetchMock)
    const body = { name: '预置声', provider_id: 'configured-service', model_id: 'configured-model', remote_voice_id: 'remote-voice', language: 'zh-CN', gender: 'female', example_text: '说明', tags: ['自然'] }
    await createPresetVoiceProfile(body)
    await updateVoiceProfile('profile/a', body)
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ ...body, kind: 'provider-preset' })
    expect(String(fetchMock.mock.calls[1][0])).toContain('/voice-profiles/profile%2Fa')
    expect(fetchMock.mock.calls[1][1].method).toBe('PATCH')
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({
      name: '预置声', model_id: 'configured-model', remote_voice_id: 'remote-voice',
      language: 'zh-CN', gender: 'female', tags: ['自然'],
    })
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).not.toHaveProperty('provider_id')
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).not.toHaveProperty('example_text')
  })
})
