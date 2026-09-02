/* ==========================================================================
   Mountain API TypeScript DTOs
   对应 webapp/mountain_v1_api.py 的实际响应结构
   ========================================================================== */

// ── Stage Keys & Names ──────────────────────────────────────────────────

export type StageKey =
  | 'generate-visual-anchors'
  | 'clone-voice'
  | 'plan-storyboard'
  | 'generate-illustrations'
  | 'render-visuals'
  | 'compose-video'

export type ExecutionMode = 'auto' | 'selective'

/** Persisted execution decision. `manual_stages` is always canonical stage order. */
export interface ExecutionPlan {
  mode: ExecutionMode
  manual_stages: StageKey[]
}

export const STAGE_KEYS: StageKey[] = [
  'generate-visual-anchors',
  'clone-voice',
  'plan-storyboard',
  'generate-illustrations',
  'render-visuals',
  'compose-video',
]

export const STAGE_NAMES: Record<StageKey, string> = {
  'generate-visual-anchors': '文案整理与画面锚定重点',
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

// ── Tasks ───────────────────────────────────────────────────────────────

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

export interface ActiveRunSummary {
  run_id: string
  status: string
  current_stage: string | null
  started_at: string
  retryable: boolean
  error_code: string | null
  final_available: boolean
  fallback_unit_count: number | null
}

export interface TaskQueueItem extends Task {
  active_run: ActiveRunSummary | null
}

export interface TaskListResponse {
  items: TaskQueueItem[]
  next_cursor: string | null
}

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

// ── Task Detail ─────────────────────────────────────────────────────────

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

// ── Events & Logs ───────────────────────────────────────────────────────

export interface EventsResponse {
  items: Record<string, unknown>[]
  next_cursor: number
}

export interface LogsResponse {
  items: Record<string, unknown>[]
}

// ── Pipeline Run ────────────────────────────────────────────────────────

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

export interface CancelRunResponse {
  ok: boolean
  status: string
}

export interface SaveInputsResponse {
  ok: boolean
  task_id: string
  input_saved: boolean
  execution_plan: ExecutionPlan
}

export interface VoiceUnitDTO {
  unit_id: string
  order: number
  source_range: { start: number; end: number }
  text: string
}

export interface ScriptPreparation {
  algorithm_version: string
  rules: { target_chars: number; min_chars: number; max_chars: number }
  voice_units: VoiceUnitDTO[]
}

export interface InputsRules {
  target_chars: number
  min_chars: number
  max_chars: number
}

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
  rules: InputsRules | null
  script_preparation: ScriptPreparation | null
  visual_anchor_enabled: boolean
  execution_plan: ExecutionPlan
}

export interface ApiError {
  code: string
  message: string
  retryable?: boolean
  unavailable?: string[]
  details?: Record<string, unknown> | null
}

export interface ErrorResponse {
  error: ApiError
}

// ==========================================================================
// NEW: Services, Assets, Settings
// ==========================================================================

// ── Services (dynamic, extensible) ──────────────────────────────────────

/** Extensible string — backend may add new capabilities */
export type ServiceCapability = string

/** Extensible string — backend may add new adapter types */
export type AdapterType = string

/** Known capabilities with display names */
export const KNOWN_CAPABILITIES: Record<string, string> = {
  text_generation: '文本生成',
  image_generation: '图像生成',
  video_generation: '视频生成',
  speech_synthesis: '语音合成',
  speech_alignment: '语音对齐',
  rendering: '渲染',
  media: '媒体处理',
  codex_skill: 'Codex 技能',
}

/** Known adapters with display names */
export const KNOWN_ADAPTERS: Record<string, string> = {
  openai_compatible: 'OpenAI 兼容',
  indextts: 'IndexTTS',
  whisper: 'Whisper',
  codex_skill: 'Codex 技能',
  ffmpeg: 'FFmpeg',
  local_process: '本地进程',
}

/** Capability categories for grouping */
export const CAPABILITY_CATEGORIES: Record<string, { label: string; capabilities: string[] }> = {
  ai_generation: {
    label: 'AI 生成',
    capabilities: ['text_generation', 'image_generation', 'video_generation'],
  },
  speech: {
    label: '语音',
    capabilities: ['speech_synthesis', 'speech_alignment'],
  },
  media: {
    label: '媒体',
    capabilities: ['rendering', 'media'],
  },
  other: {
    label: '其他',
    capabilities: ['codex_skill'],
  },
}

export interface ServiceAvailability {
  available: boolean
  checked_at: string | null
  latency_ms: number | null
  component: string | null
  error_code: string | null
  suggestion: string | null
}

/** Structured config status */
export interface ServiceConfigStatus {
  configured: boolean
  missing_fields: string[]
  missing_secrets: string[]
}

/** Structured secret status */
export interface ServiceSecretStatus {
  configured: boolean
  required: string[]
  missing: string[]
}

