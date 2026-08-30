// API View 类型 — 对应 docs/Mountain/04-webui-redesign.md §10
// WebUI v2 只消费 API View，不导入 Python Domain，也不复制状态机或 fallback 公式

export type EngineKind = 'whiteboard' | 'infographic-remotion'
export type VisualSourceKind = 'preset' | 'custom-reference'
export type StageStatus =
  | 'pending'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'cancelled'
  | 'stale'
  | 'skipped'

export type StageKey = 'split' | 'voice' | 'storyboard' | 'illustration' | 'render' | 'compose'

export const STAGE_KEYS: StageKey[] = [
  'split',
  'voice',
  'storyboard',
  'illustration',
  'render',
  'compose',
]

export const STAGE_NAMES: Record<StageKey, string> = {
  split: '文案分割',
  voice: '克隆配音',
  storyboard: '拆分分镜',
  illustration: '生成插画',
  render: '白板渲染',
  compose: '合成成片',
}

export const ENGINE_NAMES: Record<EngineKind, string> = {
  whiteboard: '白板动画',
  'infographic-remotion': '动态信息图',
}

export const VISUAL_SOURCE_NAMES: Record<VisualSourceKind, string> = {
  preset: '预设风格',
  'custom-reference': '自定义参考',
}

export interface ArtifactView {
  artifact_id: string
  logical_key: string
  schema_version: string
  revision: number
  created_at: string
  hash: string
  content_type: string
  size_bytes: number
  status: 'ready' | 'generating' | 'stale' | 'invalid'
}

export interface VisualItemView {
  visual_id: string
  unit_id: string
  text_excerpt: string
  text_range: [number, number]
  image_artifact_id?: string
  clip_seconds?: number
  switch_point_s?: number
  status: StageStatus | 'generating'
}

export interface VoiceUnitView {
  unit_id: string
  index: number
  text: string
  char_count: number
  voice_status: StageStatus
  duration_s?: number
  alignment: 'whisper' | 'fallback'
  fallback_reason?: string
  alignment_coverage?: number
  visuals: VisualItemView[]
}

export interface ErrorChainView {
  error_code: string
  retryable: boolean
  message: string
  suggestion: string
  stage?: StageKey
  unit_id?: string
  visual_id?: string
}

export interface StageSummary {
  stage: StageKey
  status: StageStatus
  started_at?: string
  ended_at?: string
  progress?: string
  error?: ErrorChainView
}

export interface RunView {
  run_id: string
  project_id: string
  trace_id: string
  command_id: string
  status: StageStatus
  strategy: 'auto' | 'stepwise'
  pipeline_version: string
  started_at: string
  stages: StageSummary[]
  voice_units: VoiceUnitView[]
  artifacts: ArtifactView[]
  whisper_aligned: number
  fallback_units: number
}

export interface RunRefView {
  run_id: string
  trace_id: string
  status: StageStatus
  current_stage?: StageKey
  voice_done: number
  voice_total: number
  visual_done: number
  visual_total: number
  whisper_aligned: number
  fallback: number
  last_entry: 'web' | 'desktop' | 'cli' | 'skill'
}

export interface ProjectSummaryView {
  project_id: string
  name: string
  created_at: string
  updated_at: string
  engine: EngineKind
  visual_source: VisualSourceKind
  pipeline_version: string
  legacy?: boolean
  final_video_artifact?: string
  run?: RunRefView
}

export interface ProjectDetailView {
  project: ProjectSummaryView
  run: RunView
}

export interface CapabilityView {
  engine: EngineKind
  visual_source: VisualSourceKind
  supported: boolean
  pipeline?: string
  reason?: string
}

export interface ServiceHealthView {
  component: string
  title: string
  status: 'ok' | 'degraded' | 'down'
  version: string
  detail?: string
}

export interface SettingsItemView {
  key: string
  label: string
  value: string
  note?: string
  has_secret?: boolean
  secret_ref?: string
}

export interface SettingsSectionView {
  key: string
  title: string
  items: SettingsItemView[]
}

export interface TraceEventView {
  cursor: number
  ts: string
  kind: string
  stage?: StageKey
  unit_id?: string
  visual_id?: string
  message: string
}

export type LogLevel = 'debug' | 'info' | 'warn' | 'error'

export interface LogEntryView {
  ts: string
  level: LogLevel
  component: string
  stage?: StageKey
  unit_id?: string
  visual_id?: string
  provider?: string
  message: string
}

export interface ProviderLatency {
  p50: number
  p95: number
  retries: number
}

export interface RunMetricsView {
  stage_durations_s: Record<string, number>
  provider_latency_ms: Record<string, ProviderLatency>
  tts_total_s: number
  whisper_total_s: number
  render_total_s: number
  fallback_ratio: number
  av_drift_ms: number
}

export interface DiagnosticBundleView {
  bundle_id: string
  created_at: string
  trace_id: string
  redacted: boolean
  size_bytes: number
}

export interface CurrentRunInfo {
  project_id: string
  project_name: string
  run_id: string
  trace_id: string
  status: StageStatus
  current_stage: StageKey
}

