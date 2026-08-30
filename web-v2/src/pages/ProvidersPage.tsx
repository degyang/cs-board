import { Link } from 'react-router-dom'
import { useAsync } from '../lib/api/queries'
import { fetchProviders } from '../lib/api/client'
import { useCallback } from 'react'

// ── Category mapping (derived from real provider_type) ─────────────────

interface CategoryInfo {
  label: string
  icon: string
  cssClass: string
}

const CATEGORY_MAP: Record<string, CategoryInfo> = {
  text_model: { label: '文本', icon: '📝', cssClass: 'cat-text' },
  image_model: { label: '图片', icon: '🖼️', cssClass: 'cat-image' },
  tts: { label: '语音', icon: '🔊', cssClass: 'cat-voice' },
  alignment: { label: '工具链', icon: '🎯', cssClass: 'cat-tool' },
  renderer: { label: '工具链', icon: '🎨', cssClass: 'cat-tool' },
  media: { label: '工具链', icon: '🎬', cssClass: 'cat-tool' },
}

function getCategory(providerType: string): CategoryInfo {
  return CATEGORY_MAP[providerType] ?? { label: '其他', icon: '⚙️', cssClass: 'cat-tool' }
}

// ── Extract model chip from config ─────────────────────────────────────

function extractModelChip(config: Record<string, unknown>): string | null {
  const model = config.model
  if (typeof model === 'string' && model) return model
  return null
}

// ── Extract display URL from config ────────────────────────────────────

function extractUrl(config: Record<string, unknown>): string | null {
  const url = config.base_url ?? config.url
  if (typeof url === 'string' && url) return url
  return null
}

// ── Component ──────────────────────────────────────────────────────────

export function ProvidersPage() {
  const loader = useCallback(() => fetchProviders(), [])
  const { data, loading, error } = useAsync(loader, [])

  return (
    <div className="page">
      <div className="page-head">
        <h1 className="page-title">模型服务</h1>
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
        const cat = getCategory(entry.profile.provider_type)
        const modelChip = extractModelChip(entry.profile.config)
        const displayUrl = extractUrl(entry.profile.config)
        const configured = entry.config_status.configured
        const available = entry.availability.available

        return (
          <div key={name} className="mp-card">
            <div className="mp-card-head">
              <div className="mp-card-icon">{cat.icon}</div>
              <div>
                <div className="mp-card-title">{entry.profile.name}</div>
                <div className="mp-card-desc">{entry.profile.description}</div>
              </div>
            </div>

            <div className="mp-card-body">
              {/* Category badge */}
              <span className={`mp-category-badge ${cat.cssClass}`}>
                {cat.label}
              </span>

              {/* Model chip */}
              {modelChip && (
                <span className="mp-model-chip">{modelChip}</span>
              )}

              {/* URL */}
              {displayUrl && (
                <span className="mp-url">{displayUrl}</span>
              )}

              {/* Configured status */}
              <span className={`badge ${configured ? 'st-succeeded' : 'st-failed'}`}>
                <span className="dot" />
                {configured ? '已配置' : '未配置'}
              </span>

              {/* Availability */}
              <span className={`badge ${available ? 'st-succeeded' : 'st-failed'}`}>
                <span className="dot" />
                {available ? '可用' : '不可用'}
              </span>

              {/* Missing secrets */}
              {entry.config_status.missing_secrets.length > 0 && (
                <span className="badge st-running">
                  缺少: {entry.config_status.missing_secrets.join(', ')}
                </span>
              )}

              {/* Error info when unavailable */}
              {!available && entry.availability.error_code && (
                <span style={{ fontSize: 12, color: 'var(--nt-danger)' }}>
                  {entry.availability.error_code}
                </span>
              )}
            </div>

            {/* Suggestion when unavailable */}
            {!available && entry.availability.suggestion && (
              <div style={{ fontSize: 12, color: 'var(--nt-text-muted)', marginBottom: 8 }}>
                💡 {entry.availability.suggestion}
              </div>
            )}

            <div className="mp-card-actions">
              <Link to={`/settings/providers/${name}`} className="btn btn-ghost btn-sm">
                配置 →
              </Link>
            </div>
          </div>
        )
      })}

      {/* CRUD gap notice */}
      <div className="mp-info">
        当前版本由后端管理 Provider Profile；新增/删除服务商将在 Provider Registry API 发布后开放。
      </div>
    </div>
  )
}
