/* ==========================================================================
   Mountain API TypeScript DTOs
   对应 webapp/mountain_v1_api.py 的实际响应结构
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
// GET /health → { status, providers: { all_available, providers, unavailable } }

export interface ProviderAvailability {
  available: boolean
  component?: string
  error_code?: string | null
  suggestion?: string | null
}

export interface HealthResponse {
  status: string
  providers: {
    all_available: boolean
    providers: Record<string, ProviderAvailability>
    unavailable: string[]
  }
}

// ── Capabilities ────────────────────────────────────────────────────────
// GET /capabilities → { items[], providers }

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
// GET /providers → { providers: { <name>: ProviderEntry }, all_configured, all_available }

export interface ProviderProfile {
  provider_type: string
  name: string
  description: string
  required_secrets: string[]
  optional_secrets: string[]
  config: Record<string, unknown>
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

// GET /providers/{name} → { name, profile, config, config_status, availability }

export interface ProviderDetail {
  name: string
  profile: ProviderProfile
  config: Record<string, unknown>
  config_status: ConfigStatus
  availability: ProviderAvailability
}

// PUT /providers/{name}/config → { ok, provider, config }

export interface UpdateConfigResponse {
  ok: boolean
  provider: string
  config: Record<string, unknown>
}

// ── Secrets ─────────────────────────────────────────────────────────────
// GET /providers/{name}/secrets → { provider, secrets: { <key>: SecretInfo } }

export interface SecretInfo {
  configured: boolean
  masked_value: string | null
}

export interface SecretStatusResponse {
  provider: string
  secrets: Record<string, SecretInfo>
}

// POST /providers/{name}/secrets → { ok, provider, key }

export interface SetSecretRequest {
  key: string
  value: string
}

export interface SecretOperationResponse {
  ok: boolean
  provider: string
  key: string
}

// ── Tasks ────────────────────────────────────────────────────────────
// GET /tasks → { items: Task[] }
// Task.to_dict() from dataclasses.asdict()

export interface Task {
  task_id: string
  title: string
  pipeline_id: string
  engine: string
  status: string
  created_at: string
  updated_at: string
  active_run_id: string | null
  revision: number
  schema_version: number
}

export interface TaskListResponse {
  items: Task[]
}

// POST /tasks → { ok, command, task_id, run_id, trace_id, command_id, event_sequence }

export interface CreateTaskRequest {
  title: string
  engine?: string
  pipeline_id?: string
}

export interface CreateTaskResponse {
  ok: boolean
  command: string
  task_id: string
  run_id: string
  trace_id: string
  command_id: string
  event_sequence: number
}

// ── Run ─────────────────────────────────────────────────────────────────
// GET /tasks/{id}/runs/{runId} → RunView
// Run.to_dict() + computed fields

export interface RunDetail {
  schema_version: number
  run_id: string
  task_id: string
  trace_id: string
  entrypoint: string
  command_ids: string[]
  status: string
  target_stage: string | null
  started_at: string
  finished_at: string | null
  stages: Record<string, StageState>
  warnings: unknown[]
}

export interface StageState {
  status: string
  attempt: number
}

// ── Task Detail ──────────────────────────────────────────────────────
// GET /tasks/{id} → _project_detail_view()
// { project, active_run, stages, warnings, artifacts, trace }

export interface TaskDetail {
  task: Task
  active_run: RunDetail | null
  stages: StageListItem[]
  warnings: unknown[]
  artifacts: Artifact[]
  trace: TraceInfo | null
}

export interface StageListItem {
  stage: string
  status: string
  attempt: number
}

export interface TraceInfo {
  trace_id: string
  command_ids: string[]
}

// ── Units ───────────────────────────────────────────────────────────────
// GET /tasks/{id}/runs/{runId}/units → { items }
// Merged from av-plan.json voice_units + timeline.json timings

export interface Unit {
  unit_id: string
  text?: string
  order?: number
  timing?: Record<string, unknown> | null
  [key: string]: unknown
}

export interface UnitListResponse {
  items: Unit[]
}

// ── Artifacts ───────────────────────────────────────────────────────────
// GET /tasks/{id}/runs/{runId}/artifacts → { items }

export interface Artifact {
  artifact_key: string
  relative_path: string
  sha256: string
  size_bytes: number
  producer_stage: string
  status: string
}

export interface ArtifactListResponse {
  items: Artifact[]
}

// ── Events ──────────────────────────────────────────────────────────────
// GET /tasks/{id}/runs/{runId}/events?after=N → { items, next_cursor }
// Items are arbitrary event dicts from telemetry

export interface EventsResponse {
  items: Record<string, unknown>[]
  next_cursor: number
}

// ── Logs ────────────────────────────────────────────────────────────────
// GET /tasks/{id}/runs/{runId}/logs?level=&component=&stage= → { items }
// Items are parsed JSONL log entries

export interface LogsResponse {
  items: Record<string, unknown>[]
}

// ── Pipeline Run Response ───────────────────────────────────────────────
// POST /tasks/{id}/runs/{runId}/start
// POST /tasks/{id}/runs/{runId}/stages/{stage}/run
// POST /tasks/{id}/runs/{runId}/stages/{stage}/retry

export interface PipelineRunResponse {
  ok: boolean
  command: string
  task_id: string
  run_id: string
  trace_id: string
  command_id: string
  policy?: string
  stages_executed?: string[]
  results?: PipelineStageResult[]
  next_stage?: string | null
  status?: string
  message?: string
}

export interface PipelineStageResult {
  ok: boolean
  command: string
  task_id: string
  run_id: string
  stage: string
  trace_id?: string
  command_id?: string
  result?: string
  artifacts?: string[]
  event_sequence?: number
  warnings?: unknown[]
  next_stage?: string | null
  error?: {
    code: string
    message: string
    retryable: boolean
  }
}

// ── Cancel Run Response ─────────────────────────────────────────────────
// POST /tasks/{id}/runs/{runId}/cancel

export interface CancelRunResponse {
  ok: boolean
  status: string
}

// ── Save Inputs Response ────────────────────────────────────────────────
// POST /tasks/{id}/inputs (multipart/form-data)

export interface SaveInputsResponse {
  ok: boolean
  task_id: string
  input_saved: boolean
}

// GET /tasks/{id}/inputs

export interface InputsReadback {
  task_id: string
  saved: boolean
  inputs: {
    script: string
    style: string
    include_subtitles: boolean
    pen_text: string
    stroke_detail: string
  } | null
  reference_audio: {
    uploaded: boolean
    filename: string | null
    content_type: string | null
    size_bytes: number | null
  }
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
