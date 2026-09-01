/* ==========================================================================
   Model Services Page — /settings/models
   Lists all dynamic services with CRUD actions.
   Card hierarchy 对齐原型 ModelsTab: head → purpose → caps → meta-row → URL → error → actions
   ========================================================================== */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { StatusBadge } from '../components/ui/StatusBadge'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { MountainApiError } from '../lib/api/http'
import { fetchServices, probeService, setDefaultService, activateService, deactivateService, deleteService } from '../lib/api/services'
import { KNOWN_CAPABILITIES, KNOWN_ADAPTERS } from '../lib/api/types'
import type { ServiceDefinition } from '../lib/api/types'

function configStatusBadge(svc: ServiceDefinition) {
  if (svc.config_status.configured) return { kind: 'succeeded' as const, label: '已配置' }
  return { kind: 'pending' as const, label: '未配置' }
}

function availabilityBadge(svc: ServiceDefinition) {
  if (svc.availability.available) return { kind: 'succeeded' as const, label: '可用' }
  if (svc.availability.checked_at) return { kind: 'failed' as const, label: '不可用' }
  return { kind: 'pending' as const, label: '未探测' }
}

function ServiceCard({ svc, actingId, onAction, onDelete }: {
  svc: ServiceDefinition
  actingId: string | null
  onAction: (id: string, label: string, fn: () => Promise<unknown>) => void
  onDelete: (svc: ServiceDefinition) => void
}) {
  const config = configStatusBadge(svc)
  const avail = availabilityBadge(svc)

  return (
    <div className="mp-card">
      <div className="mp-card-head">
        <h3 className="mp-card-name">{svc.display_name}</h3>
        <span className="badge tag-neutral">{KNOWN_CAPABILITIES[svc.capability] ?? svc.capability}</span>
      </div>

      {svc.model && <div className="mp-purpose">{svc.model}</div>}

      <div className="mp-caps">
        <span className="badge tag-neutral mono">{KNOWN_ADAPTERS[svc.adapter_type] ?? svc.adapter_type}</span>
        {svc.model && <span className="badge tag-neutral mono">{svc.model}</span>}
      </div>

      <div className="mp-meta-row">
        <span className={`badge st-${config.kind}`}>{config.label}</span>
        <span className={`badge st-${avail.kind}`}>{avail.label}</span>
        {svc.is_default && <span className="badge tag-info">默认</span>}
        <StatusBadge status={svc.enabled ? 'running' : 'pending'} label={svc.enabled ? '已启用' : '已停用'} />
      </div>

      {svc.endpoint && <div className="mp-card-meta mono">Base URL：{svc.endpoint}</div>}

      {svc.availability.error_code && (
        <div className="mp-error">
          <div className="mp-error-head">
            <span className="mp-error-code mono">{svc.availability.error_code}</span>
          </div>
          {svc.availability.suggestion && (
            <p className="mp-error-suggestion">{svc.availability.suggestion}</p>
          )}
        </div>
      )}

      <div className="mp-card-actions">
        <Link to={`/settings/models/${svc.service_id}`} className="btn btn-ghost btn-sm">详情</Link>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          disabled={actingId === svc.service_id}
          onClick={() => onAction(svc.service_id, svc.enabled ? '停用' : '启用', () => svc.enabled ? deactivateService(svc.service_id) : activateService(svc.service_id))}
        >
          {svc.enabled ? '停用' : '启用'}
        </button>
        {!svc.is_default && (
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            disabled={actingId === svc.service_id}
            onClick={() => onAction(svc.service_id, '设为默认', () => setDefaultService(svc.service_id))}
          >
            设为默认
          </button>
        )}
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          disabled={actingId === svc.service_id}
          onClick={() => onAction(svc.service_id, '探测', () => probeService(svc.service_id))}
        >
          探测
        </button>
        <button
          type="button"
          className="btn btn-danger btn-sm"
          disabled={actingId === svc.service_id}
          onClick={() => onDelete(svc)}
        >
          删除
        </button>
      </div>
    </div>
  )
}

export function ModelServicesPage() {
  const [services, setServices] = useState<ServiceDefinition[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MountainApiError | null>(null)
  const [capabilityFilter, setCapabilityFilter] = useState('')
  const [search, setSearch] = useState('')
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)
  const [actingId, setActingId] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<ServiceDefinition | null>(null)

  const load = () => {
    setIsLoading(true)
    setError(null)
    fetchServices({ capability: capabilityFilter || undefined, q: search || undefined })
      .then(r => setServices(r.items))
      .catch(err => { if (err instanceof MountainApiError) setError(err) })
      .finally(() => setIsLoading(false))
  }

  useEffect(() => { load() }, [capabilityFilter, search])

  const doAction = async (id: string, label: string, fn: () => Promise<unknown>) => {
    setActingId(id)
    setActionError(null)
    setActionSuccess(null)
    try {
      await fn()
      setActionSuccess(`${label}成功`)
      load()
    } catch (err) {
      setActionError(err instanceof MountainApiError ? `${label}失败: ${err.message}` : `${label}失败`)
    } finally {
      setActingId(null)
    }
  }

  const confirmDelete = async () => {
    if (!deleteTarget) return
    await doAction(deleteTarget.service_id, '删除', () => deleteService(deleteTarget.service_id))
    setDeleteTarget(null)
  }

  if (isLoading) return <div className="loading"><span className="spinner" />加载中...</div>
  if (error) {
    return (
      <div className="error-card">
        <div className="code">{error.code}</div>
        <div>{error.message}</div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={load} style={{ marginTop: 8 }}>重试</button>
      </div>
    )
  }

  return (
    <div className="set-models">
      <div className="set-filter-row">
        <input
          type="text"
          className="input"
          placeholder="搜索服务..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          aria-label="搜索服务"
        />
        <select
          className="select"
          value={capabilityFilter}
          onChange={e => setCapabilityFilter(e.target.value)}
          aria-label="按能力筛选"
        >
          <option value="">全部能力</option>
          {Object.entries(KNOWN_CAPABILITIES).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <Link to="/settings/models/new" className="btn btn-primary btn-sm">新建服务</Link>
      </div>

      {actionError && (
        <div className="error-card" role="alert">
          <div>{actionError}</div>
        </div>
      )}
      {actionSuccess && (
        <div className="notice notice-ok" role="status">{actionSuccess}</div>
      )}

      <div className="card">
        <h2 className="card-title">模型服务注册表</h2>
        <p className="card-sub">
          当前已接入的模型服务能力。本地引擎开箱可用、无需密钥；外部 API 需配置密钥后探测可用性。
        </p>

        <div className="ss-hint">
          密钥安全边界：API Key / token / secret 由后端密钥库（SecretStore）统一管理。本页不存储、不回显明文密钥；
          密钥仅作为一次性输入提交，落库后立即清空。
        </div>

        {services.length === 0 ? (
          <div className="empty-state">
            <div className="empty-title">暂无服务</div>
            <div className="empty-sub">尚未配置任何模型服务</div>
          </div>
        ) : (
          <div className="mp-list">
            {services.map(svc => (
              <ServiceCard
                key={svc.service_id}
                svc={svc}
                actingId={actingId}
                onAction={doAction}
                onDelete={setDeleteTarget}
              />
            ))}
          </div>
        )}
      </div>

      <ConfirmDialog
        open={deleteTarget !== null}
        title="删除服务"
        message={deleteTarget ? `确定删除服务「${deleteTarget.display_name}」？此操作不可恢复。` : ''}
        confirmLabel="删除"
        danger
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}
