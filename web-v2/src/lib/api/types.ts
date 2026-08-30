/* ==========================================================================
   Mountain API TypeScript DTOs
   对应 /api/v1 端点的请求/响应类型
   ========================================================================== */

// ── Stage Keys & Names ──────────────────────────────────────────────────

export type StageKey =
  | 'segment-script'
  | 'clone-voice'
  | 'plan-storyboard'
  | 'generate-illustrations'
  | 'render-visuals'
  | 'compose-video'

export const STAGE_KEYS: StageKey[] = [
  'segment-script',
  'clone-voice',
  'plan-storyboard',
  'generate-illustrations',
  'render-visuals',
  'compose-video',
]

export const STAGE_NAMES: Record<StageKey, string> = {
  'segment-script': '文案分割',
  'clone-voice': '克隆配音',
  'plan-storyboard': '拆分分镜',
  'generate-illustrations': '生成插画',
  'render-visuals': '白板渲染',
  'compose-video': '合成成片',
}

export const ENGINE_NAMES: Record<string, string> = {
  whiteboard: '白板动画',
  'infographic-remotion': '动态信息图',
}

// ── Health ──────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string
  providers: {
    all_available: boolean
    providers: Record<string, ProviderAvailability>
    unavailable: string[]
  }
}

// ── Capabilities ────────────────────────────────────────────────────────

export interface CapabilityItem {
  engine: string
  visual_source: string
  supported: boolean
  pipeline_id: string
  reason_code: string | null
}

export interface CapabilitiesResponse {
  items: CapabilityItem[]
  providers: {
    all_available: boolean
    providers: Record<string, ProviderAvailability>
    unavailable: string[]
  }
}

// ── Providers ───────────────────────────────────────────────────────────

export interface ProviderProfile {
  provider_type: string
  name: string
  description: string
  required_secrets: string[]
  optional_secrets: string[]
  config: Record<string, unknown>
}

export interface ProviderAvailability {
  available: boolean
  error_code?: string
  suggestion?: string
}

export interface ConfigStatus {
  configured: boolean
  missing_secrets: string[]
  configured_secrets: string[]
  is_encrypted: boolean
}

export interface ProviderEntry {
  profile: ProviderProfile
  config_status: ConfigStatus
  availability: ProviderAvailability
}

export interface ProviderListResponse {
  providers: Record<string, ProviderEntry>
  all_configured: boolean
  all_available: boolean
}

export interface ProviderDetail {
  name: string
  profile: ProviderProfile
  config: Record<string, unknown>
  config_status: ConfigStatus
  availability: ProviderAvailability
}

export interface UpdateConfigResponse {
  ok: boolean
  provider: string
  config: Record<string, unknown>
}

// ── Secrets ─────────────────────────────────────────────────────────────

export interface SecretInfo {
  configured: boolean
  masked_value: string | null
}

export interface SecretStatusResponse {
  provider: string
  secrets: Record<string, SecretInfo>
}

export interface SetSecretRequest {
  key: string
  value: string
}

export interface SecretOperationResponse {
  ok: boolean
  provider: string
  key: string
}

// ── Projects ────────────────────────────────────────────────────────────

export interface Project {
  project_id: string
  title: string
  status: string
  engine: string
  pipeline_id: string
  active_run_id: string | null
  created_at: string
  updated_at: string
}

export interface ProjectListResponse {
  items: Project[]
}

export interface CreateProjectRequest {
  title: string
  engine?: string
  pipeline_id?: string
}

export interface CreateProjectResponse {
  project_id: string
  run_id: string
  trace_id: string
  command_id: string
}

export interface ProjectDetail {
  project: Project
  run: RunDetail | null
}

// ── Run & Stages ────────────────────────────────────────────────────────

export interface RunDetail {
  run_id: string
  project_id: string
  trace_id: string
  entrypoint: string
  command_ids: string[]
  status: string
  target_stage: string | null
  started_at: string
  completed_at: string | null
  stages: Record<string, StageState>
  warnings: unknown[]
}

export interface StageState {
  status: string
  attempt: number
  started_at?: string
  finished_at?: string
  error?: string | null
}

// ── Units ───────────────────────────────────────────────────────────────

export interface Unit {
  unit_id: string
  text: string
  order: number
  timing?: {
    alignment_source?: string
    duration_ms?: number
    fallback?: boolean
  } | null
  visual_items?: VisualItem[]
}

export interface VisualItem {
  visual_id: string
  text: string
  status: string
}

export interface UnitListResponse {
  items: Unit[]
}

// ── Artifacts ───────────────────────────────────────────────────────────

export interface Artifact {
  artifact_key: string
  stage: string
  status: string
  sha256: string | null
  size_bytes: number | null
  created_at: string
}

export interface ArtifactListResponse {
  items: Artifact[]
}

// ── Events ──────────────────────────────────────────────────────────────

export interface RunEvent {
  sequence: number
  event_type: string
  stage: string | null
  action: string
  timestamp: string
  data: Record<string, unknown>
}

export interface EventsResponse {
  items: RunEvent[]
  next_cursor: number
}

// ── Logs ────────────────────────────────────────────────────────────────

export interface LogEntry {
  timestamp: string
  level: string
  component: string
  stage: string | null
  message: string
  trace_id: string | null
}

export interface LogsResponse {
  items: LogEntry[]
}

// ── API Error ───────────────────────────────────────────────────────────

export interface ApiError {
  code: string
  message: string
  unavailable?: string[]
  details?: Array<{
    provider: string
    error_code?: string
    suggestion?: string
  }>
}
