import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProviders } from '../lib/api/client'
import type { ProviderListResponse } from '../lib/api/types'

const PROVIDER_ICONS: Record<string, string> = {
  text_model: '📝',
  image_model: '🖼️',
  tts: '🔊',
  alignment: '🎯',
  renderer: '🎨',
  media: '🎬',
}

export function ProvidersPage() {
  const [data, setData] = useState<ProviderListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchProviders()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : '加载失败'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="page">
      <div className="page-head">
        <h1 className="page-title">Provider 配置</h1>
        <p className="page-desc">
          管理 AI 服务 Provider 的配置与密钥。配置完成后即可启动视频制作流程。
        </p>
      </div>

      {loading && (
        <div className="loading">
          <span className="spinner" />
          加载中…
        </div>
      )}

      {error && (
        <div className="error-card">
          <div className="code">加载失败</div>
          <div className="sug">{error}</div>
        </div>
      )}

      {data && !data.all_available && (
        <div className="notice notice-warn" style={{ marginBottom: 16 }}>
          部分 Provider 服务不可用，请检查配置。
          {!data.all_configured && ' 有未配置的必需密钥。'}
        </div>
      )}

      {data && data.all_available && data.all_configured && (
        <div className="notice notice-ok" style={{ marginBottom: 16 }}>
          所有 Provider 已就绪，可以启动视频制作流程。
        </div>
      )}

      {!loading && data && Object.entries(data.providers).map(([name, entry]) => {
        const icon = PROVIDER_ICONS[name] ?? '⚙️'
        const configured = entry.config_status.configured
        const available = entry.availability.available

        return (
          <Link
            key={name}
            to={`/settings/providers/${name}`}
            className="provider-card"
          >
            <div className="provider-icon">{icon}</div>
            <div className="provider-info">
              <div className="provider-name">{entry.profile.name}</div>
              <div className="provider-desc">{entry.profile.description}</div>
              <div className="provider-status">
                <span className={`badge ${configured ? 'st-succeeded' : 'st-failed'}`}>
                  <span className="dot" />
                  {configured ? '已配置' : '未配置'}
                </span>
                <span className={`badge ${available ? 'st-succeeded' : 'st-failed'}`}>
                  <span className="dot" />
                  {available ? '可用' : '不可用'}
                </span>
                {entry.config_status.missing_secrets.length > 0 && (
                  <span className="badge st-running">
                    缺少: {entry.config_status.missing_secrets.join(', ')}
                  </span>
                )}
              </div>
            </div>
            <span className="btn btn-ghost btn-sm">配置 →</span>
          </Link>
        )
      })}
    </div>
  )
}
