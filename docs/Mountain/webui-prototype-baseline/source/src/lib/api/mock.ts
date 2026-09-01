// Mock View 数据 — 后端 API 就绪前的前端开发基线
// 结构严格对齐 types.ts 的 View 契约，后端就绪后由 client.ts 切换到真实 /api
import type {
  CapabilityView,
  CurrentRunInfo,
  DiagnosticBundleView,
  EngineKind,
  ErrorChainView,
  LogEntryView,
  ProjectDetailView,
  ProjectSummaryView,
  RunMetricsView,
  RunView,
  ServiceHealthView,
  SettingsSectionView,
  TraceEventView,
  VisualSourceKind,
  VoiceUnitView,
} from './types'

const T = (h: number, m: number) => `2026-08-29T${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:00+08:00`

// ---------------------------------------------------------------- 项目列表
export const projects: ProjectSummaryView[] = [
  {
    project_id: 'p-2401',
    name: '量子计算十分钟科普',
    created_at: T(9, 12),
    updated_at: T(13, 40),
    engine: 'whiteboard',
    visual_source: 'preset',
    pipeline_version: 'mountain-av-v1',
    run: {
      run_id: 'run-77c3',
      trace_id: 'tr-8f3a-c24e-11aa',
      status: 'running',
      current_stage: 'illustration',
      voice_done: 24,
      voice_total: 24,
      visual_done: 35,
      visual_total: 48,
      whisper_aligned: 21,
      fallback: 3,
      last_entry: 'web',
    },
  },
  {
    project_id: 'p-2390',
    name: '时间管理方法论 · 读书笔记',
    created_at: '2026-08-27T15:02:00+08:00',
    updated_at: '2026-08-27T17:41:00+08:00',
    engine: 'whiteboard',
    visual_source: 'preset',
    pipeline_version: 'mountain-av-v1',
    final_video_artifact: 'video/final.mp4',
    run: {
      run_id: 'run-71b8',
      trace_id: 'tr-2d90-af13-77bc',
      status: 'succeeded',
      voice_done: 18,
      voice_total: 18,
      visual_done: 26,
      visual_total: 26,
      whisper_aligned: 18,
      fallback: 0,
      last_entry: 'skill',
    },
  },
  {
    project_id: 'p-2387',
    name: '习惯的力量：微习惯养成',
    created_at: '2026-08-26T10:20:00+08:00',
    updated_at: '2026-08-26T10:58:00+08:00',
    engine: 'whiteboard',
    visual_source: 'preset',
    pipeline_version: 'mountain-av-v1',
    run: {
      run_id: 'run-70a2',
      trace_id: 'tr-51cc-9e02-33df',
      status: 'failed',
      current_stage: 'voice',
      voice_done: 6,
      voice_total: 16,
      visual_done: 0,
      visual_total: 22,
      whisper_aligned: 6,
      fallback: 0,
      last_entry: 'desktop',
    },
  },
  {
    project_id: 'p-2375',
    name: '长期主义思维',
    created_at: '2026-08-24T21:05:00+08:00',
    updated_at: '2026-08-24T22:10:00+08:00',
    engine: 'whiteboard',
    visual_source: 'preset',
    pipeline_version: 'mountain-av-v1',
    run: {
      run_id: 'run-6d41',
      trace_id: 'tr-c4e1-08ab-9910',
      status: 'cancelled',
      current_stage: 'storyboard',
      voice_done: 11,
      voice_total: 11,
      visual_done: 14,
      visual_total: 14,
      whisper_aligned: 11,
      fallback: 0,
      last_entry: 'cli',
    },
  },
  {
    project_id: 'p-1902',
    name: '旧版 · 认知偏差速览',
    created_at: '2026-06-11T09:00:00+08:00',
    updated_at: '2026-06-11T12:30:00+08:00',
    engine: 'whiteboard',
    visual_source: 'preset',
    pipeline_version: 'legacy-sync-v0',
    legacy: true,
    final_video_artifact: 'video/final.mp4',
    run: {
      run_id: 'run-1902',
      trace_id: 'tr-legacy-1902',
      status: 'succeeded',
      voice_done: 15,
      voice_total: 15,
      visual_done: 15,
      visual_total: 15,
      whisper_aligned: 0,
      fallback: 15,
      last_entry: 'web',
    },
  },
]

