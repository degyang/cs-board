/* ==========================================================================
   Mountain Assets API
   Preset styles (read-only), custom styles (CRUD), voice library (CRUD).
   ========================================================================== */

import { get, del, postFormRaw } from './http'
import type {
  PresetStyle,
  CustomStyle,
  CreateCustomStyleRequest,
  VoiceAsset,
  CreateVoiceAssetRequest,
  PresetStyleListResponse,
  CustomStyleListResponse,
  VoiceAssetListResponse,
} from './types'

// ---------------------------------------------------------------------------
// Preset Styles (read-only)
// ---------------------------------------------------------------------------

export function fetchPresetStyles(): Promise<PresetStyleListResponse> {
  return get('/assets/preset-styles')
}

export function fetchPresetStyle(styleId: string): Promise<PresetStyle> {
  return get(`/assets/preset-styles/${encodeURIComponent(styleId)}`)
}

// ---------------------------------------------------------------------------
// Custom Styles (CRUD)
// ---------------------------------------------------------------------------

export function fetchCustomStyles(): Promise<CustomStyleListResponse> {
  return get('/assets/custom-styles')
}

export function fetchCustomStyle(styleId: string): Promise<CustomStyle> {
  return get(`/assets/custom-styles/${encodeURIComponent(styleId)}`)
}

export async function createCustomStyle(req: CreateCustomStyleRequest): Promise<CustomStyle> {
  const form = new FormData()
  form.set('name', req.name)
  if (req.description) form.set('description', req.description)
  form.set('category', req.category)
  for (const file of req.reference_images) {
    form.append('reference_images', file)
  }
  const res = await postFormRaw('/assets/custom-styles', form)
  return res.json() as Promise<CustomStyle>
}

export function deleteCustomStyle(styleId: string): Promise<void> {
  return del(`/assets/custom-styles/${encodeURIComponent(styleId)}`).then(() => undefined)
}

// ---------------------------------------------------------------------------
// Voice Library (CRUD)
// ---------------------------------------------------------------------------

export function fetchVoiceAssets(): Promise<VoiceAssetListResponse> {
  return get('/assets/voices')
}

export function fetchVoiceAsset(assetId: string): Promise<VoiceAsset> {
  return get(`/assets/voices/${encodeURIComponent(assetId)}`)
}

export async function createVoiceAsset(req: CreateVoiceAssetRequest): Promise<VoiceAsset> {
  const form = new FormData()
  form.set('name', req.name)
  if (req.description) form.set('description', req.description)
  form.set('audio_file', req.audio_file)
  const res = await postFormRaw('/assets/voices', form)
  return res.json() as Promise<VoiceAsset>
}

export function deleteVoiceAsset(assetId: string): Promise<void> {
  return del(`/assets/voices/${encodeURIComponent(assetId)}`).then(() => undefined)
}
