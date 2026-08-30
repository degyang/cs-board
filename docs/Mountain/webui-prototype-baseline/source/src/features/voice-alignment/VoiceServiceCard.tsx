import type { VoiceServiceCardVM } from './types'

/* 语音与对齐 · 服务卡片（IndexTTS / Whisper 共用）
 * 纯展示 + 动作回调：刷新状态 / 配置。数据由 Props 注入，无内部存储。 */

export function VoiceServiceCard({
  vm,
  refreshing,
  onRefresh,
}: {
  vm: VoiceServiceCardVM
  /** 原型演示：刷新动作期间短暂置灰 */
  refreshing: boolean
  onRefresh: () => void
}) {
  const available = vm.availability.state === 'available'
  const configured = vm.config_status === 'configured'
  const configEntries = Object.entries(vm.config).filter(([, v]) => v != null && v !== '')
  /* 配置归属：IndexTTS / Whisper 对齐均统一在「模型服务」中维护，本页不提供配置入口 */
  const targetRoute = vm.id === 'indextts' ? '/settings/providers/tts' : '/settings/providers/alignment'

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
        <button type="button" className="btn btn-ghost btn-sm" onClick={onRefresh} disabled={refreshing}>
          {refreshing ? '刷新中…' : '刷新状态'}
        </button>
        <button type="button" className="btn btn-sm" disabled title="配置在「模型服务」中统一维护">
          在模型服务中配置
        </button>
      </div>
      <div className="va-card-hint">
        <div>{vm.configure_hint}</div>
        <div className="va-route mono">目标路由 {targetRoute}</div>
      </div>
    </div>
  )
}

function StatusChip({ ok, label }: { ok: boolean; label: string }) {
  return <span className={`badge ${ok ? 'st-succeeded' : 'st-failed'}`}>{label}</span>
}

