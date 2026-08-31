import type {
  ToolchainStatusView,
  TaskStorageStatusView,
  SystemDiagnosticsView,
} from './types'

/* ==========================================================================
   系统状态原型 fixtures（明确命名，仅用于演示）
   全部为内存常量：无 localStorage/sessionStorage、无网络请求、无 Secret。
   演示场景：
     - available          正常态（工具链可用、存储全正常）
     - toolchain-unavailable 一个工具链组件不可用（白板渲染器离线）
     - storage-not-stated    存储中「视觉与渲染产物」未统计
   数据来源（候选契约，待后端确认，未实现 fetch）：
     - /api/v1/toolchain/status
     - /api/v1/storage/status
     - /api/v1/diagnostics/summary
   ========================================================================== */

/** 当前真实本地能力（Codex Skills / IndexTTS / Whisper / FFmpeg / 白板渲染器） */
export const TC_VIEW_NORMAL: ToolchainStatusView = {
  tools: [
    {
      id: 'codex-skills',
      name: 'Codex Skills',
      purpose: '本地插画生成，负责将分镜描述生成为插画。',
      modeOrVersion: 'Codex Skills · 本地',
      state: 'available',
    },
    {
      id: 'indextts',
      name: 'IndexTTS',
      purpose: '本地语音合成 / 音色克隆，负责将每个 Voice Unit 生成为语音。',
      modeOrVersion: 'IndexTTS · 本地推理',
      state: 'available',
    },
    {
      id: 'whisper',
      name: 'Whisper',
      purpose: '本地语音与文字时间对齐，驱动画面在正确时间点切换。',
      modeOrVersion: 'whisper-large-v3 · 本地推理',
      state: 'available',
    },
    {
      id: 'ffmpeg',
      name: 'FFmpeg 音画合成',
      purpose: '将配音、对齐字幕与画面合成为最终成片。',
      modeOrVersion: '6.1.1',
      state: 'available',
    },
    {
      id: 'renderer',
      name: '白板渲染器',
      purpose: '将分镜与插画合成为白板动画视频帧。',
      modeOrVersion: 'Remotion 4.0 · 本地无头渲染',
      state: 'available',
    },
  ],
}

/** 系统工具链 · 不可用：白板渲染节点离线（其余仍可用） */
export const TC_VIEW_UNAVAILABLE: ToolchainStatusView = {
  tools: [
    {
      ...TC_VIEW_NORMAL.tools[4],
      state: 'unavailable',
      error_code: 'E-RENDER-NODE-OFFLINE',
      suggestion:
        '白板渲染节点未响应。请确认本地渲染服务已启动（默认随运行时一同拉起）后由运行环境重新探测；排查期间相关成片任务将进入等待队列。',
    },
    ...TC_VIEW_NORMAL.tools.slice(0, 4),
  ],
}

/** 运行时存储状态 · 正常：五类逻辑存储均正常（仅全局逻辑健康，不暗示具体任务） */
export const STORAGE_VIEW_NORMAL: TaskStorageStatusView = {
  classes: [
    { id: 'input', name: '任务输入', state: 'normal', summary: '参考文案、音色与风格等制作输入' },
    { id: 'voice', name: '音频与对齐产物', state: 'normal', summary: '各任务配音结果与时间对齐产物' },
    { id: 'visual', name: '视觉与渲染产物', state: 'normal', summary: '分镜插画与中间渲染产物' },
    { id: 'final', name: '最终成片', state: 'normal', summary: '已合成成片' },
    { id: 'bundle', name: '脱敏诊断包', state: 'normal', summary: '脱敏后的诊断包' },
  ],
}

/** 运行时存储状态 · 未统计：其中「视觉与渲染产物」尚未统计 */
export const STORAGE_VIEW_NOT_STATED: TaskStorageStatusView = {
  classes: STORAGE_VIEW_NORMAL.classes.map((c) =>
    c.id === 'visual' ? { ...c, state: 'not-stated', summary: undefined } : c,
  ),
}

/** 系统诊断 · 只读汇总（真实接入后由 /api/v1/diagnostics/summary 返回） */
export const DIAG_VIEW: SystemDiagnosticsView = {
  health: [
    { component: 'api', title: 'Mountain API', status: 'ok', version: '2.3.1' },
    { component: 'codex-skills', title: '插画生成（Codex Skills）', status: 'ok', version: '本地' },
    { component: 'indextts', title: '语音合成（IndexTTS）', status: 'ok', version: '本地推理' },
    { component: 'whisper', title: 'Whisper 对齐', status: 'ok', version: 'whisper-large-v3（本地）' },
    { component: 'ffmpeg', title: 'FFmpeg 音画合成', status: 'ok', version: '6.1.1' },
    { component: 'renderer', title: '渲染环境', status: 'ok', version: 'Remotion 4.0 / chrome-headless' },
  ],
  capabilityMatrix: [
    { engine: '插画生成', visualSource: 'Codex Skills', supported: true, detail: '本地 Codex Skills' },
    { engine: '白板动画', visualSource: '预设风格', supported: true, detail: 'mountain-av-v1' },
    {
      engine: '白板动画',
      visualSource: '自定义参考',
      supported: false,
      detail: '自定义参考计划在后续版本开放（需风格参考与人物组 adapter 回归）',
    },
    {
      engine: '动态信息图',
      visualSource: '预设风格',
      supported: false,
      detail: '动态信息图引擎计划后续开放（需 Remotion adapter 回归）',
    },
  ],
  redactionNote:
    '所有日志、事件与诊断包均由服务端统一脱敏：不含任务原文、Prompt、参考音频、Secret、Token，也不暴露诊断文件路径。',
  taskLevel: {
    title: '任务级诊断',
    desc: 'Trace、事件、日志筛选与诊断包均绑定到某个任务运行（任务 ID）。设置页不展示任何任务的原始内容；相关操作请在任务工作台中查看。',
    queueRoute: '/tasks',
    workbenchHint: '进入任务工作台后，在对应运行下查看「运行诊断」。',
  },
}

/** 演示场景：配合 ?demo= 参数驱动工具链 / 存储状态 */
export const SYS_DEMO_VIEWS = [
  { key: 'available', label: '正常', toolchain: TC_VIEW_NORMAL, storage: STORAGE_VIEW_NORMAL },
  { key: 'toolchain-unavailable', label: '工具链不可用', toolchain: TC_VIEW_UNAVAILABLE, storage: STORAGE_VIEW_NORMAL },
  { key: 'storage-not-stated', label: '存储未统计', toolchain: TC_VIEW_NORMAL, storage: STORAGE_VIEW_NOT_STATED },
] as const
