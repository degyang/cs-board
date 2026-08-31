/* ==========================================================================
   Mountain Assets API
   Styles (preset + custom) and voices.
   ========================================================================== */

import { get, post, patch, del, postForm, getVoiceContentUrl, getAssetBlobUrl } from './http'
import type {
  StyleTemplate,
  StyleListResponse,
  StyleListParams,
  VoiceDefinition,
  VoiceListResponse,
  VoiceListParams,
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
  name: string
  description?: string
  engine?: string
  prompt_text?: string
  negative_prompt?: string
  tags?: string[]
  preview_asset_id?: string
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

export function copyStyle(styleId: string): Promise<StyleTemplate> {
  return post(`/assets/styles/${encodeURIComponent(styleId)}/copy`)
}

// ---------------------------------------------------------------------------
// Voices
// ---------------------------------------------------------------------------

export function fetchVoices(params: VoiceListParams = {}): Promise<VoiceListResponse> {
  const qs = new URLSearchParams()
  if (params.status) qs.set('status', params.status)
  if (params.q) qs.set('q', params.q)
  if (params.cursor) qs.set('cursor', params.cursor)
  if (params.limit) qs.set('limit', String(params.limit))
  const query = qs.toString()
  return get(`/assets/voices${query ? `?${query}` : ''}`)
}

export function fetchVoice(voiceId: string): Promise<VoiceDefinition> {
  return get(`/assets/voices/${encodeURIComponent(voiceId)}`)
}

export async function createVoice(form: FormData): Promise<VoiceDefinition> {
  return postForm('/assets/voices', form)
}

export function updateVoice(
  voiceId: string,
  body: { name?: string; tags?: string[] },
): Promise<VoiceDefinition> {
  return patch(`/assets/voices/${encodeURIComponent(voiceId)}`, body)
}

export function deleteVoice(voiceId: string): Promise<void> {
  return del(`/assets/voices/${encodeURIComponent(voiceId)}`)
}

export function activateVoice(voiceId: string): Promise<VoiceDefinition> {
  return post(`/assets/voices/${encodeURIComponent(voiceId)}/activate`)
}

export function deactivateVoice(voiceId: string): Promise<VoiceDefinition> {
  return post(`/assets/voices/${encodeURIComponent(voiceId)}/deactivate`)
}
