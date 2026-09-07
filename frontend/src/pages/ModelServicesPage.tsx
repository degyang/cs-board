import { useCallback, useEffect, useMemo, useState } from 'react'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { MountainApiError } from '../lib/api/http'
import { createService, deleteService, fetchServices, setDefaultService, updateService, fetchServiceSecrets, setServiceSecret, deleteServiceSecret } from '../lib/api/services'
import type { ServiceDefinition, ServiceSecret } from '../lib/api/types'

const CAPABILITIES = [
  ['text_generation', '文本'], ['multimodal', '多模态'], ['image_generation', '图片'],
  ['video_generation', '视频'], ['audio_generation', '音频'],
] as const
const ADAPTERS = [
  ['openai_compatible', 'OpenAI 兼容'],
  ['anthropic_compatible', 'Anthropic 兼容'],
  ['other', '其他（待 Provider 定制）'],
] as const
/** Adapter types that require api_key in required_secrets. */
const API_KEY_ADAPTERS = new Set(['openai_compatible', 'anthropic_compatible'])
const LOCAL_ADAPTERS = new Set(['indextts', 'codex_skill', 'ffmpeg', 'local_process'])
const LOCAL_IDS = new Set(['local-indextts', 'local-ffmpeg', 'whiteboard-renderer', 'codex-skills'])

type Draft = {
  displayName: string
  capabilities: string[]
  adapterType: string
  endpoint: string
  models: string
  makeDefault: boolean
  apiKey: string
}

function isLocal(service: ServiceDefinition) {
  return LOCAL_IDS.has(service.service_id) || LOCAL_ADAPTERS.has(service.adapter_type) || service.service_id.startsWith('local-')
}

function capabilitiesOf(service: ServiceDefinition): string[] {
  const configured = service.config.capabilities
  if (Array.isArray(configured)) {
    const values = configured.filter((value): value is string => typeof value === 'string' && value.length > 0)
    if (values.length) return values
  }
  return [service.capability]
}

const capabilityLabel = (value: string) => CAPABILITIES.find(([key]) => key === value)?.[1] ?? value
const adapterLabel = (value: string) => ADAPTERS.find(([key]) => key === value)?.[1] ?? value

function generateId() {
  const suffix = typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID().slice(0, 8)
    : Date.now().toString(36)
  return `model-service-${suffix}`
}

function toDraft(service?: ServiceDefinition): Draft {
  return {
    displayName: service?.display_name ?? '',
    capabilities: service ? capabilitiesOf(service) : ['text_generation'],
    adapterType: service?.adapter_type ?? 'openai_compatible',
    endpoint: service?.endpoint ?? '',
    models: service?.model ?? '',
    makeDefault: service?.is_default ?? false,
    apiKey: '',
  }
}

