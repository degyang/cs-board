/* ==========================================================================
   Service Detail Page — Detailed view of a single service.
   ========================================================================== */

import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { StatusBadge } from '../components/ui/StatusBadge'
import { MountainApiError } from '../lib/api/http'
import {
  fetchService,
  updateServiceConfig,
  fetchServiceSecrets,
  setServiceSecret,
  deleteServiceSecret,
} from '../lib/api/services'
import type { ServiceDetail, ServiceSecret } from '../lib/api/types'

export default function ServiceDetailPage() {
  const { serviceId } = useParams<{ serviceId: string }>()

  if (!serviceId) {
    return <div className="set-error">服务 ID 不存在</div>
  }

  return <ServiceDetailContent serviceId={serviceId} />
}

function ServiceDetailContent({ serviceId }: { serviceId: string }) {
  const [service, setService] = useState<ServiceDetail | null>(null)
  const [secrets, setSecrets] = useState<ServiceSecret[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MountainApiError | null>(null)

  const [configJson, setConfigJson] = useState('')
  const [configError, setConfigError] = useState<string | null>(null)
  const [isSavingConfig, setIsSavingConfig] = useState(false)

  const [newKey, setNewKey] = useState('')
  const [newValue, setNewValue] = useState('')
  const [secretError, setSecretError] = useState<string | null>(null)
  const [isAddingSecret, setIsAddingSecret] = useState(false)

  useEffect(() => {
    Promise.all([
      fetchService(serviceId),
      fetchServiceSecrets(serviceId),
    ])
      .then(([svc, secs]) => {
        setService(svc)
        setSecrets(secs)
        setConfigJson(JSON.stringify(svc.config, null, 2))
      })
      .catch(err => {
        if (err instanceof MountainApiError) setError(err)
      })
      .finally(() => setIsLoading(false))
  }, [serviceId])

  const handleConfigSave = async () => {
    try {
      const parsed = JSON.parse(configJson) as Record<string, unknown>
      setIsSavingConfig(true)
      setConfigError(null)
      const updated = await updateServiceConfig(serviceId, parsed)
      setService(updated)
    } catch (err) {
      if (err instanceof SyntaxError) {
        setConfigError('JSON 格式错误')
      } else {
        setConfigError(err instanceof MountainApiError ? err.message : '更新失败')
      }
    } finally {
      setIsSavingConfig(false)
    }
  }

  const handleAddSecret = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newKey.trim() || !newValue) return
    setIsAddingSecret(true)
    setSecretError(null)
    try {
      await setServiceSecret(serviceId, { key: newKey, value: newValue })
      const secs = await fetchServiceSecrets(serviceId)
      setSecrets(secs)
      setNewKey('')
      setNewValue('')
    } catch (err) {
      setSecretError(err instanceof MountainApiError ? err.message : '添加失败')
    } finally {
      setIsAddingSecret(false)
    }
  }

  const handleDeleteSecret = async (key: string) => {
    try {
      await deleteServiceSecret(serviceId, key)
      setSecrets(prev => prev.filter(s => s.key !== key))
    } catch {
      // ignore — will be refreshed on next load
    }
  }

  if (isLoading) {
    return <div className="set-loading">加载中...</div>
  }

  if (error) {
    return (
      <div className="set-error">
        <p>加载服务详情失败</p>
        <p className="set-error__detail">{error.message}</p>
      </div>
    )
  }

  if (!service) {
    return <div className="set-error">服务不存在</div>
  }

  return (
    <div className="mp-detail">
      <header className="mp-detail__header">
        <Link to="/settings" className="btn btn--secondary">
          返回设置
        </Link>
        <h1 className="mp-detail__title">{service.display_name}</h1>
        <span className="mp-detail__id">{service.service_id}</span>
      </header>

      <div className="mp-detail__status">
        <div className="mp-detail__status-item">
          <span className="mp-detail__label">配置状态</span>
          <StatusBadge status={service.config_status} />
        </div>
        <div className="mp-detail__status-item">
          <span className="mp-detail__label">可用性</span>
          <StatusBadge status={service.availability} />
        </div>
        <div className="mp-detail__status-item">
          <span className="mp-detail__label">密钥状态</span>
          <StatusBadge status={service.secret_status} />
        </div>
      </div>

      <div className="mp-detail__info">
        <div className="mp-detail__info-item">
          <span className="mp-detail__label">适配器类型</span>
          <span>{service.adapter_type}</span>
        </div>
        <div className="mp-detail__info-item">
          <span className="mp-detail__label">能力</span>
          <span>{service.capability}</span>
        </div>
        {service.model && (
          <div className="mp-detail__info-item">
            <span className="mp-detail__label">模型</span>
            <span>{service.model}</span>
          </div>
        )}
        {service.endpoint && (
          <div className="mp-detail__info-item">
            <span className="mp-detail__label">端点</span>
            <span>{service.endpoint}</span>
          </div>
        )}
        <div className="mp-detail__info-item">
          <span className="mp-detail__label">优先级</span>
          <span>{service.priority}</span>
        </div>
        <div className="mp-detail__info-item">
          <span className="mp-detail__label">默认服务</span>
          <span>{service.is_default ? '是' : '否'}</span>
        </div>
      </div>

      {service.available_models && service.available_models.length > 0 && (
        <div className="mp-detail__models">
          <h2 className="mp-detail__section-title">可用模型</h2>
          <ul className="mp-detail__model-list">
            {service.available_models.map(model => (
              <li key={model} className="mp-detail__model-item">{model}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="mp-detail__config">
        <h2 className="mp-detail__section-title">配置</h2>
        <textarea
          className="mp-detail__config-editor"
          value={configJson}
          onChange={e => setConfigJson(e.target.value)}
          rows={10}
          aria-label="服务配置 JSON"
        />
        {configError && (
          <div className="mp-detail__config-error" role="alert">
            {configError}
          </div>
        )}
        <button
          type="button"
          className="btn btn--primary"
          onClick={handleConfigSave}
          disabled={isSavingConfig}
        >
          {isSavingConfig ? '保存中...' : '保存配置'}
        </button>
      </div>

      <div className="mp-secrets">
        <h2 className="mp-detail__section-title">密钥管理</h2>

        {secrets.length > 0 && (
          <div className="mp-secrets__list">
            {secrets.map(secret => (
              <div key={secret.key} className="mp-secret-item">
                <span className="mp-secret-item__key">{secret.key}</span>
                <span className="mp-secret-item__status">
                  {secret.configured ? '已配置' : '未配置'}
                </span>
                {secret.masked_value && (
                  <span className="mp-secret-item__value">{secret.masked_value}</span>
                )}
                {secret.configured && (
                  <button
                    type="button"
                    className="btn btn--danger btn--sm"
                    onClick={() => handleDeleteSecret(secret.key)}
                    aria-label={`删除密钥 ${secret.key}`}
                  >
                    删除
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        <form className="mp-secrets__form" onSubmit={handleAddSecret}>
          <div className="mp-secrets__form-row">
            <input
              type="text"
              className="mp-secrets__key-input"
              placeholder="密钥名称"
              value={newKey}
              onChange={e => setNewKey(e.target.value)}
              required
              aria-label="密钥名称"
            />
            <input
              type="password"
              className="mp-secrets__value-input"
              placeholder="密钥值"
              value={newValue}
              onChange={e => setNewValue(e.target.value)}
              required
              aria-label="密钥值"
            />
            <button
              type="submit"
              className="btn btn--primary"
              disabled={isAddingSecret || !newKey.trim() || !newValue}
            >
              {isAddingSecret ? '添加中...' : '添加'}
            </button>
          </div>
          {secretError && (
            <div className="mp-secrets__error" role="alert">
              {secretError}
            </div>
          )}
        </form>
      </div>
    </div>
  )
}
