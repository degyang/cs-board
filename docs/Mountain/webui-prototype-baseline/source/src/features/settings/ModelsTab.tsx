import { MODEL_REGISTRY_VIEW } from './modelsRegistry/fixtures'
import {
  type ModelServiceVM,
  type ConfigStatus,
  type Availability,
  CAPABILITY_LABEL,
  SERVICE_TYPE_LABEL,
  CONFIG_STATUS_LABEL,
  AVAILABILITY_LABEL,
} from './modelsRegistry/types'

/* 设置-模型服务 · 模型服务注册表（只读原型）
   展示当前已接入的模型服务能力：本地引擎（Codex Skills / IndexTTS / Whisper / FFmpeg / 白板渲染器）
   与未来可加入的外部 API（未配置 / 未探测）。
   安全边界：本页不存储、不回显、不编辑任何 API Key / token / secret；
   密钥未来仅作为一次性 password 输入提交后端 SecretStore，成功后立即清空。 */

/** 状态徽标（复用既有 .badge .st-* 体系） */
function StateBadge({ kind, label }: { kind: 'succeeded' | 'failed' | 'pending'; label: string }) {
  return <span className={`badge st-${kind}`}>{label}</span>
}

const CONFIG_BADGE: Record<ConfigStatus, 'succeeded' | 'pending'> = {
  'no-key-required': 'succeeded',
  configured: 'succeeded',
  unconfigured: 'pending',
}
const AVAIL_BADGE: Record<Availability, 'succeeded' | 'failed' | 'pending'> = {
  available: 'succeeded',
  unavailable: 'failed',
  'not-probed': 'pending',
}

function ServiceCard({ s }: { s: ModelServiceVM }) {
  const available = s.availability === 'available'
  return (
    <div className="ss-card">
      <div className="ss-card-head">
        <h3 className="ss-card-name">{s.name}</h3>
        <span className="badge tag-neutral">{SERVICE_TYPE_LABEL[s.type]}</span>
      </div>

      {s.modelOrMode && <div className="ss-card-purpose">{s.modelOrMode}</div>}

      <div className="ms-caps">
        {s.capabilities.map((c) => (
          <span key={c} className="badge tag-neutral mono">
            {CAPABILITY_LABEL[c]}
          </span>
        ))}
      </div>

      <div className="ms-meta-row">
        <StateBadge kind={CONFIG_BADGE[s.configStatus]} label={CONFIG_STATUS_LABEL[s.configStatus]} />
        <StateBadge kind={AVAIL_BADGE[s.availability]} label={AVAILABILITY_LABEL[s.availability]} />
      </div>

      {s.baseUrl && <div className="ss-card-meta mono">Base URL：{s.baseUrl}</div>}

      {!available && (
        <div className="ss-error">
          <div className="ss-error-head">
            <span className="ss-error-code mono">{s.error_code ?? 'E-UNKNOWN'}</span>
          </div>
          <p className="ss-error-suggestion">{s.suggestion ?? '请检查服务配置后重试。'}</p>
        </div>
      )}
    </div>
  )
}

export function ModelsTab() {
  const services = MODEL_REGISTRY_VIEW.services
  return (
    <div className="card">
      <h2 className="card-title">模型服务注册表</h2>
      <p className="card-sub">
        当前已接入的模型服务能力（只读）。本地引擎开箱可用、无需密钥；外部 API 为未来可加入的 Provider，待后端契约与密钥库支持。
      </p>

      <div className="ss-hint">
        密钥安全边界：API Key / token / secret 由后端密钥库（SecretStore）统一管理。本页不存储、不回显、不提供编辑入口；
        未来密钥仅作为一次性 password 输入提交，落库后立即清空。
      </div>

      <div className="ss-grid">
        {services.map((s) => (
          <ServiceCard key={s.id} s={s} />
        ))}
      </div>
    </div>
  )
}