function Editor({ id, initial, saving, error, submitLabel, onCancel, onSubmit, secretStatus }: {
  id: string
  initial: Draft
  saving: boolean
  error: string | null
  submitLabel: string
  onCancel: () => void
  onSubmit: (draft: Draft) => void
  secretStatus?: ServiceSecret | null
}) {
  const [draft, setDraft] = useState(initial)
  const [showApiKey, setShowApiKey] = useState(false)
  useEffect(() => { setDraft(initial); setShowApiKey(false) }, [initial])

  return (
    <form className="ms-inline-form" onSubmit={event => { event.preventDefault(); onSubmit(draft) }}>
      {error && <div className="error-card" role="alert">{error}</div>}
      <div className="field"><label htmlFor={`${id}-name`}>名称</label><input id={`${id}-name`} className="input" required value={draft.displayName} onChange={event => setDraft(current => ({ ...current, displayName: event.target.value }))} /></div>
      <div className="field">
        <label>能力（可多选）</label>
        <div className="ms-capability-picker" role="group" aria-label="能力">
          {CAPABILITIES.map(([key, label]) => <label key={key} className={`ms-choice${draft.capabilities.includes(key) ? ' on' : ''}`}><input type="checkbox" checked={draft.capabilities.includes(key)} onChange={event => setDraft(current => ({ ...current, capabilities: event.target.checked ? [...current.capabilities, key] : current.capabilities.filter(item => item !== key) }))} />{label}</label>)}
        </div>
      </div>
      <div className="field"><label htmlFor={`${id}-adapter`}>适配器</label><select id={`${id}-adapter`} className="select" value={draft.adapterType} onChange={event => setDraft(current => ({ ...current, adapterType: event.target.value }))}>{ADAPTERS.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select>{draft.adapterType === 'other' && <p className="form-help">其他适配器需要根据厂商 API 由 Provider 定制，参考 URL 确认后再补充。</p>}</div>
      <div className="field"><label htmlFor={`${id}-url`}>BaseURL</label><input id={`${id}-url`} className="input mono" type="url" placeholder="https://api.example.com/v1" value={draft.endpoint} onChange={event => setDraft(current => ({ ...current, endpoint: event.target.value }))} /></div>
      <div className="field"><label htmlFor={`${id}-models`}>模型（多个用逗号分隔）</label><input id={`${id}-models`} className="input" placeholder="model-a, model-b" value={draft.models} onChange={event => setDraft(current => ({ ...current, models: event.target.value }))} /></div>
      <div className="field">
        <label htmlFor={`${id}-apikey`}>API Key</label>
        {secretStatus?.configured && !draft.apiKey && <span className="secret-masked" style={{ fontSize: '0.85em', color: 'var(--nt-muted, #888)' }}>已配置：{secretStatus.masked_value ?? '****'}</span>}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input
            id={`${id}-apikey`}
            type={showApiKey ? 'text' : 'password'}
            className="input"
            autoComplete="new-password"
            value={draft.apiKey}
            onChange={event => setDraft(current => ({ ...current, apiKey: event.target.value }))}
            placeholder={secretStatus?.configured ? '留空保留原密钥，输入新值替换' : '输入 API Key'}
          />
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowApiKey(v => !v)} aria-label={showApiKey ? '隐藏 API Key' : '显示 API Key'}>{showApiKey ? '🙈 隐藏' : '👁 显示'}</button>
        </div>
        <div className="form-help">密钥只通过 Secret API 写入，不会保存在服务配置中。</div>
      </div>
      <div className="field"><label htmlFor={`${id}-service-id`}>服务 ID（自动生成）</label><input id={`${id}-service-id`} className="input mono" value={id} readOnly /></div>
      <label className="ms-default-choice"><input type="checkbox" checked={draft.makeDefault} onChange={event => setDraft(current => ({ ...current, makeDefault: event.target.checked }))} /> 默认服务</label>
      <div className="ms-editor-actions"><button type="submit" className="btn btn-primary btn-sm" disabled={saving || draft.capabilities.length === 0}>{saving ? '保存中...' : submitLabel}</button><button type="button" className="btn btn-ghost btn-sm" onClick={onCancel} disabled={saving}>取消</button></div>
    </form>
  )
}

