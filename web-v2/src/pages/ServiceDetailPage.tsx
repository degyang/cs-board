/* ==========================================================================
   Service Detail Page /settings/models/:serviceId
   Shows service info, availability, secrets, and actions.
   ========================================================================== */

import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { StatusBadge } from '../components/ui/StatusBadge'
import { BackButton } from '../components/ui/BackButton'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { MountainApiError } from '../lib/api/http'
import {
  fetchService,
  activateService,
  deactivateService,
  probeService,
  setDefaultService,
  deleteService,
  fetchServiceSecrets,
  setServiceSecret,
  deleteServiceSecret,
} from '../lib/api/services'
import { KNOWN_CAPABILITIES, KNOWN_ADAPTERS } from '../lib/api/types'
import type { ServiceDefinition, ServiceSecret, ServiceAvailability } from '../lib/api/types'

/** Whitelist fields for error display (§3.8) */
function formatErrorDetails(err: MountainApiError): string {
  const parts: string[] = [err.message]
  if (err.details && typeof err.details === 'object') {
    const d = err.details as Record<string, unknown>
    if (d.request_id) parts.push(`请求 ID: ${d.request_id}`)
    if (d.suggestion) parts.push(`建议: ${d.suggestion}`)
    if (d.revision != null) parts.push(`修订: ${d.revision}`)
    if (d.missing_fields) parts.push(`缺少字段: ${(d.missing_fields as string[]).join(', ')}`)
    if (d.missing_secrets) parts.push(`缺少 Secret: ${(d.missing_secrets as string[]).join(', ')}`)
  }
  return parts.join(' | ')
}

