/* ==========================================================================
   Service Form Page — Create or edit a dynamic service.
   /settings/models/new       -> create mode
   /settings/models/:id/edit  -> edit mode
   ========================================================================== */

import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { BackButton } from '../components/ui/BackButton'
import { MountainApiError } from '../lib/api/http'
import { createService, fetchService, updateService } from '../lib/api/services'
import { KNOWN_CAPABILITIES, KNOWN_ADAPTERS } from '../lib/api/types'

export function ServiceFormPage() {
  const { serviceId } = useParams<{ serviceId: string }>()
  const isEdit = !!serviceId
  const navigate = useNavigate()

  const [displayName, setDisplayName] = useState('')
  const [capability, setCapability] = useState('text_generation')
  const [adapterType, setAdapterType] = useState('openai_compatible')
  const [endpoint, setEndpoint] = useState('')
  const [model, setModel] = useState('')
  const [priority, setPriority] = useState('10')
  const [enabled, setEnabled] = useState(true)
  const [configJson, setConfigJson] = useState('{}')
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isEdit || !serviceId) return
    setIsLoading(true)
    fetchService(serviceId)
      .then(svc => {
        setDisplayName(svc.display_name)
        setCapability(svc.capability)
        setAdapterType(svc.adapter_type)
        setEndpoint(svc.endpoint ?? '')
        setModel(svc.model ?? '')
        setPriority(String(svc.priority))
        setEnabled(svc.enabled)
        setConfigJson(JSON.stringify(svc.config, null, 2))
      })
      .catch(err => {
        setError(err instanceof MountainApiError ? err.message : '加载失败')
      })
      .finally(() => setIsLoading(false))
  }, [isEdit, serviceId])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    let config: Record<string, unknown> = {}
    try {
      config = JSON.parse(configJson)
    } catch {
      setError('config JSON 格式错误')
      return
    }

    setIsSaving(true)
    try {
      if (isEdit && serviceId) {
        await updateService(serviceId, {
          display_name: displayName,
          capability,
          adapter_type: adapterType,
          endpoint: endpoint || undefined,
          model: model || undefined,
          priority: Number(priority),
          enabled,
          config,
        })
      } else {
        await createService({
          display_name: displayName,
          capability,
          adapter_type: adapterType,
          endpoint: endpoint || undefined,
          model: model || undefined,
          priority: Number(priority),
          enabled,
          config,
        })
      }
      navigate('/settings/models')
    } catch (err) {
      setError(err instanceof MountainApiError ? err.message : '保存失败')
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) return <div className="page"><div className="loading"><span className="spinner" />加载中...</div></div>

  return (
    <div className="page">
      <BackButton to="/settings/models" label="返回模型服务" />

      <div className="page-head">
        <h1 className="page-title">{isEdit ? '编辑服务' : '新建服务'}</h1>
      </div>

      {error && (
        <div className="error-card" role="alert"><div>{error}</div></div>
      )}

      <form onSubmit={handleSubmit} className="service-form">
        <div className="form-field">
          <label className="form-label" htmlFor="svc-name">显示名称 *</label>
          <input id="svc-name" type="text" className="input" required value={displayName} onChange={e => setDisplayName(e.target.value)} />
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="svc-capability">能力 *</label>
          <select id="svc-capability" className="select" value={capability} onChange={e => setCapability(e.target.value)}>
            {Object.entries(KNOWN_CAPABILITIES).map(([k, v]) => (
              <option key={k} value={k}>{v} ({k})</option>
            ))}
          </select>
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="svc-adapter">适配器 *</label>
          <select id="svc-adapter" className="select" value={adapterType} onChange={e => setAdapterType(e.target.value)}>
            {Object.entries(KNOWN_ADAPTERS).map(([k, v]) => (
              <option key={k} value={k}>{v} ({k})</option>
            ))}
          </select>
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="svc-endpoint">端点</label>
          <input id="svc-endpoint" type="text" className="input" placeholder="https://..." value={endpoint} onChange={e => setEndpoint(e.target.value)} />
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="svc-model">模型</label>
          <input id="svc-model" type="text" className="input" placeholder="gpt-4" value={model} onChange={e => setModel(e.target.value)} />
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="svc-priority">优先级</label>
          <input id="svc-priority" type="number" className="input" min="0" value={priority} onChange={e => setPriority(e.target.value)} />
        </div>

        <div className="form-field">
          <label className="form-label">
            <input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} />
            {' '}启用
          </label>
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="svc-config">Config (JSON)</label>
          <textarea id="svc-config" className="input mono" rows={4} value={configJson} onChange={e => setConfigJson(e.target.value)} />
        </div>

        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={() => navigate('/settings/models')}>取消</button>
          <button type="submit" className="btn btn-primary" disabled={isSaving}>
            {isSaving ? '保存中...' : (isEdit ? '保存修改' : '创建服务')}
          </button>
        </div>
      </form>
    </div>
  )
}
