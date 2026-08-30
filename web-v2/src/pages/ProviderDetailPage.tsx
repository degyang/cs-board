import { useState, useCallback, useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAsync } from '../lib/api/queries'
import {
  fetchProvider,
  updateProviderConfig,
  fetchProviderSecrets,
  setProviderSecret,
  deleteProviderSecret,
} from '../lib/api/client'

// ── Category mapping ───────────────────────────────────────────────────

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

function extractModelChip(config: Record<string, unknown>): string | null {
  const model = config.model
  if (typeof model === 'string' && model) return model
  return null
}

// ── Component ──────────────────────────────────────────────────────────

export function ProviderDetailPage() {
  const { name } = useParams<{ name: string }>()

  // ── Data loading ───────────────────────────────────────────────────
  const detailLoader = useCallback(() => fetchProvider(name!), [name])
  const secretsLoader = useCallback(() => fetchProviderSecrets(name!), [name])
  const { data: detail, loading, error, refetch } = useAsync(detailLoader, [name])
  const { data: secrets, refetch: refetchSecrets } = useAsync(secretsLoader, [name])

  // ── Config editing state ───────────────────────────────────────────
  const [configDraft, setConfigDraft] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  // ── Secret editing state ───────────────────────────────────────────
  const [secretInputs, setSecretInputs] = useState<Record<string, string>>({})
  const [secretSaving, setSecretSaving] = useState<Record<string, boolean>>({})
  const [secretError, setSecretError] = useState<string | null>(null)

  // Initialize config draft when a detail response arrives that matches the
  // current route param.  Guard: detail.name !== name prevents a stale
  // response (e.g. from a previous route) from overwriting the draft for the
  // new provider.  Refetch within the same provider does NOT re-initialise
  // because the guard still passes — only a route change resets the draft.
  useEffect(() => {
    if (!detail || detail.name !== name) return
    const draft: Record<string, string> = {}
    for (const [k, v] of Object.entries(detail.config)) {
      draft[k] = String(v ?? '')
    }
    setConfigDraft(draft)
    setSaveError(null)
    setSaveSuccess(false)
    setSecretInputs({})
    setSecretError(null)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name, detail?.name])

  // ── Config save ────────────────────────────────────────────────────
  const handleSaveConfig = async () => {
    if (!name || !detail) return
    setSaving(true)
    setSaveError(null)
    setSaveSuccess(false)

    const config: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(configDraft)) {
      const orig = detail.config[k]
      if (typeof orig === 'number') {
        config[k] = Number(v)
      } else if (typeof orig === 'boolean') {
        config[k] = v === 'true'
      } else {
        config[k] = v
      }
    }

    try {
      await updateProviderConfig(name, config)
      setSaveSuccess(true)
      refetch()
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  // ── Secret set ─────────────────────────────────────────────────────
  const handleSetSecret = async (key: string) => {
    if (!name) return
    const value = secretInputs[key]
    if (!value) return

    setSecretSaving((s) => ({ ...s, [key]: true }))
    setSecretError(null)
    try {
      await setProviderSecret(name, { key, value })
      setSecretInputs((s) => ({ ...s, [key]: '' }))
      refetchSecrets()
    } catch (e) {
      setSecretError(e instanceof Error ? e.message : '设置密钥失败')
    } finally {
      setSecretSaving((s) => ({ ...s, [key]: false }))
    }
  }

  // ── Secret delete ──────────────────────────────────────────────────
  const handleDeleteSecret = async (key: string) => {
    if (!name) return
    if (!confirm(`确定删除密钥 ${key}？`)) return

    setSecretSaving((s) => ({ ...s, [key]: true }))
    setSecretError(null)
    try {
      await deleteProviderSecret(name, key)
      refetchSecrets()
    } catch (e) {
      setSecretError(e instanceof Error ? e.message : '删除密钥失败')
    } finally {
      setSecretSaving((s) => ({ ...s, [key]: false }))
    }
  }

  // ── Loading / Error states ─────────────────────────────────────────
  if (loading) {
    return (
      <div className="page">
        <div className="loading">
          <span className="spinner" />
          加载中…
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="page">
        <div className="error-card">
          <div className="code">加载失败</div>
          <div className="sug">{error}</div>
        </div>
        <Link to="/settings/providers" className="btn btn-ghost" style={{ marginTop: 12 }}>
          ← 返回模型服务
        </Link>
      </div>
    )
  }

  if (!detail) return null

  // ── Derived state ──────────────────────────────────────────────────
  const cat = getCategory(detail.profile.provider_type)
  const modelChip = extractModelChip(detail.config)
  const allowedKeys = Object.keys(detail.config)
  const availability = detail.availability

  return (
    <div className="page page-narrow">
      {/* ── Header ───────────────────────────────────────────────────── */}
      <div className="page-head">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <div className="mp-card-icon">{cat.icon}</div>
          <div>
            <h1 className="page-title">{detail.profile.name}</h1>
            <p className="page-desc">{detail.profile.description}</p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
          <span className={`mp-category-badge ${cat.cssClass}`}>{cat.label}</span>
          {modelChip && <span className="mp-model-chip">{modelChip}</span>}
          <span className={`badge ${availability.available ? 'st-succeeded' : 'st-failed'}`}>
            <span className="dot" />
            {availability.available ? '可用' : '不可用'}
          </span>
        </div>
      </div>

      {/* ── Availability error ───────────────────────────────────────── */}
      {!availability.available && (
        <div className="error-card" style={{ marginBottom: 16 }}>
          <div className="code">Provider 不可用</div>
          {availability.error_code && (
            <div style={{ marginTop: 4 }}>
              错误码: <code>{availability.error_code}</code>
            </div>
          )}
          {availability.suggestion && (
            <div className="sug">建议: {availability.suggestion}</div>
          )}
        </div>
      )}

      {/* ── Config section ───────────────────────────────────────────── */}
      <div className="mp-card">
        <div className="card-title">配置</div>
        <div className="card-sub">
          非敏感配置项。允许的字段: {allowedKeys.length > 0 ? allowedKeys.join(', ') : '无'}
        </div>

        {allowedKeys.length === 0 && (
          <p style={{ color: 'var(--nt-text-muted)', fontSize: 13 }}>
            此 Provider 没有可配置的非敏感字段。
          </p>
        )}

        {allowedKeys.map((key) => (
          <div key={key} className="settings-row">
            <span className="k">{key}</span>
            <span className="v">
              <input
                className="input"
                style={{ maxWidth: 400 }}
                value={configDraft[key] ?? ''}
                onChange={(e) => setConfigDraft((d) => ({ ...d, [key]: e.target.value }))}
                disabled={saving}
              />
            </span>
          </div>
        ))}

        {allowedKeys.length > 0 && (
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginTop: 16 }}>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={handleSaveConfig}
              disabled={saving}
            >
              {saving ? '保存中…' : '保存配置'}
            </button>
            {saveSuccess && (
              <span style={{ fontSize: 13, color: 'var(--nt-success)' }}>✓ 已保存</span>
            )}
          </div>
        )}

        {saveError && (
          <div className="error-card" style={{ marginTop: 12 }}>
            <div className="sug">{saveError}</div>
          </div>
        )}
      </div>

      {/* ── Secrets section ──────────────────────────────────────────── */}
      <div className="mp-card">
        <div className="card-title">密钥管理</div>
        <div className="card-sub">
          敏感密钥（API Key 等）通过此区域设置。密钥值提交后立即清空，绝不回显明文。
        </div>

        {secrets && Object.entries(secrets.secrets).map(([key, info]) => (
          <div key={key} className="settings-row">
            <span className="k">{key}</span>
            <span className="v">
              <div className="secret-row">
                {info.configured ? (
                  <>
                    <span className="badge st-succeeded">
                      <span className="dot" /> 已配置
                    </span>
                    {info.masked_value && (
                      <span className="mp-secret-mask">{info.masked_value}</span>
                    )}
                    <button
                      type="button"
                      className="btn btn-danger btn-sm"
                      onClick={() => handleDeleteSecret(key)}
                      disabled={secretSaving[key]}
                    >
                      删除
                    </button>
                  </>
                ) : (
                  <>
                    <span className="badge st-failed">
                      <span className="dot" /> 未配置
                    </span>
                    <input
                      className="input secret-input"
                      type="password"
                      placeholder={`输入 ${key}`}
                      value={secretInputs[key] ?? ''}
                      onChange={(e) => setSecretInputs((s) => ({ ...s, [key]: e.target.value }))}
                      disabled={secretSaving[key]}
                    />
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={() => handleSetSecret(key)}
                      disabled={secretSaving[key] || !secretInputs[key]}
                    >
                      {secretSaving[key] ? '设置中…' : '设置'}
                    </button>
                  </>
                )}
              </div>
            </span>
          </div>
        ))}

        {secrets && Object.keys(secrets.secrets).length === 0 && (
          <p style={{ color: 'var(--nt-text-muted)', fontSize: 13 }}>
            此 Provider 没有需要配置的密钥。
          </p>
        )}

        {secretError && (
          <div className="error-card" style={{ marginTop: 12 }}>
            <div className="sug">{secretError}</div>
          </div>
        )}
      </div>

      {/* ── Profile info ─────────────────────────────────────────────── */}
      <div className="mp-card">
        <div className="card-title">Profile 信息</div>
        <div className="settings-row">
          <span className="k">Provider 类型</span>
          <span className="v mono">{detail.profile.provider_type}</span>
        </div>
        <div className="settings-row">
          <span className="k">必需密钥</span>
          <span className="v">
            {detail.profile.required_secrets.length > 0
              ? detail.profile.required_secrets.join(', ')
              : '无'}
          </span>
        </div>
        <div className="settings-row">
          <span className="k">可选密钥</span>
          <span className="v">
            {detail.profile.optional_secrets.length > 0
              ? detail.profile.optional_secrets.join(', ')
              : '无'}
          </span>
        </div>
        <div className="settings-row">
          <span className="k">加密存储</span>
          <span className="v">{detail.config_status.is_encrypted ? '是' : '否'}</span>
        </div>
      </div>

      {/* ── Back link ────────────────────────────────────────────────── */}
      <div style={{ marginTop: 16 }}>
        <Link to="/settings/providers" className="btn btn-ghost">
          ← 返回模型服务
        </Link>
      </div>
    </div>
  )
}
