import { Link } from 'react-router-dom'
import type { VoiceServiceCardVM } from './types'

/* 语音与对齐 · 服务卡片（IndexTTS / Whisper 共用）
 * 纯展示：配置状态、可用性、错误码与修复建议、非敏感配置键值。
 * 不提供刷新按钮（不得伪装真实服务探测），也不提供配置编辑入口；
 * IndexTTS / Whisper 对齐统一在「模型服务」中维护，点「查看模型服务」跳转到 /settings#models。 */

export function VoiceServiceCard({ vm }: { vm: VoiceServiceCardVM }) {
  const available = vm.availability.state === 'available'
  const configured = vm.config_status === 'configured'
  const configEntries = Object.entries(vm.config).filter(([, v]) => v != null && v !== '')

  return (
    <div className="va-card">
      <div className="va-card-head">
        <div className="va-card-title-row">
          <h3 className="va-card-name">{vm.name}</h3>
          <span className="badge tag-neutral">{vm.category}</span>
        </div>
        <p className="va-card-desc">{vm.description}</p>
      </div>

      <div className="va-status-row">
        <span className="va-status-item">
          <span className="va-status-label">配置状态</span>
          <StatusChip ok={configured} label={configured ? '已配置' : '未配置'} />
        </span>
        <span className="va-status-item">
          <span className="va-status-label">可用性</span>
          <StatusChip ok={available} label={available ? '可用' : '不可用'} />
        </span>
      </div>

      {configEntries.length > 0 && (
        <div className="va-config">
          {configEntries.map(([k, v]) => (
            <div key={k} className="va-config-row">
              <span className="va-config-key">{k}</span>
              <span className="va-config-val mono">{v}</span>
            </div>
          ))}
        </div>
      )}

      {!available && (
        <div className="va-error">
          <div className="va-error-head">
            <span className="va-error-code mono">{vm.availability.error_code ?? 'E-UNKNOWN'}</span>
            <span className="badge st-failed">不可用</span>
          </div>
          <p className="va-error-suggestion">{vm.availability.suggestion ?? '请检查服务配置后重试。'}</p>
        </div>
      )}

      <div className="va-card-actions">
        <Link className="btn btn-sm" to="/settings#models">
          查看模型服务
        </Link>
      </div>
      <div className="va-card-hint">{vm.configure_hint}</div>
    </div>
  )
}

function StatusChip({ ok, label }: { ok: boolean; label: string }) {
  return <span className={`badge ${ok ? 'st-succeeded' : 'st-failed'}`}>{label}</span>
}
