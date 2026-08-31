/* ==========================================================================
   Settings Page — Dynamic service management with tabs.
   ========================================================================== */

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Tabs } from '../components/ui/Tabs'
import { StatusBadge } from '../components/ui/StatusBadge'
import { MountainApiError } from '../lib/api/http'
import {
  fetchServices,
  toggleService,
  setDefaultService,
} from '../lib/api/services'
import {
  fetchVoiceAlignment,
  fetchToolchain,
  fetchStorage,
  fetchDiagnostics,
} from '../lib/api/settings'
import type {
  ServiceEntry,
  ServiceCapability,
  VoiceAlignmentSettings,
  ToolchainSettings,
  StorageSettings,
  DiagnosticsSettings,
} from '../lib/api/types'

const SETTINGS_TABS = [
  { key: 'models', label: '模型服务' },
  { key: 'voice-alignment', label: '声音对齐' },
  { key: 'toolchain', label: '工具链' },
  { key: 'storage', label: '存储' },
  { key: 'diagnostics', label: '诊断' },
]

const CAPABILITY_LABELS: Record<ServiceCapability, string> = {
  text_generation: '文本生成',
  image_generation: '图像生成',
  voice_generation: '声音生成',
  video_generation: '视频生成',
  music_generation: '音乐生成',
  file_storage: '文件存储',
  object_storage: '对象存储',
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('models')

  return (
    <div className="set-page">
      <header className="set-page__header">
        <h1 className="set-page__title">设置</h1>
        <p className="set-page__subtitle">管理系统服务和配置</p>
      </header>

      <Tabs
        items={SETTINGS_TABS}
        active={activeTab}
        onChange={setActiveTab}
      />

      <div className="set-page__content">
        {activeTab === 'models' && <ModelsTab />}
        {activeTab === 'voice-alignment' && <VoiceAlignmentTab />}
        {activeTab === 'toolchain' && <ToolchainTab />}
        {activeTab === 'storage' && <StorageTab />}
        {activeTab === 'diagnostics' && <DiagnosticsTab />}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Models Tab (dynamic service list)
// ---------------------------------------------------------------------------

function ModelsTab() {
  const [services, setServices] = useState<ServiceEntry[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MountainApiError | null>(null)

  const loadServices = () => {
    setIsLoading(true)
    fetchServices()
      .then(data => setServices(data.items))
      .catch(err => {
        if (err instanceof MountainApiError) setError(err)
      })
      .finally(() => setIsLoading(false))
  }

  useEffect(() => {
    loadServices()
  }, [])

  const handleToggle = async (serviceId: string, enabled: boolean) => {
    try {
      await toggleService(serviceId, enabled)
      setServices(prev =>
        prev.map(s => s.service_id === serviceId ? { ...s, enabled } : s)
      )
    } catch {
      // ignore — will be refreshed on next load
    }
  }

  const handleSetDefault = async (serviceId: string) => {
    try {
      await setDefaultService(serviceId)
      setServices(prev =>
        prev.map(s => ({
          ...s,
          is_default: s.service_id === serviceId,
        }))
      )
    } catch {
      // ignore — will be refreshed on next load
    }
  }

  // Group services by capability
  const grouped = services.reduce<Record<string, ServiceEntry[]>>((acc, svc) => {
    const cap = svc.capability
    if (!acc[cap]) acc[cap] = []
    acc[cap].push(svc)
    return acc
  }, {})

  if (isLoading) {
    return <div className="set-loading">加载中...</div>
  }

  if (error) {
    return (
      <div className="set-error">
        <p>加载服务列表失败</p>
        <p className="set-error__detail">{error.message}</p>
      </div>
    )
  }

  return (
    <div className="mp-models">
      <div className="mp-models__header">
        <h2 className="mp-models__title">模型服务</h2>
        <p className="mp-models__desc">
          管理系统使用的模型服务，包括文本生成、图像生成等
        </p>
      </div>

      {Object.entries(grouped).map(([capability, svcList]) => (
        <section key={capability} className="mp-capability-group">
          <h3 className="mp-capability-group__title">
            {CAPABILITY_LABELS[capability as ServiceCapability] ?? capability}
          </h3>
          <div className="mp-service-list">
            {svcList.map(svc => (
              <ServiceCard
                key={svc.service_id}
                service={svc}
                onToggle={(enabled) => handleToggle(svc.service_id, enabled)}
                onSetDefault={() => handleSetDefault(svc.service_id)}
              />
            ))}
          </div>
        </section>
      ))}

      {services.length === 0 && (
        <div className="set-empty">暂无可用服务</div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Service Card
// ---------------------------------------------------------------------------

interface ServiceCardProps {
  service: ServiceEntry
  onToggle: (enabled: boolean) => void
  onSetDefault: () => void
}

function ServiceCard({ service, onToggle, onSetDefault }: ServiceCardProps) {
  return (
    <article className="mp-service-card">
      <div className="mp-service-card__header">
        <div className="mp-service-card__info">
          <h4 className="mp-service-card__name">{service.display_name}</h4>
          <span className="mp-service-card__id">{service.service_id}</span>
        </div>
        <div className="mp-service-card__status">
          <StatusBadge status={service.config_status} />
          <StatusBadge status={service.availability} />
        </div>
      </div>

      <div className="mp-service-card__body">
        <div className="mp-service-card__meta">
          <span className="mp-service-card__adapter">
            {service.adapter_type}
          </span>
          {service.model && (
            <span className="mp-service-card__model">{service.model}</span>
          )}
          {service.endpoint && (
            <span className="mp-service-card__endpoint">{service.endpoint}</span>
          )}
        </div>

        <div className="mp-service-card__actions">
          <label className="mp-service-card__toggle">
            <input
              type="checkbox"
              checked={service.enabled}
              onChange={e => onToggle(e.target.checked)}
              aria-label={`启用 ${service.display_name}`}
            />
            <span>启用</span>
          </label>

          {!service.is_default && (
            <button
              type="button"
              className="btn btn--secondary btn--sm"
              onClick={onSetDefault}
              aria-label={`设为默认 ${service.display_name}`}
            >
              设为默认
            </button>
          )}

          {service.is_default && (
            <span className="mp-service-card__default-badge">默认</span>
          )}

          <Link
            to={`/settings/models/${service.service_id}`}
            className="btn btn--secondary btn--sm"
          >
            详情
          </Link>
        </div>
      </div>
    </article>
  )
}

// ---------------------------------------------------------------------------
// Voice Alignment Tab
// ---------------------------------------------------------------------------

function VoiceAlignmentTab() {
  const [data, setData] = useState<VoiceAlignmentSettings | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MountainApiError | null>(null)

  useEffect(() => {
    fetchVoiceAlignment()
      .then(setData)
      .catch(err => {
        if (err instanceof MountainApiError) setError(err)
      })
      .finally(() => setIsLoading(false))
  }, [])

  if (isLoading) {
    return <div className="set-loading">加载中...</div>
  }

  if (error) {
    return (
      <div className="set-error">
        <p>加载声音对齐状态失败</p>
        <p className="set-error__detail">{error.message}</p>
      </div>
    )
  }

  if (!data) {
    return <div className="set-empty">无法获取声音对齐状态</div>
  }

  return (
    <div className="va-page">
      <h2 className="va-page__title">声音对齐</h2>
      <div className="va-status">
        <div className="va-status__item">
          <span className="va-status__label">状态</span>
          <StatusBadge status={data.status} />
        </div>
        <div className="va-status__item">
          <span className="va-status__label">可用性</span>
          <span>{data.available ? '可用' : '不可用'}</span>
        </div>
      </div>
      {data.config && (
        <pre className="va-config">
          {JSON.stringify(data.config, null, 2)}
        </pre>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Toolchain Tab
// ---------------------------------------------------------------------------

function ToolchainTab() {
  const [data, setData] = useState<ToolchainSettings | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MountainApiError | null>(null)

  useEffect(() => {
    fetchToolchain()
      .then(setData)
      .catch(err => {
        if (err instanceof MountainApiError) setError(err)
      })
      .finally(() => setIsLoading(false))
  }, [])

  if (isLoading) {
    return <div className="set-loading">加载中...</div>
  }

  if (error) {
    return (
      <div className="set-error">
        <p>加载工具链状态失败</p>
        <p className="set-error__detail">{error.message}</p>
      </div>
    )
  }

  if (!data) {
    return <div className="set-empty">无法获取工具链状态</div>
  }

  return (
    <div className="tc-page">
      <h2 className="tc-page__title">工具链</h2>
      <div className="tc-tools">
        {data.tools.map(tool => (
          <div key={tool.name} className="tc-tool">
            <div className="tc-tool__header">
              <h3 className="tc-tool__name">{tool.name}</h3>
              <StatusBadge status={tool.status} />
            </div>
            <div className="tc-tool__meta">
              {tool.version && (
                <span className="tc-tool__version">当前版本: {tool.version}</span>
              )}
              {tool.required_version && (
                <span className="tc-tool__required">
                  要求版本: {tool.required_version}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
      {data.tools.length === 0 && (
        <div className="set-empty">暂无工具链信息</div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Storage Tab
// ---------------------------------------------------------------------------

function StorageTab() {
  const [data, setData] = useState<StorageSettings | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MountainApiError | null>(null)

  useEffect(() => {
    fetchStorage()
      .then(setData)
      .catch(err => {
        if (err instanceof MountainApiError) setError(err)
      })
      .finally(() => setIsLoading(false))
  }, [])

  if (isLoading) {
    return <div className="set-loading">加载中...</div>
  }

  if (error) {
    return (
      <div className="set-error">
        <p>加载存储状态失败</p>
        <p className="set-error__detail">{error.message}</p>
      </div>
    )
  }

  if (!data) {
    return <div className="set-empty">无法获取存储状态</div>
  }

  const usagePercent = data.usage
    ? Math.round((data.usage.used_bytes / data.usage.total_bytes) * 100)
    : null

  return (
    <div className="st-page">
      <h2 className="st-page__title">存储</h2>
      <div className="st-info">
        <div className="st-info__item">
          <span className="st-info__label">后端</span>
          <span className="st-info__value">{data.backend}</span>
        </div>
        {usagePercent !== null && data.usage && (
          <div className="st-info__item">
            <span className="st-info__label">使用量</span>
            <div className="st-info__usage">
              <div className="st-info__bar">
                <div
                  className="st-info__bar-fill"
                  style={{ width: `${usagePercent}%` }}
                />
              </div>
              <span className="st-info__percent">{usagePercent}%</span>
            </div>
          </div>
        )}
      </div>
      {Object.keys(data.config).length > 0 && (
        <pre className="st-config">
          {JSON.stringify(data.config, null, 2)}
        </pre>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Diagnostics Tab
// ---------------------------------------------------------------------------

function DiagnosticsTab() {
  const [data, setData] = useState<DiagnosticsSettings | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<MountainApiError | null>(null)

  useEffect(() => {
    fetchDiagnostics()
      .then(setData)
      .catch(err => {
        if (err instanceof MountainApiError) setError(err)
      })
      .finally(() => setIsLoading(false))
  }, [])

  if (isLoading) {
    return <div className="set-loading">加载中...</div>
  }

  if (error) {
    return (
      <div className="set-error">
        <p>加载诊断状态失败</p>
        <p className="set-error__detail">{error.message}</p>
      </div>
    )
  }

  if (!data) {
    return <div className="set-empty">无法获取诊断状态</div>
  }

  return (
    <div className="dg-page">
      <h2 className="dg-page__title">诊断</h2>
      <div className="dg-checks">
        {data.checks.map(check => (
          <div key={check.name} className="dg-check">
            <div className="dg-check__header">
              <h3 className="dg-check__name">{check.name}</h3>
              <StatusBadge status={check.status} />
            </div>
            {check.message && (
              <p className="dg-check__message">{check.message}</p>
            )}
          </div>
        ))}
      </div>
      {data.checks.length === 0 && (
        <div className="set-empty">暂无诊断信息</div>
      )}
    </div>
  )
}
