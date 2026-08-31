/* ==========================================================================
   诊断 — Diagnostics Page
   ========================================================================== */

import { useState, useEffect } from 'react'
import { fetchDiagnosticsSettings } from '../lib/api/settings'
import type { DiagnosticsSettings } from '../lib/api/types'

export function DiagnosticsPage() {
  const [settings, setSettings] = useState<DiagnosticsSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchDiagnosticsSettings()
      setSettings(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  if (loading) return <div className="page-container"><div className="dg-loading">加载中...</div></div>
  if (error) return <div className="page-container"><div className="dg-error">{error}</div></div>
  if (!settings) return <div className="page-container"><div className="dg-empty">未找到配置</div></div>

  return (
    <div className="page-container">
      <div className="dg-header">
        <h1 className="dg-title">诊断</h1>
        <p className="dg-description">系统健康状态</p>
        <button className="btn btn-secondary" onClick={load}>刷新</button>
      </div>

      <div className="dg-grid">
        <div className="dg-item">
          <span className="dg-item-label">API 状态</span>
          <span className={`dg-item-value ${settings.api.status === 'ok' ? 'dg-item-value--ok' : 'dg-item-value--fail'}`}>
            {settings.api.status}
          </span>
        </div>
        <div className="dg-item">
          <span className="dg-item-label">服务</span>
          <span className="dg-item-value">
            总计 {settings.services.total} | 可用 {settings.services.available} | 不可用 {settings.services.unavailable}
          </span>
        </div>
        <div className="dg-item">
          <span className="dg-item-label">工具链</span>
          <span className="dg-item-value">
            总计 {settings.toolchain.total} | 可用 {settings.toolchain.available} | 缺失 {settings.toolchain.missing}
          </span>
        </div>
        <div className="dg-item">
          <span className="dg-item-label">存储</span>
          <span className={`dg-item-value ${settings.storage.writable ? 'dg-item-value--ok' : 'dg-item-value--fail'}`}>
            {settings.storage.writable ? '可写' : '不可写'}
            {settings.storage.free_bytes != null && ` | 可用空间: ${(settings.storage.free_bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`}
          </span>
        </div>
        {settings.telemetry && (
          <div className="dg-item">
            <span className="dg-item-label">遥测</span>
            <span className="dg-item-value">{settings.telemetry.enabled ? '已启用' : '未启用'}</span>
          </div>
        )}
        {settings.logs && (
          <div className="dg-item">
            <span className="dg-item-label">近期错误</span>
            <span className={`dg-item-value ${settings.logs.recent_errors > 0 ? 'dg-item-value--warn' : 'dg-item-value--ok'}`}>
              {settings.logs.recent_errors}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