// ---------------------------------------------------------------- Voice Units（p-2401，节选前 5 个单元，实际 24 个）
const units: VoiceUnitView[] = [
  {
    unit_id: 'u-01',
    index: 1,
    text: '你有没有想过，为什么一台量子计算机，能在几分钟内完成传统超算需要上万年的计算？',
    char_count: 44,
    voice_status: 'succeeded',
    duration_s: 12.4,
    alignment: 'whisper',
    alignment_coverage: 0.97,
    visuals: [
      { visual_id: 'v-01-01', unit_id: 'u-01', text_excerpt: '为什么量子计算机……', text_range: [0, 22], image_artifact_id: 'art-v03', clip_seconds: 6.8, switch_point_s: 0, status: 'succeeded' },
      { visual_id: 'v-01-02', unit_id: 'u-01', text_excerpt: '几分钟 vs 上万年', text_range: [23, 44], image_artifact_id: 'art-v04', clip_seconds: 5.6, switch_point_s: 6.8, status: 'succeeded' },
    ],
  },
  {
    unit_id: 'u-02',
    index: 2,
    text: '答案藏在一个反直觉的物理现象里：叠加态。经典比特只能是 0 或 1，而量子比特可以同时处于 0 和 1。',
    char_count: 52,
    voice_status: 'succeeded',
    duration_s: 14.9,
    alignment: 'whisper',
    alignment_coverage: 0.94,
    visuals: [
      { visual_id: 'v-02-01', unit_id: 'u-02', text_excerpt: '反直觉的叠加态', text_range: [0, 18], image_artifact_id: 'art-v05', clip_seconds: 8.1, switch_point_s: 0, status: 'succeeded' },
      { visual_id: 'v-02-02', unit_id: 'u-02', text_excerpt: '经典比特 vs 量子比特', text_range: [19, 52], image_artifact_id: 'art-v06', clip_seconds: 6.8, switch_point_s: 8.1, status: 'succeeded' },
    ],
  },
  {
    unit_id: 'u-03',
    index: 3,
    text: '更妙的是纠缠：两个量子比特一旦纠缠，测量其中一个，另一个的状态会瞬间确定，无论相隔多远。',
    char_count: 46,
    voice_status: 'succeeded',
    duration_s: 13.2,
    alignment: 'fallback',
    fallback_reason: 'Whisper 置信度低于阈值 0.62（实际 0.58），已按平均切图 fallback',
    visuals: [
      { visual_id: 'v-03-01', unit_id: 'u-03', text_excerpt: '量子纠缠示意', text_range: [0, 23], image_artifact_id: 'art-v07', clip_seconds: 6.6, switch_point_s: 0, status: 'succeeded' },
      { visual_id: 'v-03-02', unit_id: 'u-03', text_excerpt: '瞬间确定状态', text_range: [24, 46], image_artifact_id: 'art-v08', clip_seconds: 6.6, switch_point_s: 6.6, status: 'generating' },
    ],
  },
  {
    unit_id: 'u-04',
    index: 4,
    text: '不过量子计算并不是万能的。它只在特定问题上具有指数级加速，比如因数分解、量子模拟和优化搜索。',
    char_count: 49,
    voice_status: 'succeeded',
    duration_s: 13.8,
    alignment: 'whisper',
    alignment_coverage: 0.96,
    visuals: [
      { visual_id: 'v-04-01', unit_id: 'u-04', text_excerpt: '不是万能的', text_range: [0, 16], image_artifact_id: 'art-v09', clip_seconds: 7.2, switch_point_s: 0, status: 'succeeded' },
      { visual_id: 'v-04-02', unit_id: 'u-04', text_excerpt: '三类加速问题', text_range: [17, 49], image_artifact_id: 'art-v10', clip_seconds: 6.6, switch_point_s: 7.2, status: 'succeeded' },
    ],
  },
  {
    unit_id: 'u-05',
    index: 5,
    text: '今天的量子计算机仍处于含噪声中等规模时代，纠错是通往实用化的最大关卡。',
    char_count: 35,
    voice_status: 'succeeded',
    duration_s: 10.1,
    alignment: 'whisper',
    alignment_coverage: 0.98,
    visuals: [
      { visual_id: 'v-05-01', unit_id: 'u-05', text_excerpt: 'NISQ 时代', text_range: [0, 17], image_artifact_id: 'art-v11', clip_seconds: 5.4, switch_point_s: 0, status: 'succeeded' },
      { visual_id: 'v-05-02', unit_id: 'u-05', text_excerpt: '纠错关卡', text_range: [18, 35], image_artifact_id: 'art-v12', clip_seconds: 4.7, switch_point_s: 5.4, status: 'pending' },
    ],
  },
]

