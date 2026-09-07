import { get, patch, post } from './http'
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

export interface PresetVoiceProfileInput {
  name: string
  provider_id: string
  model_id: string
  remote_voice_id: string
  language?: string
  gender?: string
  example_text?: string
  tags: string[]
}

/** Persist user-managed preset metadata; provider identity remains explicit. */
export function createPresetVoiceProfile(body: PresetVoiceProfileInput): Promise<import('./types').VoiceProfile> {
  return post('/voice-profiles', { ...body, kind: 'provider-preset' })
}

export function updateVoiceProfile(profileId: string, body: PresetVoiceProfileInput): Promise<import('./types').VoiceProfile> {
  // The profile's Provider is its catalog identity, not an editable PATCH
  // field.  The server accepts metadata changes only; sending a binding here
  // made the UI imply a Provider switch that the API cannot perform.
  const { provider_id: _providerId, example_text: _exampleText, ...update } = body
  return patch(`/voice-profiles/${encodeURIComponent(profileId)}`, update)
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
