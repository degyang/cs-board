/* ==========================================================================
   Mountain Settings API
   All settings endpoints are GET-only. Refresh by re-fetching.
   ========================================================================== */

import { get } from './http'
import type {
  RuntimeSettings,
  VoiceAlignmentSettings,
  ToolchainSettings,
  StorageSettings,
  DiagnosticsSettings,
} from './types'

export function fetchRuntimeSettings(): Promise<RuntimeSettings> {
  return get('/settings/runtime')
}

export function fetchVoiceAlignment(): Promise<VoiceAlignmentSettings> {
  return get('/settings/voice-alignment')
}

export function fetchToolchain(): Promise<ToolchainSettings> {
  return get('/settings/toolchain')
}

export function fetchStorage(): Promise<StorageSettings> {
  return get('/settings/storage')
}

export function fetchDiagnostics(): Promise<DiagnosticsSettings> {
  return get('/settings/diagnostics')
}

/** Aliased names used by pages and tests */
export const fetchVoiceAlignmentSettings = fetchVoiceAlignment
export const fetchToolchainSettings = fetchToolchain
export const fetchStorageSettings = fetchStorage
export const fetchDiagnosticsSettings = fetchDiagnostics
