/* ==========================================================================
   本地服务 — Voice Alignment / Local Services Page

   Left-list / right-detail layout for managing local speech services:
   TTS (speech_synthesis), voice alignment (speech_alignment), and IndexTTS.

   All CRUD and probe actions use the real /services API; no mock state.
   ========================================================================== */

import { useState, useEffect, useCallback } from 'react'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import {
  fetchServices,
  createService,
  updateService,
  deleteService,
  probeService,
  setServiceSecret,
  fetchServiceSecrets,
} from '../lib/api/services'
import type { ServiceDefinition, ServiceAvailability, ServiceSecret } from '../lib/api/types'

/** Capabilities available to locally managed speech services. */
const LOCAL_CAPABILITIES = ['speech_synthesis', 'speech_alignment', 'indextts']

/** Structured Whisper exclusion — never rely on display-name text matching. */
const isWhisperService = (s: ServiceDefinition) =>
  s.adapter_type === 'whisper' || s.service_id === 'local-whisper'

const CAPABILITY_OPTIONS: Array<[string, string]> = [
  ['speech_synthesis', '语音合成 (TTS)'],
  ['speech_alignment', '语音对齐'],
  ['indextts', 'IndexTTS'],
]

const ADAPTER_OPTIONS: Array<[string, string]> = [
  ['openai_compatible', 'OpenAI 兼容'],
  ['indextts', 'IndexTTS'],
  ['local_process', '本地进程'],
  ['other', '其他'],
]

const capabilityLabel = (value: string) =>
  CAPABILITY_OPTIONS.find(([k]) => k === value)?.[1] ?? value

const adapterLabel = (value: string) =>
  ADAPTER_OPTIONS.find(([k]) => k === value)?.[1] ?? value

function generateLocalId() {
  const suffix =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID().slice(0, 8)
      : Date.now().toString(36)
  return `local-${suffix}`
}

/* ── Service Detail (right panel) ──────────────────────────────────────── */

