/* ==========================================================================
   语音与对齐 · View Model 类型
   仅为「设置-语音与对齐」原型页定义的数据契约：
   页面组件全部通过 Props 注入 VoiceAlignmentView，不持有任何存储或请求逻辑，
   便于后续产品工程直接替换为真实 API 数据（IndexTTS / Whisper 统一出现在
   「模型服务注册表」，其接入状态由 /api/v1/models/registry 候选契约返回）。
   字段映射（真实 API → VM）：
     profile                  → name / description / category
     config                   → config（仅展示非敏感键值：base_url / mode 等）
     config_status            → config_status（'configured' | 'unconfigured'）
     availability             → availability.state（'available' | 'unavailable'）
     availability.error_code  → availability.error_code
     availability.suggestion  → availability.suggestion
   ========================================================================== */

/** 服务可用性：loading 由外层独立标注；此结构仅表达终态 */
export interface ServiceAvailability {
  state: 'available' | 'unavailable'
  /** 真实 API：availability.error_code */
  error_code?: string
  /** 真实 API：availability.suggestion */
  suggestion?: string
}

/** 单个服务卡片（IndexTTS / Whisper 对齐 共用） */
export interface VoiceServiceCardVM {
  /** 稳定 ID：'indextts' | 'whisper' */
  id: string
  /** 真实 API：profile.name */
  name: string
  /** 真实 API：profile.description */
  description: string
  /** 类别徽标文案：'语音' / '工具链 · 对齐' */
  category: string
  /** 真实 API：config_status */
  config_status: 'configured' | 'unconfigured'
  /** 真实 API：availability（loading 态在页面级由 vm.state === 'loading' 表达） */
  availability: ServiceAvailability
  /** 非敏感配置键值（真实 API：config），如 base_url / mode；不含任何 Secret */
  config: Record<string, string | undefined>
  /** 「配置」动作的视觉去向说明（原型阶段仅文案） */
  configure_hint: string
}

/** 页面级 View Model：两个服务卡片 + 演示态 */
export type VoiceAlignmentState = 'ready' | 'loading'

export interface VoiceAlignmentView {
  /** 演示态：ready = 正常渲染两卡片；loading = 整页骨架加载 */
  state: VoiceAlignmentState
  /** IndexTTS 服务卡片 */
  tts: VoiceServiceCardVM
  /** Whisper 对齐服务卡片 */
  alignment: VoiceServiceCardVM
}