function Detail({ service, onSaved, onDelete }: { service: ServiceDefinition; onSaved: () => Promise<void>; onDelete: () => void }) {
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [apiKeySecret, setApiKeySecret] = useState<ServiceSecret | null>(null)
  const [clearTarget, setClearTarget] = useState<string | null>(null)
  const initial = useMemo(() => toDraft(service), [service])
  useEffect(() => { setEditing(false); setError(null) }, [service.service_id, service.revision])

  // Load secret status for API Key
  useEffect(() => {
    let cancelled = false
    fetchServiceSecrets(service.service_id)
      .then(res => {
        if (cancelled) return
        const key = res.items.find(s => s.secret_key === 'api_key') ?? null
        setApiKeySecret(key)
      })
      .catch(() => { if (!cancelled) setApiKeySecret(null) })
    return () => { cancelled = true }
  }, [service.service_id, service.revision])

  const save = async (draft: Draft) => {
    if (!draft.capabilities.length) { setError('至少选择一项能力'); return }
    setSaving(true); setError(null)
    try {
      // If adapter type requires api_key but service doesn't declare it, patch required_secrets first
      const needsApiKey = API_KEY_ADAPTERS.has(draft.adapterType)
      const hasApiKeyDeclared = service.required_secrets.includes('api_key')
      const patchSecrets = needsApiKey && !hasApiKeyDeclared
      await updateService(service.service_id, {
        display_name: draft.displayName.trim(), capability: draft.capabilities[0],
        adapter_type: draft.adapterType, endpoint: draft.endpoint, model: draft.models,
        config: { ...service.config, capabilities: draft.capabilities },
        ...(patchSecrets ? { required_secrets: [...service.required_secrets, 'api_key'] } : {}),
      })
      if (draft.makeDefault && !service.is_default) await setDefaultService(service.service_id)
      // Write API Key via Secret API if provided
      if (draft.apiKey) {
        await setServiceSecret(service.service_id, { key: 'api_key', value: draft.apiKey })
      }
      setEditing(false); await onSaved()
    } catch (reason) { setError(reason instanceof Error ? reason.message : '保存失败') }
    finally { setSaving(false) }
  }

  const handleClearApiKey = async () => {
    try {
      await deleteServiceSecret(service.service_id, 'api_key')
      setApiKeySecret(null)
      setClearTarget(null)
      await onSaved()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '清除 API Key 失败')
      setClearTarget(null)
    }
  }

  return <div className="ms-detail-card">
    <div className="am-detail-head"><div className="mp-card-icon">{service.display_name[0] ?? '?'}</div><div className="am-detail-heading"><h2 className="am-detail-name">{editing ? '编辑模型服务' : service.display_name}</h2><div className="am-detail-tag">模型服务 · revision {service.revision}</div></div>{!editing && <div className="am-tools"><button type="button" className="btn btn-primary btn-sm" onClick={() => setEditing(true)}>编辑</button><button type="button" className="btn btn-danger btn-sm" onClick={onDelete}>删除</button></div>}</div>
    {editing ? <Editor id={`edit-${service.service_id}`} initial={initial} saving={saving} error={error} submitLabel="保存" onCancel={() => { setEditing(false); setError(null) }} onSubmit={save} secretStatus={apiKeySecret} /> : <div className="ms-preview">
      {error && <div className="error-card" role="alert" style={{ marginBottom: 8 }}>{error}</div>}
      <div className="settings-row"><span className="k">名称</span><span className="v">{service.display_name}</span></div>
      <div className="settings-row"><span className="k">能力</span><span className="v ms-chip-row">{capabilitiesOf(service).map(item => <span className="mp-category-badge" key={item}>{capabilityLabel(item)}</span>)}</span></div>
      <div className="settings-row"><span className="k">适配器</span><span className="v"><span className="mp-model-chip">{adapterLabel(service.adapter_type)}</span></span></div>
      <div className="settings-row"><span className="k">BaseURL</span><span className="v mono">{service.endpoint || '—'}</span></div>
      <div className="settings-row"><span className="k">模型</span><span className="v ms-chip-row">{service.model ? service.model.split(',').map(item => item.trim()).filter(Boolean).map(item => <span className="mp-model-chip" key={item}>{item}</span>) : '—'}</span></div>
      <div className="settings-row"><span className="k">API Key</span><span className="v">{apiKeySecret?.configured ? <>{apiKeySecret.masked_value ?? '****'} <button type="button" className="btn btn-danger btn-sm" onClick={() => setClearTarget('api_key')} style={{ marginLeft: 8 }}>清除</button></> : '未配置'}</span></div>
      <div className="settings-row"><span className="k">服务 ID</span><span className="v mono">{service.service_id}</span></div>
      <div className="settings-row"><span className="k">默认</span><span className="v">{service.is_default ? '是' : '否'}</span></div>
    </div>}
    <ConfirmDialog open={clearTarget !== null} title="清除 API Key" message="确定清除该服务的 API Key？清除后需要重新输入才能使用。" confirmLabel="清除" danger onConfirm={handleClearApiKey} onCancel={() => setClearTarget(null)} />
  </div>
}