export function ServiceDetailPage() {
  const { serviceId } = useParams<{ serviceId: string }>()
  const navigate = useNavigate()
  const [svc, setSvc] = useState<ServiceDefinition | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MountainApiError | null>(null)
  const [acting, setActing] = useState(false)
  const [actionMsg, setActionMsg] = useState<string | null>(null)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [probeResult, setProbeResult] = useState<ServiceAvailability | null>(null)

  // Secrets state
  const [secrets, setSecrets] = useState<ServiceSecret[]>([])
  const [secretsLoading, setSecretsLoading] = useState(false)
  const [secretValues, setSecretValues] = useState<Record<string, string>>({})
  const [secretAction, setSecretAction] = useState<string | null>(null)
  const [secretError, setSecretError] = useState<string | null>(null)

  const load = useCallback(() => {
    if (!serviceId) return
    setIsLoading(true)
    setError(null)
    fetchService(serviceId)
      .then(setSvc)
      .catch(err => {
        if (err instanceof MountainApiError) setError(err)
      })
      .finally(() => setIsLoading(false))
  }, [serviceId])

  const loadSecrets = useCallback(() => {
    if (!serviceId) return
    setSecretsLoading(true)
    setSecretError(null)
    fetchServiceSecrets(serviceId)
      .then(res => {
        setSecrets(res.items)
      })
      .catch(err => {
        setSecretError(err instanceof MountainApiError ? formatErrorDetails(err) : '加载 Secret 失败')
      })
      .finally(() => setSecretsLoading(false))
  }, [serviceId])

  useEffect(() => {
    load()
    loadSecrets()
  }, [load, loadSecrets])

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

  const handleProbe = async () => {
    if (!serviceId) return
    setActing(true)
    setActionMsg(null)
    try {
      const result = await probeService(serviceId)
      setProbeResult(result)
      setActionMsg('探测完成')
      load()
    } catch (err) {
      setActionMsg(err instanceof MountainApiError ? `探测失败: ${err.message}` : '探测失败')
    } finally {
      setActing(false)
    }
  }

  const handleSaveSecret = async (key: string) => {
    if (!serviceId) return
    const value = secretValues[key]
    if (!value) return
    setSecretAction(key)
    setSecretError(null)
    try {
      await setServiceSecret(serviceId, { key, value })
      // Clear plaintext immediately after save (§3.6)
      setSecretValues(prev => ({ ...prev, [key]: '' }))
      loadSecrets()
      load()
    } catch (err) {
      setSecretError(err instanceof MountainApiError ? formatErrorDetails(err) : `保存 ${key} 失败`)
    } finally {
      setSecretAction(null)
    }
  }

  const handleDeleteSecret = async (key: string) => {
    if (!serviceId) return
    setSecretAction(key)
    setSecretError(null)
    try {
      await deleteServiceSecret(serviceId, key)
      loadSecrets()
      load()
    } catch (err) {
      setSecretError(err instanceof MountainApiError ? formatErrorDetails(err) : `删除 ${key} 失败`)
    } finally {
      setSecretAction(null)
    }
  }

  // Fix #6: Delete flow - stay on page on failure, navigate only on success
  const handleDelete = async () => {
    if (!serviceId) return
    setActing(true)
    setActionMsg(null)
    try {
      await deleteService(serviceId)
      // Success - navigate to list
      navigate('/settings/models', { replace: true })
    } catch (err) {
      // Failure - stay on page, show error
      setActionMsg(err instanceof MountainApiError ? `删除失败: ${err.message}` : '删除失败')
      setShowDeleteDialog(false)
    } finally {
      setActing(false)
    }
  }

  if (!serviceId) return <div className="error-card">缺少 serviceId</div>
  if (isLoading) return <div className="page"><div className="loading"><span className="spinner" />加载中...</div></div>
  if (error) {
    return (
      <div className="page">
        <BackButton to="/settings/models" label="返回模型服务" />
        <div className="error-card">
          <div className="code">{error.code}</div>
          <div>{error.message}</div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={load} style={{ marginTop: 8 }}>重试</button>
        </div>
      </div>
    )
  }
  if (!svc) return <div className="page"><BackButton to="/settings/models" label="返回模型服务" /><div className="empty-state"><div className="empty-title">未找到服务</div></div></div>

  const configOk = svc.config_status.configured
  const secretOk = svc.secret_status.configured

  return (
    <div className="page page-narrow service-detail-page">
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

      <div className="service-detail-actions">
        <Link to={`/settings/models/${serviceId}/edit`} className="btn btn-ghost btn-sm">编辑</Link>
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
          onClick={handleProbe}
        >
          探测
        </button>
        <button
          type="button"
          className="btn btn-danger btn-sm"
          disabled={acting}
          onClick={() => setShowDeleteDialog(true)}
        >
          删除
        </button>
      </div>

      {/* Basic info */}
      <div className="card service-detail-card">
        <div className="card-title">基本信息</div>
        <div className="settings-row">
          <span className="k">服务 ID</span>
          <span className="v mono">{svc.service_id}</span>
        </div>
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
          <span className="k">修订</span>
          <span className="v">{svc.revision}</span>
        </div>
      </div>

      {/* Availability */}
      <div className="card service-detail-card">
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

      {/* Probe result */}
      {probeResult && (
        <div className="card service-detail-card">
          <div className="card-title">探测结果</div>
          <div className="settings-row">
            <span className="k">可用</span>
            <span className="v"><StatusBadge status={probeResult.available ? 'succeeded' : 'failed'} /></span>
          </div>
          {probeResult.checked_at && (
            <div className="settings-row">
              <span className="k">检查时间</span>
              <span className="v">{new Date(probeResult.checked_at).toLocaleString('zh-CN')}</span>
            </div>
          )}
          {probeResult.latency_ms != null && (
            <div className="settings-row">
              <span className="k">延迟</span>
              <span className="v mono">{probeResult.latency_ms}ms</span>
            </div>
          )}
          {probeResult.component && (
            <div className="settings-row">
              <span className="k">组件</span>
              <span className="v mono">{probeResult.component}</span>
            </div>
          )}
          {probeResult.error_code && (
            <div className="settings-row">
              <span className="k">错误码</span>
              <span className="v" style={{ color: 'var(--nt-danger)' }}>{probeResult.error_code}</span>
            </div>
          )}
          {probeResult.suggestion && (
            <div className="settings-row">
              <span className="k">建议</span>
              <span className="v">{probeResult.suggestion}</span>
            </div>
          )}
        </div>
      )}

      {/* Config status */}
      <div className="card service-detail-card">
        <div className="card-title">配置状态</div>
        <div className="settings-row">
          <span className="k">配置</span>
          <span className="v"><StatusBadge status={configOk ? 'succeeded' : 'failed'} label={configOk ? '已配置' : '未配置'} /></span>
        </div>
        {!configOk && svc.config_status.missing_fields.length > 0 && (
          <div className="settings-row">
            <span className="k">缺少字段</span>
            <span className="v">
              {svc.config_status.missing_fields.map(f => <span key={f} className="badge tag-warn" style={{ marginRight: 4 }}>{f}</span>)}
            </span>
          </div>
        )}
        {!configOk && svc.config_status.missing_secrets.length > 0 && (
          <div className="settings-row">
            <span className="k">缺少 Secret</span>
            <span className="v">
              {svc.config_status.missing_secrets.map(s => <span key={s} className="badge tag-warn" style={{ marginRight: 4 }}>{s}</span>)}
            </span>
          </div>
        )}
        <div className="settings-row">
          <span className="k">Secret</span>
          <span className="v"><StatusBadge status={secretOk ? 'succeeded' : svc.secret_status.required.length > 0 ? 'pending' : 'failed'} label={secretOk ? '已配置' : '未配置'} /></span>
        </div>
        {!secretOk && svc.secret_status.missing.length > 0 && (
          <div className="settings-row">
            <span className="k">缺少 Secret</span>
            <span className="v">
              {svc.secret_status.missing.map(s => <span key={s} className="badge tag-warn" style={{ marginRight: 4 }}>{s}</span>)}
            </span>
          </div>
        )}
        {svc.required_secrets.length > 0 && (
          <div className="settings-row">
            <span className="k">必填 Secret</span>
            <span className="v">
              {svc.required_secrets.map(s => <span key={s} className="badge tag-warn" style={{ marginRight: 4 }}>{s}</span>)}
            </span>
          </div>
        )}
        {svc.optional_secrets.length > 0 && (
          <div className="settings-row">
            <span className="k">可选 Secret</span>
            <span className="v">
              {svc.optional_secrets.map(s => <span key={s} className="badge" style={{ marginRight: 4 }}>{s}</span>)}
            </span>
          </div>
        )}
      </div>

      {/* Secrets management */}
      <div className="card service-detail-card">
        <div className="card-title">Secret 管理</div>
        {secretError && <div className="error-card" role="alert" style={{ marginBottom: 8 }}><div>{secretError}</div></div>}
        {secretsLoading ? (
          <div className="loading"><span className="spinner" />加载中...</div>
        ) : secrets.length === 0 && svc.required_secrets.length === 0 ? (
          <div className="empty-sub">无 Secret 配置</div>
        ) : (
          <div className="secrets-list">
            {/* Show required secrets as input fields */}
            {svc.required_secrets.map(key => {
              const existing = secrets.find(s => s.secret_key === key)
              return (
                <div key={key} className="secret-row">
                  <span className="secret-key">{key}</span>
                  {existing?.configured ? (
                    <span className="secret-masked">{existing.masked_value ?? '****'}</span>
                  ) : (
                    <span className="badge tag-warn">未配置</span>
                  )}
                  <input
                    type="password"
                    className="input secret-input"
                    placeholder={existing?.configured ? '输入新值以更新' : '输入 Secret 值'}
                    value={secretValues[key] ?? ''}
                    onChange={e => setSecretValues(prev => ({ ...prev, [key]: e.target.value }))}
                    aria-label={`${key} 值`}
                  />
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    disabled={secretAction === key || !(secretValues[key]?.trim())}
                    onClick={() => handleSaveSecret(key)}
                  >
                    {secretAction === key ? '保存中...' : '保存'}
                  </button>
                  {existing?.configured && (
                    <button
                      type="button"
                      className="btn btn-danger btn-sm"
                      disabled={secretAction === key}
                      onClick={() => handleDeleteSecret(key)}
                    >
                      删除
                    </button>
                  )}
                </div>
              )
            })}
            {/* Show optional secrets that are configured */}
            {secrets.filter(s => !svc.required_secrets.includes(s.secret_key)).map(s => (
              <div key={s.secret_key} className="secret-row">
                <span className="secret-key">{s.secret_key}</span>
                <span className="secret-masked">{s.masked_value ?? '****'}</span>
                <input
                  type="password"
                  className="input secret-input"
                  placeholder="输入新值以更新"
                  value={secretValues[s.secret_key] ?? ''}
                  onChange={e => setSecretValues(prev => ({ ...prev, [s.secret_key]: e.target.value }))}
                  aria-label={`${s.secret_key} 值`}
                />
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  disabled={secretAction === s.secret_key || !(secretValues[s.secret_key]?.trim())}
                  onClick={() => handleSaveSecret(s.secret_key)}
                >
                  {secretAction === s.secret_key ? '保存中...' : '保存'}
                </button>
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  disabled={secretAction === s.secret_key}
                  onClick={() => handleDeleteSecret(s.secret_key)}
                >
                  删除
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <ConfirmDialog
        open={showDeleteDialog}
        title="删除服务"
        message={`确定删除服务「${svc.display_name}」？此操作不可恢复。`}
        confirmLabel="删除"
        danger
        onConfirm={handleDelete}
        onCancel={() => setShowDeleteDialog(false)}
      />
    </div>
  )
}