function ServiceDetail({
  service,
  submitting,
  onSaved,
  onDelete,
}: {
  service: ServiceDefinition
  submitting: string | null
  onSaved: () => void | Promise<void>
  onDelete: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)
  const [probing, setProbing] = useState(false)
  const [probeResult, setProbeResult] = useState<ServiceAvailability | null>(null)
  const [probeMsg, setProbeMsg] = useState<string | null>(null)

  // Edit draft state
  const [draftName, setDraftName] = useState(service.display_name)
  const [draftCapability, setDraftCapability] = useState(service.capability)
  const [draftAdapter, setDraftAdapter] = useState(service.adapter_type)
  const [draftEndpoint, setDraftEndpoint] = useState(service.endpoint ?? '')
  const [draftModel, setDraftModel] = useState(service.model ?? '')
  const [draftPriority, setDraftPriority] = useState(String(service.priority))
  const [draftEnabled, setDraftEnabled] = useState(service.enabled)
  const [draftApiKey, setDraftApiKey] = useState('')
  const [apiKeySecret, setApiKeySecret] = useState<ServiceSecret | null>(null)

  // Reset draft when service changes
  useEffect(() => {
    setDraftName(service.display_name)
    setDraftCapability(service.capability)
    setDraftAdapter(service.adapter_type)
    setDraftEndpoint(service.endpoint ?? '')
    setDraftModel(service.model ?? '')
    setDraftPriority(String(service.priority))
    setDraftEnabled(service.enabled)
    setEditing(false)
    setEditError(null)
    setDraftApiKey('')
  }, [service.service_id, service.revision])

  // Load API key secret status
  useEffect(() => {
    let cancelled = false
    fetchServiceSecrets(service.service_id)
      .then(res => {
        if (cancelled) return
        const key = res.items.find(s => s.secret_key === 'api_key') ?? null
        setApiKeySecret(key)
      })
      .catch(() => {
        if (!cancelled) setApiKeySecret(null)
      })
    return () => {
      cancelled = true
    }
  }, [service.service_id, service.revision])

  const cancelEdit = () => {
    setDraftName(service.display_name)
    setDraftCapability(service.capability)
    setDraftAdapter(service.adapter_type)
    setDraftEndpoint(service.endpoint ?? '')
    setDraftModel(service.model ?? '')
    setDraftPriority(String(service.priority))
    setDraftEnabled(service.enabled)
    setDraftApiKey('')
    setEditing(false)
    setEditError(null)
  }

  const saveEdit = async () => {
    if (!draftName.trim()) {
      setEditError('显示名称不能为空')
      return
    }
    setSaving(true)
    setEditError(null)
    try {
      await updateService(service.service_id, {
        display_name: draftName.trim(),
        capability: draftCapability,
        adapter_type: draftAdapter,
        endpoint: draftEndpoint || undefined,
        model: draftModel || undefined,
        priority: Number(draftPriority),
        enabled: draftEnabled,
      })
      if (draftApiKey) {
        await setServiceSecret(service.service_id, { key: 'api_key', value: draftApiKey })
        setDraftApiKey('')
      }
      setEditing(false)
      await onSaved()
    } catch (err) {
      setEditError(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleProbe = async () => {
    setProbing(true)
    setProbeMsg(null)
    setProbeResult(null)
    try {
      const result = await probeService(service.service_id)
      await onSaved()
      // Refresh can replace the selected service object. Apply the transient
      // result after it completes so the right-hand preview retains it.
      setProbeResult(result)
      setProbeMsg('探测完成')
    } catch (err) {
      setProbeMsg(err instanceof Error ? err.message : '探测失败')
    } finally {
      setProbing(false)
    }
  }

  return (
    <>
      <div className="am-detail-head">
        <div className="mp-card-icon">{service.display_name[0] ?? '?'}</div>
        <div>
          <h2 className="am-detail-name">{editing ? '编辑本地服务' : service.display_name}</h2>
          <div className="am-detail-tag">
            {capabilityLabel(service.capability)} · 修订 {service.revision}
          </div>
        </div>
        <div className="am-tools">
          {editing ? (
            <>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={saveEdit}
                disabled={saving}
              >
                {saving ? '保存中...' : '保存'}
              </button>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={cancelEdit}
                disabled={saving}
              >
                取消
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => setEditing(true)}
                disabled={submitting !== null}
              >
                编辑
              </button>
              <button
                type="button"
                className="btn btn-danger btn-sm"
                onClick={onDelete}
                disabled={submitting !== null}
              >
                删除
              </button>
            </>
          )}
        </div>
      </div>

      {editError && (
        <div className="error-card" role="alert">
          {editError}
        </div>
      )}

      <section className="am-detail-section" aria-label="服务预览">
        <h3 className="am-section-title">服务预览</h3>
        <div className="am-detail-field">
          <span className="am-detail-label">当前服务:</span>
          {service.display_name}
        </div>
        <div className="am-detail-field">
          <span className="am-detail-label">预览状态:</span>
          {editing ? '正在编辑，保存后将更新预览' : '查看详情'}
        </div>
      </section>

      {/* Connectivity / Probe */}
      <section className="am-detail-section" aria-label="连通性探测">
        <h3 className="am-section-title">连通性</h3>
        <div className="am-detail-field">
          <span className="am-detail-label">状态:</span>
          {service.availability.available ? (
            <span className="mp-badge" style={{ background: 'var(--nt-primary-100)', color: 'var(--nt-primary-700)' }}>
              可用
            </span>
          ) : (
            <span className="mp-badge" style={{ background: '#F9E5E0', color: 'var(--nt-danger)' }}>
              不可用
            </span>
          )}
        </div>
        {service.availability.checked_at && (
          <div className="am-detail-field">
            <span className="am-detail-label">上次检查:</span>
            {new Date(service.availability.checked_at).toLocaleString('zh-CN')}
          </div>
        )}
        {service.availability.latency_ms != null && (
          <div className="am-detail-field">
            <span className="am-detail-label">延迟:</span>
            {service.availability.latency_ms}ms
          </div>
        )}
        {service.availability.error_code && (
          <div className="am-detail-field">
            <span className="am-detail-label">错误码:</span>
            <span style={{ color: 'var(--nt-danger)' }}>{service.availability.error_code}</span>
          </div>
        )}
        {service.availability.suggestion && (
          <div className="am-detail-field">
            <span className="am-detail-label">建议:</span>
            {service.availability.suggestion}
          </div>
        )}
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={handleProbe}
          disabled={probing}
        >
          {probing ? '探测中...' : '探测连通性'}
        </button>
        {probeMsg && (
          <div className="va-feedback" style={{ marginTop: 8 }}>{probeMsg}</div>
        )}
        {probeResult && (
          <div className="am-detail-field" style={{ marginTop: 8 }}>
            <span className="am-detail-label">探测结果:</span>
            <span style={{ color: probeResult.available ? 'var(--nt-primary-700)' : 'var(--nt-danger)' }}>
              {probeResult.available ? '可用' : '不可用'}
            </span>
            {probeResult.latency_ms != null && ` · ${probeResult.latency_ms}ms`}
          </div>
        )}
      </section>

      {/* Service Info — editable */}
      <section className="am-detail-section" aria-label="服务信息">
        <h3 className="am-section-title">服务信息</h3>
        <div className="am-detail-field">
          <span className="am-detail-label">显示名称:</span>
          {editing ? (
            <input
              className="input"
              aria-label="显示名称"
              value={draftName}
              onChange={e => setDraftName(e.target.value)}
            />
          ) : (
            service.display_name
          )}
        </div>
        <div className="am-detail-field">
          <span className="am-detail-label">能力:</span>
          {editing ? (
            <select
              className="input"
              aria-label="能力"
              value={draftCapability}
              onChange={e => setDraftCapability(e.target.value)}
            >
              {CAPABILITY_OPTIONS.map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          ) : (
            capabilityLabel(service.capability)
          )}
        </div>
        <div className="am-detail-field">
          <span className="am-detail-label">适配器:</span>
          {editing ? (
            <select
              className="input"
              aria-label="适配器"
              value={draftAdapter}
              onChange={e => setDraftAdapter(e.target.value)}
            >
              {ADAPTER_OPTIONS.map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          ) : (
            adapterLabel(service.adapter_type)
          )}
        </div>
        <div className="am-detail-field">
          <span className="am-detail-label">端点:</span>
          {editing ? (
            <input
              className="input"
              aria-label="端点"
              value={draftEndpoint}
              onChange={e => setDraftEndpoint(e.target.value)}
              placeholder="http://127.0.0.1:9000/v1"
            />
          ) : (
            service.endpoint || '—'
          )}
        </div>
        <div className="am-detail-field">
          <span className="am-detail-label">模型:</span>
          {editing ? (
            <input
              className="input"
              aria-label="模型"
              value={draftModel}
              onChange={e => setDraftModel(e.target.value)}
              placeholder="模型 ID"
            />
          ) : (
            service.model || '—'
          )}
        </div>
        <div className="am-detail-field">
          <span className="am-detail-label">优先级:</span>
          {editing ? (
            <input
              className="input"
              aria-label="优先级"
              type="number"
              min="0"
              value={draftPriority}
              onChange={e => setDraftPriority(e.target.value)}
            />
          ) : (
            service.priority
          )}
        </div>
        <div className="am-detail-field">
          <span className="am-detail-label">启用:</span>
          {editing ? (
            <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <input
                type="checkbox"
                checked={draftEnabled}
                onChange={e => setDraftEnabled(e.target.checked)}
              />
              {draftEnabled ? '已启用' : '未启用'}
            </label>
          ) : (
            <span
              className={`am-status ${service.enabled ? 'am-status--active' : 'am-status--inactive'}`}
            >
              <span className="am-status-dot" aria-hidden="true" />
              {service.enabled ? '已启用' : '未启用'}
            </span>
          )}
        </div>
        {editing && (
          <div className="am-detail-field">
            <span className="am-detail-label">API Key:</span>
            <input
              className="input"
              aria-label="API Key"
              type="password"
              value={draftApiKey}
              onChange={e => setDraftApiKey(e.target.value)}
              placeholder={apiKeySecret?.configured ? '留空保留原密钥，输入新值替换' : '输入 API Key'}
            />
          </div>
        )}
      </section>

      {/* Config Status */}
      <section className="am-detail-section" aria-label="配置状态">
        <h3 className="am-section-title">配置状态</h3>
        <div className="am-detail-field">
          <span className="am-detail-label">配置:</span>
          <span
            className="mp-badge"
            style={{
              background: service.config_status.configured ? 'var(--nt-primary-100)' : '#F9E5E0',
              color: service.config_status.configured ? 'var(--nt-primary-700)' : 'var(--nt-danger)',
            }}
          >
            {service.config_status.configured ? '已配置' : '未配置'}
          </span>
        </div>
        {!service.config_status.configured && service.config_status.missing_fields.length > 0 && (
          <div className="am-detail-field">
            <span className="am-detail-label">缺少字段:</span>
            {service.config_status.missing_fields.join(', ')}
          </div>
        )}
        {!service.config_status.configured && service.config_status.missing_secrets.length > 0 && (
          <div className="am-detail-field">
            <span className="am-detail-label">缺少 Secret:</span>
            {service.config_status.missing_secrets.join(', ')}
          </div>
        )}
        <div className="am-detail-field">
          <span className="am-detail-label">Secret:</span>
          <span
            className="mp-badge"
            style={{
              background: service.secret_status.configured ? 'var(--nt-primary-100)' : '#F9E5E0',
              color: service.secret_status.configured ? 'var(--nt-primary-700)' : 'var(--nt-danger)',
            }}
          >
            {service.secret_status.configured ? '已配置' : '未配置'}
          </span>
        </div>
        {apiKeySecret?.configured && (
          <div className="am-detail-field">
            <span className="am-detail-label">API Key:</span>
            {apiKeySecret.masked_value ?? '****'}
          </div>
        )}
        <div className="am-detail-field">
          <span className="am-detail-label">服务 ID:</span>
          <span className="mono">{service.service_id}</span>
        </div>
      </section>
    </>
  )
}

/* ── Create Service Dialog ─────────────────────────────────────────────── */

function CreateServiceDialog({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: () => void | Promise<void>
}) {
  const [serviceId, setServiceId] = useState(generateLocalId)
  const [displayName, setDisplayName] = useState('')
  const [capability, setCapability] = useState('speech_synthesis')
  const [adapterType, setAdapterType] = useState('openai_compatible')
  const [endpoint, setEndpoint] = useState('')
  const [model, setModel] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!displayName.trim()) {
      setError('显示名称不能为空')
      return
    }
    setSaving(true)
    setError(null)
    try {
      const needsApiKey = adapterType === 'openai_compatible' || adapterType === 'anthropic_compatible'
      const requiredSecrets = needsApiKey ? ['api_key'] : []
      const created = await createService({
        service_id: serviceId,
        display_name: displayName.trim(),
        capability,
        adapter_type: adapterType,
        endpoint: endpoint || undefined,
        model: model || undefined,
        required_secrets: requiredSecrets.length > 0 ? requiredSecrets : undefined,
      })
      if (apiKey && needsApiKey) {
        await setServiceSecret(created.service_id, { key: 'api_key', value: apiKey })
      }
      await onCreated()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <h2 className="modal-title">新建本地服务</h2>
        {error && (
          <div className="error-card" role="alert">
            <div>{error}</div>
          </div>
        )}
        <form onSubmit={handleSubmit} className="style-form">
          <div className="form-field">
            <label className="form-label" htmlFor="new-svc-id">服务 ID *</label>
            <input
              id="new-svc-id"
              type="text"
              className="input mono"
              required
              value={serviceId}
              onChange={e => setServiceId(e.target.value)}
              pattern="[a-z0-9][a-z0-9_-]*"
              title="小写字母、数字、连字符、下划线"
            />
          </div>
          <div className="form-field">
            <label className="form-label" htmlFor="new-svc-name">显示名称 *</label>
            <input
              id="new-svc-name"
              type="text"
              className="input"
              required
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
              placeholder="我的 TTS 服务"
            />
          </div>
          <div className="form-field">
            <label className="form-label" htmlFor="new-svc-cap">能力 *</label>
            <select
              id="new-svc-cap"
              className="input"
              required
              value={capability}
              onChange={e => setCapability(e.target.value)}
            >
              {CAPABILITY_OPTIONS.map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div className="form-field">
            <label className="form-label" htmlFor="new-svc-adapter">适配器 *</label>
            <select
              id="new-svc-adapter"
              className="input"
              required
              value={adapterType}
              onChange={e => setAdapterType(e.target.value)}
            >
              {ADAPTER_OPTIONS.map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div className="form-field">
            <label className="form-label" htmlFor="new-svc-endpoint">端点</label>
            <input
              id="new-svc-endpoint"
              type="url"
              className="input"
              value={endpoint}
              onChange={e => setEndpoint(e.target.value)}
              placeholder="http://127.0.0.1:9000/v1"
            />
          </div>
          <div className="form-field">
            <label className="form-label" htmlFor="new-svc-model">模型</label>
            <input
              id="new-svc-model"
              type="text"
              className="input"
              value={model}
              onChange={e => setModel(e.target.value)}
              placeholder="模型 ID"
            />
          </div>
          {(adapterType === 'openai_compatible' || adapterType === 'anthropic_compatible') && (
            <div className="form-field">
              <label className="form-label" htmlFor="new-svc-key">API Key</label>
              <input
                id="new-svc-key"
                type="password"
                className="input"
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                placeholder="输入 API Key（可选）"
              />
              <div className="form-help">密钥只通过 Secret API 写入，不会保存在服务配置中。</div>
            </div>
          )}
          <div className="form-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>
              取消
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? '创建中...' : '创建服务'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

/* ── Main Page ─────────────────────────────────────────────────────────── */

export function VoiceAlignmentPage() {
  const [services, setServices] = useState<ServiceDefinition[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<ServiceDefinition | null>(null)

  const load = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true)
    setError(null)
    try {
      const allServices = (await fetchServices()).items
      const localServices = allServices.filter(
        s => LOCAL_CAPABILITIES.includes(s.capability) && !isWhisperService(s),
      )
      setServices(localServices)
      setSelectedId(current =>
        current && localServices.some(s => s.service_id === current)
          ? current
          : localServices[0]?.service_id ?? null,
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      if (showLoading) setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(true)
  }, [load])

  const selected = services.find(s => s.service_id === selectedId) ?? null

  const handleDelete = async () => {
    if (!deleteTarget) return
    const id = deleteTarget.service_id
    setSubmitting(id)
    setFeedback(null)
    try {
      await deleteService(id)
      setFeedback('已删除本地服务')
      setDeleteTarget(null)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败')
      setDeleteTarget(null)
    } finally {
      setSubmitting(null)
    }
  }

  const handleSaved = async () => {
    setFeedback('已保存')
    await load()
  }

  if (loading) {
    return (
      <div className="page-container">
        <div className="va-loading">加载中...</div>
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="page-head">
        <h1 className="page-title">本地服务</h1>
        <p className="page-desc">管理本地语音服务、配置与连通性。</p>
      </div>
      {feedback && <div className="va-feedback">{feedback}</div>}
      {error && (
        <div className="va-error" role="alert">
          {error}
        </div>
      )}

      <div className="am-body am-layout">
        {/* Left: service list */}
        <div className="am-list">
          <div className="am-list-head">
            <div className="am-list-action">
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => setShowCreate(true)}
              >
                + 新建本地服务
              </button>
            </div>
          </div>
          {services.length === 0 && (
            <div className="am-list-empty">未配置本地语音服务</div>
          )}
          {services.map(svc => (
            <button
              key={svc.service_id}
              type="button"
              className={`am-item am-list-item${selectedId === svc.service_id ? ' on am-list-item--selected' : ''}`}
              onClick={() => setSelectedId(svc.service_id)}
            >
              <div className="mp-card-icon">{svc.display_name[0] ?? '?'}</div>
              <div className="am-item-main am-list-item-main">
                <div className="am-list-item-name">{svc.display_name}</div>
                <div className="am-list-item-desc">
                  {capabilityLabel(svc.capability)} · {svc.model || '未配置模型'}
                </div>
                <div className="am-list-item-desc">
                  <span
                    className="mp-badge"
                    style={{
                      background: svc.availability.available
                        ? 'var(--nt-primary-100)'
                        : '#F9E5E0',
                      color: svc.availability.available
                        ? 'var(--nt-primary-700)'
                        : 'var(--nt-danger)',
                    }}
                  >
                    {svc.availability.available ? '可用' : '不可用'}
                  </span>
                </div>
              </div>
            </button>
          ))}
        </div>

        {/* Right: detail */}
        <div className="am-detail">
          {selected ? (
            <ServiceDetail
              key={selected.service_id}
              service={selected}
              submitting={submitting}
              onSaved={handleSaved}
              onDelete={() => setDeleteTarget(selected)}
            />
          ) : (
            <div className="am-detail-empty">
              <strong>{services.length === 0 ? '暂无本地服务' : '从左侧列表选择一项'}</strong>
              <span>可新建本地语音服务。</span>
            </div>
          )}
        </div>
      </div>

      {/* Create dialog */}
      {showCreate && (
        <CreateServiceDialog
          onClose={() => setShowCreate(false)}
          onCreated={async () => {
            setFeedback('已创建本地服务')
            await load()
          }}
        />
      )}

      {/* Delete confirmation */}
      <ConfirmDialog
        open={deleteTarget !== null}
        title="删除本地服务"
        message={
          deleteTarget
            ? `确定删除「${deleteTarget.display_name}」？此操作不可恢复。`
            : ''
        }
        confirmLabel="删除"
        danger
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}
