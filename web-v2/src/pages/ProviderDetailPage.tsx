import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  fetchProvider,
  updateProviderConfig,
  fetchProviderSecrets,
  setProviderSecret,
  deleteProviderSecret,
} from '../lib/api/client'
import type { ProviderDetail, SecretStatusResponse } from '../lib/api/types'

export function ProviderDetailPage() {
  const { name } = useParams<{ name: string }>()
  const [detail, setDetail] = useState<ProviderDetail | null>(null)
  const [secrets, setSecrets] = useState<SecretStatusResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Config editing state
  const [configDraft, setConfigDraft] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  // Secret editing state
  const [secretInputs, setSecretInputs] = useState<Record<string, string>>({})
  const [secretSaving, setSecretSaving] = useState<Record<string, boolean>>({})

  const load = () => {
    if (!name) return
    Promise.all([fetchProvider(name), fetchProviderSecrets(name)])
      .then(([d, s]) => {
        setDetail(d)
        setSecrets(s)
        // Initialize config draft with current values
        const draft: Record<string, string> = {}
        for (const [k, v] of Object.entries(d.config)) {
          draft[k] = String(v ?? '')
        }
        setConfigDraft(draft)
      })
      .catch((e) => setError(e instanceof Error ? e.message : '加载失败'))
      .finally(() => setLoading(false))
  }

  useEffect(load, [name])

  const handleSaveConfig = async () => {
    if (!name || !detail) return
    setSaving(true)
    setSaveError(null)
    setSaveSuccess(false)

    // Convert string values back to original types
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
      // Reload to get fresh data
      const d = await fetchProvider(name)
      setDetail(d)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleSetSecret = async (key: string) => {
    if (!name) return
    const value = secretInputs[key]
    if (!value) return

    setSecretSaving((s) => ({ ...s, [key]: true }))
    try {
      await setProviderSecret(name, { key, value })
      // Clear input immediately
      setSecretInputs((s) => ({ ...s, [key]: '' }))
      // Reload secrets
      const s = await fetchProviderSecrets(name)
      setSecrets(s)
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : '设置密钥失败')
    } finally {
      setSecretSaving((s) => ({ ...s, [key]: false }))
    }
  }

  const handleDeleteSecret = async (key: string) => {
    if (!name) return
    if (!confirm(`确定删除密钥 ${key}？`)) return

    setSecretSaving((s) => ({ ...s, [key]: true }))
    try {
      await deleteProviderSecret(name, key)
      const s = await fetchProviderSecrets(name)
      setSecrets(s)
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : '删除密钥失败')
    } finally {
      setSecretSaving((s) => ({ ...s, [key]: false }))
    }
  }

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
          ← 返回 Provider 列表
        </Link>
      </div>
    )
  }

  if (!detail) return null

  const allowedKeys = Object.keys(detail.config)
  const availability = detail.availability

  return (
    <div className="page page-narrow">
      <div className="page-head">
        <h1 className="page-title">{detail.profile.name}</h1>
        <p className="page-desc">{detail.profile.description}</p>
      </div>

      {/* Availability status */}
      {!availability.available && (
        <div className="error-card">
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

      {availability.available && (
        <div className="notice notice-ok" style={{ marginBottom: 16 }}>
          Provider 可用，配置正常。
        </div>
      )}

      {/* Config section */}
      <div className="card">
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

      {/* Secrets section */}
      <div className="card">
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
                    <span className={`badge st-succeeded`}>
                      <span className="dot" /> 已配置
                    </span>
                    <span className="secret-mask">{info.masked_value}</span>
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
                    <span className={`badge st-failed`}>
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
      </div>

      {/* Profile info */}
      <div className="card">
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

      <div style={{ marginTop: 16 }}>
        <Link to="/settings/providers" className="btn btn-ghost">
          ← 返回 Provider 列表
        </Link>
      </div>
    </div>
  )
}