export function ModelServicesPage() {
  const [services, setServices] = useState<ServiceDefinition[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [createId, setCreateId] = useState(generateId)
  const [saving, setSaving] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<ServiceDefinition | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const external = (await fetchServices()).items.filter(service => !isLocal(service))
      setServices(external)
      setSelectedId(current => external.some(service => service.service_id === current) ? current : external[0]?.service_id ?? null)
    } catch (reason) { setError(reason instanceof MountainApiError || reason instanceof Error ? reason.message : '加载失败') }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { load() }, [load])

  const visible = services.filter(service => `${service.display_name} ${service.service_id} ${service.model ?? ''}`.toLocaleLowerCase().includes(search.toLocaleLowerCase()))
  const selected = services.find(service => service.service_id === selectedId) ?? null

  const create = async (draft: Draft) => {
    if (!draft.capabilities.length) { setError('至少选择一项能力'); return }
    setSaving(true); setError(null)
    try {
      const secrets = API_KEY_ADAPTERS.has(draft.adapterType) ? ['api_key'] : []
      const created = await createService({ service_id: createId, display_name: draft.displayName.trim(), capability: draft.capabilities[0], adapter_type: draft.adapterType, endpoint: draft.endpoint || undefined, model: draft.models || undefined, required_secrets: secrets, config: { capabilities: draft.capabilities } })
      if (draft.apiKey) {
        await setServiceSecret(created.service_id, { key: 'api_key', value: draft.apiKey })
      }
      if (draft.makeDefault && !created.is_default) await setDefaultService(created.service_id)
      setCreating(false); setFeedback('已创建模型服务'); setCreateId(generateId()); await load(); setSelectedId(created.service_id)
    } catch (reason) { setError(reason instanceof Error ? reason.message : '创建失败') }
    finally { setSaving(false) }
  }

  const remove = async () => {
    if (!deleteTarget) return
    try { await deleteService(deleteTarget.service_id); setFeedback('已删除模型服务'); setDeleteTarget(null); await load() }
    catch (reason) { setError(reason instanceof Error ? reason.message : '删除失败'); setDeleteTarget(null) }
  }

  return <div className="set-models">
    <div className="ms-layout">
      <aside className="am-list ms-list">
        <div className="am-list-head"><div className="am-search-wrap"><span className="am-search-ico" aria-hidden="true">🔍</span><input className="input am-search-input" type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="搜索模型服务…" aria-label="搜索模型服务" /></div><div className="am-list-action"><button type="button" className="btn btn-primary btn-sm" onClick={() => { setCreating(true); setError(null) }}>+ 新建模型服务</button></div></div>
        {loading && <div className="am-loading">加载中...</div>}
        {!loading && !visible.length && <div className="am-list-empty">暂无模型服务</div>}
        {visible.map(service => <button key={service.service_id} type="button" className={`am-item am-list-item${selectedId === service.service_id ? ' on am-list-item--selected' : ''}`} onClick={() => setSelectedId(service.service_id)}><div className="mp-card-icon">{service.display_name[0] ?? '?'}</div><div className="am-list-item-main"><div className="am-list-item-name">{service.display_name}</div><div className="am-list-item-desc">{adapterLabel(service.adapter_type)} · {service.model || '未填写模型'}</div><div className="ms-list-caps">{capabilitiesOf(service).map(item => <span className="am-tag am-tag-sm" key={item}>{capabilityLabel(item)}</span>)}</div></div>{service.is_default && <span className="badge tag-info">默认</span>}</button>)}
      </aside>
      <section className="am-detail ms-detail">{feedback && <div className="am-feedback" role="status">{feedback}</div>}{error && !creating && <div className="error-card" role="alert">{error}</div>}{selected ? <Detail service={selected} onSaved={async () => { setFeedback('已保存模型服务'); await load() }} onDelete={() => setDeleteTarget(selected)} /> : !loading && <div className="am-detail-empty"><strong>暂无模型服务</strong><span>从左侧新建服务。</span></div>}</section>
    </div>
    {creating && <div className="modal-backdrop" role="presentation"><div className="modal" role="dialog" aria-modal="true" aria-label="新建模型服务"><div className="modal-head"><h2>新建模型服务</h2></div><Editor id={createId} initial={toDraft()} saving={saving} error={error} submitLabel="创建" onCancel={() => { setCreating(false); setError(null) }} onSubmit={create} /></div></div>}
    <ConfirmDialog open={deleteTarget !== null} title="删除模型服务" message={deleteTarget ? `确定删除「${deleteTarget.display_name}」？` : ''} confirmLabel="删除" danger onConfirm={remove} onCancel={() => setDeleteTarget(null)} />
  </div>
}