// ---------------------------------------------------------------- Run View（p-2401）
const run2401: RunView = {
  run_id: 'run-77c3',
  project_id: 'p-2401',
  trace_id: 'tr-8f3a-c24e-11aa',
  command_id: 'cmd-3e19',
  status: 'running',
  strategy: 'auto',
  pipeline_version: 'mountain-av-v1',
  started_at: T(9, 14),
  stages: [
    { stage: 'split', status: 'succeeded', started_at: T(9, 14), ended_at: T(9, 15), progress: '24 units / 48 visuals' },
    { stage: 'voice', status: 'succeeded', started_at: T(9, 15), ended_at: T(9, 41), progress: '24/24 单元' },
    { stage: 'storyboard', status: 'succeeded', started_at: T(9, 41), ended_at: T(9, 44), progress: '48 visuals' },
    { stage: 'illustration', status: 'running', started_at: T(9, 44), progress: '35/48' },
    { stage: 'render', status: 'pending' },
    { stage: 'compose', status: 'pending' },
  ],
  voice_units: units,
  artifacts: [
    { artifact_id: 'art-01', logical_key: 'storyboard/plan.json', schema_version: 'storyboard.plan/v2', revision: 1, created_at: T(9, 44), hash: 'sha256:4b1c…e7a2', content_type: 'application/json', size_bytes: 48211, status: 'ready' },
    { artifact_id: 'art-02', logical_key: 'voice/master.wav', schema_version: 'audio.master/v1', revision: 2, created_at: T(9, 41), hash: 'sha256:9f21…c0d4', content_type: 'audio/wav', size_bytes: 18432000, status: 'ready' },
    { artifact_id: 'art-v03', logical_key: 'visual/u01-v01.png', schema_version: 'visual.image/v1', revision: 1, created_at: T(10, 2), hash: 'sha256:77aa…19ff', content_type: 'image/png', size_bytes: 524288, status: 'ready' },
    { artifact_id: 'art-v04', logical_key: 'visual/u01-v02.png', schema_version: 'visual.image/v1', revision: 2, created_at: T(11, 18), hash: 'sha256:30de…84c1', content_type: 'image/png', size_bytes: 507904, status: 'ready' },
    { artifact_id: 'art-v07', logical_key: 'visual/u03-v01.png', schema_version: 'visual.image/v1', revision: 1, created_at: T(12, 40), hash: 'sha256:c2f8…0a63', content_type: 'image/png', size_bytes: 498073, status: 'ready' },
    { artifact_id: 'art-v08', logical_key: 'visual/u03-v02.png', schema_version: 'visual.image/v1', revision: 1, created_at: T(13, 39), hash: '—', content_type: 'image/png', size_bytes: 0, status: 'generating' },
    { artifact_id: 'art-05', logical_key: 'subtitle/draft.vtt', schema_version: 'subtitle.vtt/v1', revision: 1, created_at: T(9, 41), hash: 'sha256:1d0f…9b33', content_type: 'text/vtt', size_bytes: 15360, status: 'stale' },
  ],
  whisper_aligned: 21,
  fallback_units: 3,
}

