/* ==========================================================================
   Service Detail Page /settings/models/:serviceId
   ========================================================================== */

import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { StatusBadge } from '../components/ui/StatusBadge'
import { BackButton } from '../components/ui/BackButton'
import { MountainApiError } from '../lib/api/http'
import { fetchService, activateService, deactivateService, probeService, setDefaultService } from '../lib/api/services'
import { KNOWN_CAPABILITIES, KNOWN_ADAPTERS } from '../lib/api/types'
import type { ServiceDefinition } from '../lib/api/types'

export function ServiceDetailPage() {
  const { serviceId } = useParams<{ serviceId: string }>()
  const [svc, setSvc] = useState<ServiceDefinition | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MountainApiError | null>(null)
  const [acting, setActing] = useState(false)
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  const load = () => {
    if (!serviceId) return
    setIsLoading(true)
    setError(null)
    fetchService(serviceId)
      .then(setSvc)
      .catch(err => { if (err instanceof MountainApiError) setError(err) })
      .finally(() => setIsLoading(false))
  }

  useEffect(() => { load() }, [serviceId])

  const doAction = async (label: string, fn: () => Promise<unknown>) => {
    setActing(true)
    setActionMsg(null)
    try {
      await fn()
      setActionMsg(`${label}成功`)
      load()
    } catch (err) {
      setActionMsg(err instanceof MountainApiError ? `${label}失败: ${err.message}` : `${label}失败`)
    } finally {
      setActing(false)
    }
  }

  if (!serviceId) return <div className="error-card">缺少 serviceId</div>
  if (isLoading) return <div className="loading"><span className="spinner" />加载中...</div>
  if (error) {
    return (
      <div className="page">
        <BackButton to="/settings/models" label="返回模型服务" />
        <div className="error-card">
          <div className="code">{error.code}</div>
          <div>{error.message}</div>
          {error.details && <div className="sug">{JSON.stringify(error.details)}</div>}
          <button type="button" className="btn btn-ghost btn-sm" onClick={load} style={{ marginTop: 8 }}>重试</button>
        </div>
      </div>
    )
  }
  if (!svc) return <div className="page"><BackButton to="/settings/models" label="返回模型服务" /><div className="empty-state"><div className="empty-title">未找到服务</div></div></div>

  return (
    <div className="page">
      <BackButton to="/settings/models" label="返回模型服务" />

      <div className="page-head">
        <h1 className="page-title">{svc.display_name}</h1>
        <p className="page-desc">{svc.service_id}</p>
      </div>

      {actionMsg && (
        <div className={`notice ${actionMsg.includes('失败') ? 'notice-error' : 'notice-ok'}`} role="status" style={{ marginBottom: 12 }}>
          {actionMsg}
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        <button
          type="button"
          className="btn btn-primary btn-sm"
          disabled={acting}
          onClick={() => doAction(svc.enabled ? '停用' : '启用', () => svc.enabled ? deactivateService(svc.service_id) : activateService(svc.service_id))}
        >
          {svc.enabled ? '停用' : '启用'}
        </button>
        {!svc.is_default && (
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            disabled={acting}
            onClick={() => doAction('设为默认', () => setDefaultService(svc.service_id))}
          >
            设为默认
          </button>
        )}
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          disabled={acting}
          onClick={() => doAction('Probe', () => probeService(svc.service_id))}
        >
          Probe
        </button>
      </div>

      {/* Basic info */}
      <div className="card">
        <div className="card-title">基本信息</div>
        <div className="settings-row">
          <span className="k">显示名称</span>
          <span className="v">{svc.display_name}</span>
        </div>
        <div className="settings-row">
          <span className="k">能力</span>
          <span className="v"><span className="mp-category-badge">{KNOWN_CAPABILITIES[svc.capability] ?? svc.capability}</span></span>
        </div>
        <div className="settings-row">
          <span className="k">适配器</span>
          <span className="v"><span className="mp-model-chip">{KNOWN_ADAPTERS[svc.adapter_type] ?? svc.adapter_type}</span></span>
        </div>
        <div className="settings-row">
          <span className="k">模型</span>
          <span className="v mono">{svc.model || '—'}</span>
        </div>
        <div className="settings-row">
          <span className="k">端点</span>
          <span className="v mono">{svc.endpoint || '—'}</span>
        </div>
        <div className="settings-row">
          <span className="k">优先级</span>
          <span className="v">{svc.priority}</span>
        </div>
        <div className="settings-row">
          <span className="k">启用</span>
          <span className="v"><StatusBadge status={svc.enabled ? 'succeeded' : 'pending'} /></span>
        </div>
        <div className="settings-row">
          <span className="k">默认</span>
          <span className="v">{svc.is_default ? '是' : '否'}</span>
        </div>
        <div className="settings-row">
          <span className="k">Schema 版本</span>
          <span className="v mono">{svc.schema_version}</span>
        </div>
        <div className="settings-row">
          <span className="k">修订版本</span>
          <span className="v mono">{svc.revision}</span>
        </div>
        <div className="settings-row">
          <span className="k">创建时间</span>
          <span className="v">{svc.created_at ? new Date(svc.created_at).toLocaleString('zh-CN') : '—'}</span>
        </div>
        <div className="settings-row">
          <span className="k">更新时间</span>
          <span className="v">{svc.updated_at ? new Date(svc.updated_at).toLocaleString('zh-CN') : '—'}</span>
        </div>
      </div>

      {/* Availability */}
      <div className="card">
        <div className="card-title">可用性</div>
        <div className="settings-row">
          <span className="k">可用</span>
          <span className="v"><StatusBadge status={svc.availability.available ? 'succeeded' : 'failed'} /></span>
        </div>
        {svc.availability.checked_at && (
          <div className="settings-row">
            <span className="k">上次检查</span>
            <span className="v">{new Date(svc.availability.checked_at).toLocaleString('zh-CN')}</span>
          </div>
        )}
        {svc.availability.latency_ms != null && (
          <div className="settings-row">
            <span className="k">延迟</span>
            <span className="v mono">{svc.availability.latency_ms}ms</span>
          </div>
        )}
        {svc.availability.component && (
          <div className="settings-row">
            <span className="k">组件</span>
            <span className="v mono">{svc.availability.component}</span>
          </div>
        )}
        {svc.availability.error_code && (
          <div className="settings-row">
            <span className="k">错误码</span>
            <span className="v" style={{ color: 'var(--nt-danger)' }}>{svc.availability.error_code}</span>
          </div>
        )}
        {svc.availability.suggestion && (
          <div className="settings-row">
            <span className="k">建议</span>
            <span className="v">{svc.availability.suggestion}</span>
          </div>
        )}
      </div>

      {/* Config */}
      <div className="card">
        <div className="card-title">配置</div>
        <div className="settings-row">
          <span className="k">配置状态</span>
          <span className="v"><StatusBadge status={svc.config_status === 'ok' ? 'succeeded' : svc.config_status === 'error' ? 'failed' : 'running'} label={svc.config_status} /></span>
        </div>
        <div className="settings-row">
          <span className="k">端点</span>
          <span className="v mono">{svc.endpoint || '—'}</span>
        </div>
        <div className="settings-row">
          <span className="k">模型</span>
          <span className="v mono">{svc.model || '—'}</span>
        </div>
      </div>

      {/* Secrets */}
      <div className="card">
        <div className="card-title">Secrets</div>
        {svc.required_secrets.length > 0 && (
          <div className="settings-row">
            <span className="k">必填</span>
            <span className="v">
              {svc.required_secrets.map(s => <span key={s} className="badge tag-warn" style={{ marginRight: 4 }}>{s}</span>)}
            </span>
          </div>
        )}
        {svc.optional_secrets.length > 0 && (
          <div className="settings-row">
            <span className="k">可选</span>
            <span className="v">
              {svc.optional_secrets.map(s => <span key={s} className="badge" style={{ marginRight: 4 }}>{s}</span>)}
            </span>
          </div>
        )}
        {svc.required_secrets.length === 0 && svc.optional_secrets.length === 0 && (
          <div className="empty-sub">无 Secret 配置</div>
        )}
        <div className="settings-row">
          <span className="k">Secret 状态</span>
          <span className="v"><StatusBadge status={svc.secret_status === 'ok' ? 'succeeded' : svc.secret_status === 'missing' ? 'pending' : 'failed'} label={svc.secret_status} /></span>
        </div>
      </div>
    </div>
  )
}
