/* ==========================================================================
   模型服务注册表 · View Model 类型
   仅为「设置-模型服务」只读原型页定义的数据契约。
   页面组件全部通过 Props 注入 ModelRegistryView，不持有任何存储或请求逻辑，
   便于后续产品工程直接替换为真实 API 数据（候选契约：/api/v1/models/registry）。

   设计约束（来自安全边界与 IA 约定）：
     - 只读展示，不包含任何可保存的「配置」字段，不提供增删改；
     - 不暴露 API Key / token / secret：本页不存储、不回显、不提供编辑入口；
     - 密钥未来仅作为一次性 password 输入提交到后端 SecretStore，成功后立即清空；
     - 不提供 storage / session 持久化，所有数据来自内存 fixture。
   ========================================================================== */

/** 能力标签（一个服务可多选、多能力） */
export type CapabilityTag =
  | 'text.generate'
  | 'image.generate'
  | 'speech.synthesize'
  | 'audio.align'
  | 'video.render'
  | 'media.compose'

/** 服务类型：本地引擎 / 外部 API */
export type ServiceType = 'local' | 'external-api'

/** 配置状态 */
export type ConfigStatus =
  | 'no-key-required' // 无需密钥（本地引擎）
  | 'unconfigured' // 未配置（未来外部 Provider 待接入）
  | 'configured' // 已配置（未来外部 Provider 接入后）

/** 可用性 */
export type Availability = 'available' | 'unavailable' | 'not-probed'

/** 单个模型服务卡片（只读） */
export interface ModelServiceVM {
  /** 稳定 ID */
  id: string
  /** 服务名称 */
  name: string
  /** 服务类型：本地 / 外部 API */
  type: ServiceType
  /** 能力标签（可多选） */
  capabilities: CapabilityTag[]
  /** 模型名称或运行模式（纯展示，非路径） */
  modelOrMode?: string
  /** Base URL（仅适用于确实需要的外部 API；本地引擎不展示） */
  baseUrl?: string
  /** 配置状态 */
  configStatus: ConfigStatus
  /** 可用性 */
  availability: Availability
  /** 不可用时：错误码（真实 API：availability.error_code） */
  error_code?: string
  /** 不可用时：修复建议（真实 API：availability.suggestion） */
  suggestion?: string
}

/** 页面级 View Model */
export interface ModelRegistryView {
  /** 模型服务列表（只读） */
  services: ModelServiceVM[]
}

/* —— 展示用映射 —— */
export const CAPABILITY_LABEL: Record<CapabilityTag, string> = {
  'text.generate': 'text.generate',
  'image.generate': 'image.generate',
  'speech.synthesize': 'speech.synthesize',
  'audio.align': 'audio.align',
  'video.render': 'video.render',
  'media.compose': 'media.compose',
}

export const SERVICE_TYPE_LABEL: Record<ServiceType, string> = {
  local: '本地',
  'external-api': '外部 API',
}

export const CONFIG_STATUS_LABEL: Record<ConfigStatus, string> = {
  'no-key-required': '无需密钥',
  unconfigured: '未配置',
  configured: '已配置',
}

export const AVAILABILITY_LABEL: Record<Availability, string> = {
  available: '可用',
  unavailable: '不可用',
  'not-probed': '未探测',
}