// ---------------------------------------------------------------- Run View（p-2387 失败样例）
const run2387: RunView = {
  run_id: 'run-70a2',
  project_id: 'p-2387',
  trace_id: 'tr-51cc-9e02-33df',
  command_id: 'cmd-2c87',
  status: 'failed',
  strategy: 'auto',
  pipeline_version: 'mountain-av-v1',
  started_at: '2026-08-26T10:22:00+08:00',
  stages: [
    { stage: 'split', status: 'succeeded', started_at: '2026-08-26T10:22:00+08:00', ended_at: '2026-08-26T10:23:00+08:00', progress: '16 units / 22 visuals' },
    {
      stage: 'voice',
      status: 'failed',
      started_at: '2026-08-26T10:23:00+08:00',
      progress: '6/16 单元',
      error: {
        error_code: 'E-TTS-503',
        retryable: true,
        message: '语音节点 tts-node-02 连续返回 503，超过重试上限',
        suggestion: '语音节点过载。请在项目页点击「重试」，系统将从失败单元续跑，已完成单元不会重算。',
        stage: 'voice',
        unit_id: 'u-07',
      },
    },
    { stage: 'storyboard', status: 'pending' },
    { stage: 'illustration', status: 'pending' },
    { stage: 'render', status: 'pending' },
    { stage: 'compose', status: 'pending' },
  ],
  voice_units: [],
  artifacts: [
    { artifact_id: 'art-f01', logical_key: 'storyboard/plan.json', schema_version: 'storyboard.plan/v2', revision: 1, created_at: '2026-08-26T10:23:00+08:00', hash: 'sha256:8812…f4c9', content_type: 'application/json', size_bytes: 39114, status: 'ready' },
    { artifact_id: 'art-f02', logical_key: 'voice/master.wav', schema_version: 'audio.master/v1', revision: 1, created_at: '2026-08-26T10:44:00+08:00', hash: 'sha256:5e37…a120', content_type: 'audio/wav', size_bytes: 6291456, status: 'invalid' },
  ],
  whisper_aligned: 6,
  fallback_units: 0,
}

export function projectDetail(projectId: string): ProjectDetailView {
  const project = projects.find((p) => p.project_id === projectId) ?? projects[0]
  if (project.project_id === 'p-2387') return { project, run: run2387 }
  return { project, run: run2401 }
}

// ---------------------------------------------------------------- Capability（M07 只开放 whiteboard + preset）
export function capability(engine: EngineKind, visual_source: VisualSourceKind): CapabilityView {
  const supported = engine === 'whiteboard' && visual_source === 'preset'
  return {
    engine,
    visual_source,
    supported,
    pipeline: supported ? 'mountain-av-v1' : undefined,
    reason: supported
      ? undefined
      : engine !== 'whiteboard'
        ? '动态信息图引擎计划在 M09 开放（需 Remotion adapter 回归与 capability 测试）'
        : '自定义参考计划在 M09 开放（需风格参考与人物组 adapter 回归）',
  }
}

export const capabilities: CapabilityView[] = [
  capability('whiteboard', 'preset'),
  capability('whiteboard', 'custom-reference'),
  capability('infographic-remotion', 'preset'),
  capability('infographic-remotion', 'custom-reference'),
]

// ---------------------------------------------------------------- 服务健康 & 设置
export const serviceHealth: ServiceHealthView[] = [
  { component: 'api', title: 'Mountain API', status: 'ok', version: '2.3.1' },
  { component: 'text-model', title: '文本模型', status: 'ok', version: 'profile-a (OpenAI 兼容)', detail: 'dify-qwen-72b' },
  { component: 'image-model', title: '图片模型', status: 'ok', version: 'profile-img-1', detail: '本地 SDXL + 白板风格 LoRA' },
  { component: 'tts-node', title: '语音节点', status: 'degraded', version: 'tts-node-02', detail: '偶发 503，重试可恢复' },
  { component: 'whisper', title: 'Whisper 对齐', status: 'ok', version: 'whisper-large-v3 (本地)' },
  { component: 'renderer', title: '渲染环境', status: 'ok', version: 'remotion 4.0 / chrome-headless' },
]