export interface ServiceDefinition {
  schema_version: number
  revision: number
  service_id: string
  display_name: string
  capability: ServiceCapability
  adapter_type: AdapterType
  endpoint: string | null
  model: string | null
  enabled: boolean
  priority: number
  is_default: boolean
  config: Record<string, unknown>
  required_secrets: string[]
  optional_secrets: string[]
  config_status: ServiceConfigStatus
  availability: ServiceAvailability
  secret_status: ServiceSecretStatus
  created_at: string
  updated_at: string
}

export interface ServiceListResponse {
  items: ServiceDefinition[]
  next_cursor: string | null
  total: number
}

export interface ServiceSecretListResponse {
  items: ServiceSecret[]
  total: number
}

export interface ServiceSecret {
  secret_key: string
  configured: boolean
  masked_value: string | null
  updated_at: string | null
}

// ── Assets: Styles ──────────────────────────────────────────────────────

export interface StyleTemplate {
  style_id: string
  kind: 'preset' | 'custom'
  name: string
  description: string
  engine: string | null
  status: 'active' | 'inactive'
  revision: number
  tags: string[]
  prompt_text: string | null
  negative_prompt: string | null
  preview_asset_id: string | null
  config: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface StyleListResponse {
  items: StyleTemplate[]
  next_cursor: string | null
  total: number
}

export interface StyleListParams {
  kind?: 'preset' | 'custom'
  status?: 'active' | 'inactive'
  engine?: string
  q?: string
  cursor?: string
  limit?: number
}

export interface CreateStyleRequest {
  name: string
  description?: string
  engine?: string
  prompt_text?: string
  negative_prompt?: string
  tags?: string[]
  preview_asset_id?: string
  reference_images?: File[]
}

export interface UpdateStyleRequest {
  name?: string
  description?: string
  engine?: string
  prompt_text?: string
  negative_prompt?: string
  tags?: string[]
  preview_asset_id?: string
}

// ── Assets: Voices ──────────────────────────────────────────────────────

export interface VoiceDefinition {
  voice_id: string
  name: string
  description?: string
  tags: string[]
  duration_ms: number
  sample_rate: number | null
  channels: number | null
  format: string | null
  enabled: boolean
  status: 'active' | 'inactive'
  content_url?: string | null
  created_at: string
  updated_at: string
}

/** Unified voice DTO name — alias for VoiceDefinition */
export type VoiceAsset = VoiceDefinition

export interface VoiceListResponse {
  items: VoiceDefinition[]
  next_cursor: string | null
  total: number
}

export interface VoiceListParams {
  status?: 'active' | 'inactive'
  q?: string
  cursor?: string
  limit?: number
}

export interface CreateVoiceRequest {
  name: string
  tags?: string[]
  audio_file: File
}

export interface UpdateVoiceRequest {
  name?: string
  tags?: string[]
}

// ── Settings ────────────────────────────────────────────────────────────

export interface RuntimeSettings {
  task_runner: {
    enabled: boolean
    max_concurrent_tasks: number
  }
  global_defaults: Record<string, unknown>
}

export interface VoiceAlignmentServiceSummary {
  service_id: string
  display_name: string
  capability: string
  adapter_type: string
  endpoint: string | null
  model: string | null
  timeout: number | null
  availability: ServiceAvailability
}

export interface ProbeSummary {
  available: boolean
  checked_at: string | null
  latency_ms: number | null
  component: string | null
  error_code: string | null
  suggestion: string | null
}

export interface VoiceAlignmentSettings {
  speech_synthesis: VoiceAlignmentServiceSummary | null
  speech_alignment: VoiceAlignmentServiceSummary | null
  indextts: ProbeSummary | null
  whisper: ProbeSummary | null
}

export interface ToolchainComponent {
  component: string
  available: boolean
  version: string | null
  error_code: string | null
  suggestion: string | null
}

export interface ToolchainSettings {
  tools: ToolchainComponent[]
}

export interface StorageSettings {
  writable: boolean
  assets_available: boolean
  tasks_available: boolean
  temp_available: boolean
  free_bytes: number | null
  used_bytes: number | null
  cleanup_policy: string | null
  error_code: string | null
  suggestion: string | null
}

export interface DiagnosticsApiStatus {
  status: string
  endpoint: string | null
  latency_ms: number | null
}

export interface DiagnosticsServiceSummary {
  total: number
  available: number
  unavailable: number
}

export interface DiagnosticsToolchainSummary {
  total: number
  available: number
  missing: number
}

export interface DiagnosticsStorageSummary {
  writable: boolean
  free_bytes: number | null
  used_bytes: number | null
}

export interface DiagnosticsTelemetry {
  enabled: boolean
  endpoint: string | null
}

export interface DiagnosticsLogs {
  recent_errors: number
  log_path: string | null
}

export interface DiagnosticsRecentError {
  timestamp: string
  component: string
  message: string
}

export interface DiagnosticsSettings {
  api: DiagnosticsApiStatus
  services: DiagnosticsServiceSummary
  toolchain: DiagnosticsToolchainSummary
  storage: DiagnosticsStorageSummary
  telemetry: DiagnosticsTelemetry | null
  logs: DiagnosticsLogs | null
  recent_errors: DiagnosticsRecentError[]
}
