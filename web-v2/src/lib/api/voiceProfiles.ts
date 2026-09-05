import { get, post } from './http'
import type {
  VoiceProfileKind,
  VoiceProfileListResponse,
  VoiceProfilePreviewResponse,
  VoiceStyleProfileListResponse,
} from './types'

export interface VoiceProfileListParams {
  kind?: VoiceProfileKind
  provider_id?: string
  status?: 'active' | 'inactive'
}

function queryString(params: object): string {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (typeof value === 'string' && value) query.set(key, value)
  })
  const encoded = query.toString()
  return encoded ? `?${encoded}` : ''
}

/** Provider-neutral VoiceProfile catalog; no provider secrets enter this DTO. */
export function fetchVoiceProfiles(params: VoiceProfileListParams = {}): Promise<VoiceProfileListResponse> {
  return get<VoiceProfileListResponse>(`/voice-profiles${queryString({ provider_id: params.provider_id })}`)
    .then(response => ({
      ...response,
      items: response.items.filter(item => (!params.kind || item.kind === params.kind) && (!params.status || item.status === params.status)),
      next_cursor: response.next_cursor ?? null,
    }))
}

export function createVoiceProfile(body: {
  name: string
  kind: 'provider-designed'
  provider_id: string
  model_id: string
  design_prompt: string
  tags: string[]
}): Promise<import('./types').VoiceProfile> {
  return post('/voice-profiles', body)
}

/** Generate a real provider preview; the returned URL points at backend-owned audio content. */
export function previewVoiceProfile(profileId: string, text?: string): Promise<VoiceProfilePreviewResponse> {
  return post(`/voice-profiles/${encodeURIComponent(profileId)}/preview`, text ? { text } : {})
}

/** Reusable speaking-style profiles returned by the selected provider capability. */
export function fetchVoiceStyleProfiles(params: { provider_id?: string; status?: 'active' | 'inactive' } = {}): Promise<VoiceStyleProfileListResponse> {
  return get<VoiceStyleProfileListResponse>(`/voice-style-profiles${queryString({ provider_id: params.provider_id })}`)
    .then(response => ({
      ...response,
      items: response.items.filter(item => !params.status || item.status === params.status),
      next_cursor: response.next_cursor ?? null,
    }))
}

export function createVoiceStyleProfile(body: {
  name: string
  provider_id: string
  instruction: string
  tags: string[]
}): Promise<import('./types').VoiceStyleProfile> {
  return post('/voice-style-profiles', body)
}