export const settingsSections: SettingsSectionView[] = [
  {
    key: 'models',
    title: '模型',
    items: [
      { key: 'text_profile', label: '文本模型 profile', value: 'profile-a（OpenAI 兼容）', note: '用于文案分割与分镜规划' },
      { key: 'image_profile', label: '图片模型 profile', value: 'profile-img-1（本地 SDXL）', note: '用于统一插画生成' },
      { key: 'api_key', label: '文本模型 API Key', value: 'sk-****-****-3e19', has_secret: true, secret_ref: 'keyring://mountain/text-model' },
    ],
  },
  {
    key: 'speech',
    title: '语音与对齐',
    items: [
      { key: 'tts_node', label: '语音节点', value: 'tts-node-02', note: '状态：degraded（偶发 503）' },
      { key: 'whisper', label: 'Whisper 能力', value: 'whisper-large-v3（本地）', note: '用于 Voice 时长对齐，置信度阈值 0.62' },
      { key: 'fallback_policy', label: 'fallback 策略', value: '低置信度自动平均切图，前端可见但不计为失败' },
    ],
  },
  {
    key: 'toolchain',
    title: '工具链',
    items: [
      { key: 'renderer', label: '渲染环境', value: 'remotion 4.0 + chrome-headless' },
      { key: 'ffmpeg', label: 'FFmpeg', value: '6.1.1' },
      { key: 'python', label: 'Python 工具链', value: '3.11 · mountain-core 0.9.4' },
    ],
  },
  {
    key: 'storage',
    title: '存储',
    items: [
      { key: 'workspace', label: '工作区', value: 'D:\\Mountain\\workspace（逻辑 key 映射，UI 不显示物理路径）' },
      { key: 'retention', label: '保留策略', value: '成片 90 天 / 中间产物 14 天' },
      { key: 'quota', label: '剩余空间', value: '2.1 TB' },
    ],
  },
]

// ---------------------------------------------------------------- 活动 / 日志 / 指标 / 诊断
export function events(after: number): TraceEventView[] {
  const all: TraceEventView[] = [
    { cursor: 1, ts: T(9, 14), kind: 'run.start', message: 'Run 启动（策略 auto，pipeline mountain-av-v1）' },
    { cursor: 2, ts: T(9, 15), kind: 'stage.done', stage: 'split', message: '文案分割完成：24 units / 48 visuals' },
    { cursor: 3, ts: T(9, 15), kind: 'stage.start', stage: 'voice', message: '克隆配音开始' },
    { cursor: 4, ts: T(9, 28), kind: 'unit.fallback', stage: 'voice', unit_id: 'u-03', message: 'u-03 Whisper 置信度 0.58 < 0.62，使用平均切图 fallback' },
    { cursor: 5, ts: T(9, 41), kind: 'stage.done', stage: 'voice', message: '克隆配音完成：21 Whisper 对齐 / 3 fallback' },
    { cursor: 6, ts: T(9, 44), kind: 'stage.done', stage: 'storyboard', message: '分镜规划完成：48 visuals，平均 1.96 图/单元' },
    { cursor: 7, ts: T(10, 2), kind: 'visual.done', stage: 'illustration', visual_id: 'v-01-01', message: 'v-01-01 插画完成（rev 1）' },
    { cursor: 8, ts: T(11, 18), kind: 'visual.redo', stage: 'illustration', visual_id: 'v-01-02', message: 'v-01-02 重新生成（rev 2），仅失效该 Visual 下游' },
    { cursor: 9, ts: T(12, 40), kind: 'retry', stage: 'illustration', visual_id: 'v-03-02', message: 'v-03-02 生成超时后自动重试（1/3）' },
    { cursor: 10, ts: T(13, 39), kind: 'visual.generating', stage: 'illustration', visual_id: 'v-03-02', message: 'v-03-02 重试中（35/48 已完成）' },
  ]
  return all.filter((e) => e.cursor > after)
}

