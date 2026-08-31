/* ==========================================================================
   Service Detail Page /settings/models/:serviceId
   Shows service info, availability, secrets, and actions.
   ========================================================================== */

import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { StatusBadge } from '../components/ui/StatusBadge'
import { BackButton } from '../components/ui/BackButton'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { MountainApiError } from '../lib/api/http'
import { fetchService, activateService, deactivateService, probeService, setDefaultService, deleteService, fetchServiceSecrets, setServiceSecret, deleteServiceSecret } from '../lib/api/services'
import { KNOWN_CAPABILITIES, KNOWN_ADAPTERS } from '../lib/api/types'
import type { ServiceDefinition, ServiceSecret } from '../lib/api/types'

export function ServiceDetailPage() {
  const { serviceId } = useParams<{ serviceId: string }>()
  const [svc, setSvc] = useState<ServiceDefinition | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MountainApiError | null>(null)
  const [acting, setActing] = useState(false)
  const [actionMsg, setActionMsg] = useState<string | null>(null)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)

  // Secrets state
  const [secrets, setSecrets] = useState<ServiceSecret[]>([])
  const [secretsLoading, setSecretsLoading] = useState(false)
  const [secretValues, setSecretValues] = useState<Record<string, string>>({})
  const [secretAction, setSecretAction] = useState<string | null>(null)
  const [secretError, setSecretError] = useState<string | null>(null)

  const load = () => {
    if (!serviceId) return
    setIsLoading(true)
    setError(null)
    fetchService(serviceId)
      .then(setSvc)
      .catch(err => { if (err instanceof MountainApiError) setError(err) })
      .finally(() => setIsLoading(false))
  }

  const loadSecrets = () => {
    if (!serviceId) return
    setSecretsLoading(true)
    fetchServiceSecrets(serviceId)
      .then(setSecrets)
      .catch(() => {})
      .finally(() => setSecretsLoading(false))
  }

  useEffect(() => { load(); loadSecrets() }, [serviceId])

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

  const handleSaveSecret = async (key: string) => {
    if (!serviceId) return
    const value = secretValues[key]
    if (!value) return
    setSecretAction(key)
    setSecretError(null)
    try {
      await setServiceSecret(serviceId, { key, value })
      setSecretValues(prev => ({ ...prev, [key]: '' }))
      loadSecrets()
      load()
    } catch (err) {
      setSecretError(err instanceof MountainApiError ? `保存 ${key} 失败: ${err.message}` : `保存 ${key} 失败`)
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
      setSecretError(err instanceof MountainApiError ? `删除 ${key} 失败: ${err.message}` : `删除 ${key} 失败`)
    } finally {
      setSecretAction(null)
    }
  }

  const handleDelete = async () => {
    if (!serviceId) return
    await doAction('删除', () => deleteService(serviceId))
    setShowDeleteDialog(false)
    if (!actionMsg?.includes('失败')) {
      window.history.back()
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
          onClick={() => doAction('探测', () => probeService(svc.service_id))}
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

      {/* Config status */}
      <div className="card">
        <div className="card-title">配置状态</div>
        <div className="settings-row">
          <span className="k">配置</span>
          <span className="v"><StatusBadge status={svc.config_status === 'ok' || svc.config_status === 'configured' ? 'succeeded' : 'failed'} label={svc.config_status} /></span>
        </div>
        <div className="settings-row">
          <span className="k">Secret</span>
          <span className="v"><StatusBadge status={svc.secret_status === 'ok' || svc.secret_status === 'configured' ? 'succeeded' : svc.secret_status === 'required' ? 'pending' : 'failed'} label={svc.secret_status} /></span>
        </div>
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
      <div className="card">
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
