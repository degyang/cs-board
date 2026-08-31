/* ==========================================================================
   系统状态原型 · View Model 类型
   仅为「设置-系统工具链 / 任务存储状态 / 系统诊断」原型页定义的数据契约。
   页面组件全部通过 Props 注入下列 View Model，不持有任何存储或请求逻辑，
   便于后续产品工程直接替换为真实 API 数据：
     - /api/v1/toolchain/status     → ToolchainStatusView
     - /api/v1/storage/status       → TaskStorageStatusView
     - /api/v1/diagnostics/summary  → SystemDiagnosticsView
   设计约束（来自 IA 约定）：
     - 只读展示，不包含任何可保存的「配置」字段；
     - 不暴露本机绝对路径 / 命令行参数 / 引擎选择 / 密钥；
     - 不提供 storage / session 持久化，所有数据来自内存 fixture。
   ========================================================================== */

/** 单个系统工具链组件（Codex Skills / IndexTTS / Whisper / FFmpeg / 白板渲染器 等） */
export interface ToolStatusCardVM {
  /** 稳定 ID：'codex-skills' | 'indextts' | 'whisper' | 'ffmpeg' | 'renderer' */
  id: string
  /** 组件名称 */
  name: string
  /** 用途说明（只读） */
  purpose: string
  /** 运行模式或版本（可选，纯展示，非可执行路径） */
  modeOrVersion?: string
  /** 可用 / 不可用 */
  state: 'available' | 'unavailable'
  /** 不可用时：错误码（真实 API：availability.error_code） */
  error_code?: string
  /** 不可用时：修复建议（真实 API：availability.suggestion） */
  suggestion?: string
}

export interface ToolchainStatusView {
  /** 系统工具链组件列表 */
  tools: ToolStatusCardVM[]
}

/** 逻辑存储状态：正常 / 不可用 / 未统计 */
export type StorageState = 'normal' | 'unavailable' | 'not-stated'

/** 单个逻辑存储类 */
export interface StorageClassVM {
  /** 稳定 ID */
  id: string
  /** 存储类名称 */
  name: string
  /** 运行状态 */
  state: StorageState
  /** 可选的逻辑摘要，仅描述全局逻辑健康，不含本机路径、文件名，也不暗示具体任务上下文 */
  summary?: string
}

export interface TaskStorageStatusView {
  /** 五类逻辑存储 */
  classes: StorageClassVM[]
}

/** 服务健康汇总行 */
export interface DiagHealthRow {
  /** 组件 key */
  component: string
  /** 展示标题 */
  title: string
  /** 状态：正常 / 降级 / 不可用 */
  status: 'ok' | 'degraded' | 'down'
  /** 版本（可选） */
  version?: string
  /** 细节说明（可选） */
  detail?: string
}

/** 系统能力矩阵行（引擎 × 视觉来源） */
export interface DiagCapabilityRow {
  /** 引擎名（展示用） */
  engine: string
  /** 视觉来源名（展示用） */
  visualSource: string
  /** 是否受支持 */
  supported: boolean
  /** 细节 / 未开放原因（可选） */
  detail?: string
}

export interface SystemDiagnosticsView {
  /** 服务健康汇总 */
  health: DiagHealthRow[]
  /** 系统能力矩阵 */
  capabilityMatrix: DiagCapabilityRow[]
  /** 脱敏与隐私说明（只读文案） */
  redactionNote: string
  /** 任务级诊断入口说明 */
  taskLevel: {
    title: string
    desc: string
    /** 主按钮目标路由（前往任务队列） */
    queueRoute: string
    /** 辅助说明：进入任务工作台后查看运行诊断 */
    workbenchHint: string
  }
}
