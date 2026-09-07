/* ==========================================================================
   Mountain Assets API
   Styles (preset + custom), read-only preconditions, and voices.
   ========================================================================== */

import { get, post, patch, del, postForm, getVoiceContentUrl, getAssetBlobUrl } from './http'
import type {
  StyleTemplate,
  StyleListResponse,
  StyleListParams,
  VoiceDefinition,
  VoiceListResponse,
  VoiceListParams,
  PreconditionListResponse,
  Precondition,
} from './types'

export { getVoiceContentUrl, getAssetBlobUrl }

/** Response from POST /api/v1/assets/uploads */
export interface UploadResponse {
  asset_id: string
  filename: string
  content_type: string
  size_bytes: number
}

/**
 * Upload a file to /api/v1/assets/uploads.
 * Returns asset_id for use in style preview_asset_id.
 */
export function uploadAsset(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  return postForm('/assets/uploads', form)
}

// ---------------------------------------------------------------------------
// Styles (preset + custom, unified endpoint)
// ---------------------------------------------------------------------------

export function fetchStyles(params: StyleListParams = {}): Promise<StyleListResponse> {
  const qs = new URLSearchParams()
  if (params.kind) qs.set('kind', params.kind)
  if (params.status) qs.set('status', params.status)
  if (params.engine) qs.set('engine', params.engine)
  if (params.q) qs.set('q', params.q)
  if (params.cursor) qs.set('cursor', params.cursor)
  if (params.limit) qs.set('limit', String(params.limit))
  const query = qs.toString()
  return get(`/assets/styles${query ? `?${query}` : ''}`)
}

export function fetchStyle(styleId: string): Promise<StyleTemplate> {
  return get(`/assets/styles/${encodeURIComponent(styleId)}`)
}

export function createStyle(body: {
  kind?: 'preset' | 'custom'
  name: string
  description?: string
  engine?: string
  prompt_text?: string
  negative_prompt?: string
  tags?: string[]
  preview_asset_id?: string
  characters?: import('./types').StyleCharacter[]
}): Promise<StyleTemplate> {
  return post('/assets/styles', body)
}

export function updateStyle(
  styleId: string,
  body: {
    name?: string
    description?: string
    engine?: string
    prompt_text?: string
    negative_prompt?: string
    tags?: string[]
    preview_asset_id?: string
    characters?: import('./types').StyleCharacter[]
    config?: import('./types').StyleTemplate['config']
    expected_revision?: number
  },
): Promise<StyleTemplate> {
  return patch(`/assets/styles/${encodeURIComponent(styleId)}`, body)
}

export function deleteStyle(styleId: string): Promise<void> {
  return del(`/assets/styles/${encodeURIComponent(styleId)}`)
}

export function activateStyle(styleId: string): Promise<StyleTemplate> {
  return post(`/assets/styles/${encodeURIComponent(styleId)}/activate`)
}

export function deactivateStyle(styleId: string): Promise<StyleTemplate> {
  return post(`/assets/styles/${encodeURIComponent(styleId)}/deactivate`)
}

// ---------------------------------------------------------------------------
// Preconditions (read-only catalog; no Task selection or mutation contract)
// ---------------------------------------------------------------------------

export function fetchPreconditions(): Promise<PreconditionListResponse> {
  return get('/assets/preconditions')
}

export function fetchPrecondition(preconditionId: string): Promise<Precondition> {
  return get(`/assets/preconditions/${encodeURIComponent(preconditionId)}`)
}

// ---------------------------------------------------------------------------
// Voices
// ---------------------------------------------------------------------------

type VoiceApiDto = Omit<VoiceDefinition, 'enabled' | 'status'> & {
  enabled?: boolean
  status?: 'active' | 'inactive'
  is_active?: boolean
}

/** Normalize the live Mountain DTO (`is_active`) for all UI consumers. */
function normalizeVoice(voice: VoiceApiDto): VoiceDefinition {
  const active = typeof voice.is_active === 'boolean'
    ? voice.is_active
    : voice.status
      ? voice.status === 'active'
      : voice.enabled === true
  return { ...voice, is_active: active, enabled: active, status: active ? 'active' : 'inactive' }
}

export async function fetchVoices(params: VoiceListParams = {}): Promise<VoiceListResponse> {
  const qs = new URLSearchParams()
  if (params.status) qs.set('status', params.status)
  if (params.q) qs.set('q', params.q)
  if (params.cursor) qs.set('cursor', params.cursor)
  if (params.limit) qs.set('limit', String(params.limit))
  const query = qs.toString()
  const response = await get<VoiceListResponse & { items: VoiceApiDto[] }>(`/assets/voices${query ? `?${query}` : ''}`)
  return { ...response, items: response.items.map(normalizeVoice) }
}

export async function fetchVoice(voiceId: string): Promise<VoiceDefinition> {
  return normalizeVoice(await get<VoiceApiDto>(`/assets/voices/${encodeURIComponent(voiceId)}`))
}

export async function createVoice(form: FormData): Promise<VoiceDefinition> {
  return normalizeVoice(await postForm<VoiceApiDto>('/assets/voices', form))
}

export async function updateVoice(
  voiceId: string,
  body: {
    name?: string; tags?: string[]; language?: string; emotion_mode?: string
    example_text?: string; availability_status?: 'available' | 'verified' | 'limited'
    status_note?: string; engine?: string
    compatibility?: VoiceDefinition['compatibility']
  },
): Promise<VoiceDefinition> {
  return normalizeVoice(await patch<VoiceApiDto>(`/assets/voices/${encodeURIComponent(voiceId)}`, body))
}

export function deleteVoice(voiceId: string): Promise<void> {
  return del(`/assets/voices/${encodeURIComponent(voiceId)}`)
}

export async function activateVoice(voiceId: string): Promise<VoiceDefinition> {
  return normalizeVoice(await post<VoiceApiDto>(`/assets/voices/${encodeURIComponent(voiceId)}/activate`))
}

export async function deactivateVoice(voiceId: string): Promise<VoiceDefinition> {
  return normalizeVoice(await post<VoiceApiDto>(`/assets/voices/${encodeURIComponent(voiceId)}/deactivate`))
}
