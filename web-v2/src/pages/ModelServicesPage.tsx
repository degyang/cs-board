/* ==========================================================================
   Model Services Page — /settings/models
   Lists all dynamic services with CRUD actions.
   ========================================================================== */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { StatusBadge } from '../components/ui/StatusBadge'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { MountainApiError } from '../lib/api/http'
import { fetchServices, probeService, setDefaultService, activateService, deactivateService, deleteService } from '../lib/api/services'
import { KNOWN_CAPABILITIES, KNOWN_ADAPTERS } from '../lib/api/types'
import type { ServiceDefinition } from '../lib/api/types'

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

      {services.length === 0 ? (
        <div className="empty-state">
          <div className="empty-title">暂无服务</div>
          <div className="empty-sub">尚未配置任何模型服务</div>
        </div>
      ) : (
        <div className="mp-list">
          {services.map(svc => (
            <div key={svc.service_id} className="mp-card">
              <div className="mp-card-head">
                <div className="mp-card-icon">{svc.display_name[0] ?? '?'}</div>
                <div>
                  <div className="mp-card-title">{svc.display_name}</div>
                  <div className="mp-card-desc">{svc.service_id}</div>
                </div>
                <div className="mp-card-actions" style={{ marginLeft: 'auto' }}>
                  <span className="mp-category-badge">{KNOWN_CAPABILITIES[svc.capability] ?? svc.capability}</span>
                  {svc.is_default && <span className="badge tag-info">默认</span>}
                  <StatusBadge status={svc.enabled ? 'running' : 'pending'} label={svc.enabled ? '已启用' : '已停用'} />
                </div>
              </div>
              <div className="mp-card-body">
                <span className="mp-model-chip">{KNOWN_ADAPTERS[svc.adapter_type] ?? svc.adapter_type}</span>
                {svc.model && <span className="mp-model-chip">{svc.model}</span>}
                {svc.endpoint && <span className="mp-url">{svc.endpoint}</span>}
                {svc.availability.error_code && (
                  <span className="badge st-failed">{svc.availability.error_code}</span>
                )}
                {svc.availability.suggestion && (
                  <span className="mp-info">{svc.availability.suggestion}</span>
                )}
                {svc.availability.checked_at && (
                  <span style={{ fontSize: 11, color: 'var(--nt-text-muted)' }}>
                    上次检查: {new Date(svc.availability.checked_at).toLocaleString('zh-CN')}
                    {svc.availability.latency_ms != null && ` (${svc.availability.latency_ms}ms)`}
                  </span>
                )}
              </div>
              <div className="mp-card-actions">
                <Link to={`/settings/models/${svc.service_id}`} className="btn btn-ghost btn-sm">详情</Link>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  disabled={actingId === svc.service_id}
                  onClick={() => doAction(svc.service_id, svc.enabled ? '停用' : '启用', () => svc.enabled ? deactivateService(svc.service_id) : activateService(svc.service_id))}
                >
                  {svc.enabled ? '停用' : '启用'}
                </button>
                {!svc.is_default && (
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    disabled={actingId === svc.service_id}
                    onClick={() => doAction(svc.service_id, '设为默认', () => setDefaultService(svc.service_id))}
                  >
                    设为默认
                  </button>
                )}
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  disabled={actingId === svc.service_id}
                  onClick={() => doAction(svc.service_id, '探测', () => probeService(svc.service_id))}
                >
                  探测
                </button>
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  disabled={actingId === svc.service_id}
                  onClick={() => setDeleteTarget(svc)}
                >
                  删除
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

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
