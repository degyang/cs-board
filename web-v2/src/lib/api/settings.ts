/* ==========================================================================
   Mountain Settings API
   Runtime configuration, voice alignment, toolchain, storage, diagnostics.
   ========================================================================== */

import { get, post } from './http'
import type {
  RuntimeSettings,
  VoiceAlignmentSettings,
  ToolchainSettings,
  StorageSettings,
  DiagnosticsSettings,
} from './types'

// ---------------------------------------------------------------------------
// Runtime Settings
// ---------------------------------------------------------------------------

export function fetchRuntimeSettings(): Promise<RuntimeSettings> {
  return get('/settings/runtime')
}

export function updateRuntimeSettings(settings: Partial<RuntimeSettings>): Promise<RuntimeSettings> {
  return post('/settings/runtime', settings)
}

// ---------------------------------------------------------------------------
// Voice Alignment
// ---------------------------------------------------------------------------

export function fetchVoiceAlignment(): Promise<VoiceAlignmentSettings> {
  return get('/settings/voice-alignment')
}

export function triggerVoiceAlignment(): Promise<{ status: string }> {
  return post('/settings/voice-alignment/trigger')
}

// ---------------------------------------------------------------------------
// Toolchain
// ---------------------------------------------------------------------------

export function fetchToolchain(): Promise<ToolchainSettings> {
  return get('/settings/toolchain')
}

export function refreshToolchain(): Promise<ToolchainSettings> {
  return post('/settings/toolchain/refresh')
}

// ---------------------------------------------------------------------------
// Storage
// ---------------------------------------------------------------------------

export function fetchStorage(): Promise<StorageSettings> {
  return get('/settings/storage')
}

// ---------------------------------------------------------------------------
// Diagnostics
// ---------------------------------------------------------------------------

export function fetchDiagnostics(): Promise<DiagnosticsSettings> {
  return get('/settings/diagnostics')
}

export function triggerDiagnostics(): Promise<DiagnosticsSettings> {
  return post('/settings/diagnostics/trigger')
}