export function logs(): LogEntryView[] {
  return [
    { ts: T(9, 14), level: 'info', component: 'orchestrator', message: 'run-77c3 created, strategy=auto' },
    { ts: T(9, 15), level: 'info', component: 'stage.split', message: 'split done: 24 units, coverage 100%' },
    { ts: T(9, 16), level: 'debug', component: 'stage.voice', provider: 'tts-provider', message: 'voice request u-01 style=ref-a' },
    { ts: T(9, 28), level: 'warn', component: 'align.whisper', stage: 'voice', unit_id: 'u-03', message: 'confidence 0.58 below threshold 0.62, fallback to equal-split' },
    { ts: T(9, 34), level: 'error', component: 'stage.voice', stage: 'voice', unit_id: 'u-11', provider: 'tts-provider', message: 'tts 503, retry 1/3' },
    { ts: T(9, 35), level: 'info', component: 'stage.voice', stage: 'voice', unit_id: 'u-11', message: 'tts retry succeeded' },
    { ts: T(9, 44), level: 'info', component: 'stage.storyboard', message: 'storyboard plan v1 saved (48 visuals)' },
    { ts: T(11, 18), level: 'info', component: 'command', message: 'visual.regenerate v-01-02 accepted (cmd-9f02)' },
    { ts: T(12, 40), level: 'warn', component: 'stage.illustration', visual_id: 'v-03-02', provider: 'image-provider', message: 'image timeout after 60s, retrying' },
    { ts: T(13, 39), level: 'debug', component: 'stage.illustration', visual_id: 'v-03-02', message: 'render worker slot acquired' },
  ]
}

export const metrics: RunMetricsView = {
  stage_durations_s: { split: 62, voice: 1560, storyboard: 180, illustration: 13830, render: 0, compose: 0 },
  provider_latency_ms: {
    'tts-provider': { p50: 8200, p95: 15300, retries: 2 },
    'whisper-local': { p50: 1200, p95: 2400, retries: 0 },
    'image-provider': { p50: 11000, p95: 26000, retries: 1 },
  },
  tts_total_s: 1480,
  whisper_total_s: 78,
  render_total_s: 0,
  fallback_ratio: 0.125,
  av_drift_ms: 18,
}

export const errorChains: Record<string, ErrorChainView[]> = {
  'p-2401': [
    {
      error_code: 'E-ALIGN-LOWCOV',
      retryable: true,
      message: 'u-03 Whisper 置信度 0.58 低于阈值 0.62，已 fallback 平均切图',
      suggestion: '可在诊断页重试该单元的对齐；接受 fallback 不影响成片可用性，画面切换点按等分估计。',
      stage: 'voice',
      unit_id: 'u-03',
    },
    {
      error_code: 'E-IMG-TIMEOUT',
      retryable: true,
      message: 'v-03-02 插画生成 60s 超时',
      suggestion: '系统已自动重试（1/3）。持续失败时可在插画阶段单独重新生成该 Visual，不影响 Voice 与时间边界。',
      stage: 'illustration',
      visual_id: 'v-03-02',
    },
  ],
  'p-2387': [run2387.stages[1].error!],
}

export const diagnosticBundles: DiagnosticBundleView[] = [
  { bundle_id: 'db-20260829-1', created_at: T(13, 30), trace_id: 'tr-8f3a-c24e-11aa', redacted: true, size_bytes: 1835008 },
]

export const currentRun: CurrentRunInfo = {
  project_id: 'p-2401',
  project_name: '量子计算十分钟科普',
  run_id: 'run-77c3',
  trace_id: 'tr-8f3a-c24e-11aa',
  status: 'running',
  current_stage: 'illustration',
}

