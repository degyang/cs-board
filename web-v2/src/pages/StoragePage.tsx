/* ==========================================================================
   存储 — Storage Page
   ========================================================================== */

import { useState, useEffect } from 'react'
import { fetchStorageSettings } from '../lib/api/settings'
import type { StorageSettings } from '../lib/api/types'

export function StoragePage() {
  const [settings, setSettings] = useState<StorageSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchStorageSettings()
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

  const formatBytes = (bytes: number | null) => {
    if (bytes == null) return '—'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
  }

  if (loading) return <div className="page-container"><div className="st-loading">加载中...</div></div>
  if (error) return <div className="page-container"><div className="st-error">{error}</div></div>
  if (!settings) return <div className="page-container"><div className="st-empty">未找到配置</div></div>

  return (
    <div className="page-container">
      <div className="st-header">
        <h1 className="st-title">存储</h1>
        <p className="st-description">存储系统状态</p>
      </div>

      <div className="st-grid">
        <div className="st-item">
          <span className="st-item-label">可写</span>
          <span className={`st-item-value ${settings.writable ? 'st-item-value--ok' : 'st-item-value--fail'}`}>
            {settings.writable ? '是' : '否'}
          </span>
        </div>
        <div className="st-item">
          <span className="st-item-label">素材存储</span>
          <span className={`st-item-value ${settings.assets_available ? 'st-item-value--ok' : 'st-item-value--fail'}`}>
            {settings.assets_available ? '可用' : '不可用'}
          </span>
        </div>
        <div className="st-item">
          <span className="st-item-label">任务存储</span>
          <span className={`st-item-value ${settings.tasks_available ? 'st-item-value--ok' : 'st-item-value--fail'}`}>
            {settings.tasks_available ? '可用' : '不可用'}
          </span>
        </div>
        <div className="st-item">
          <span className="st-item-label">临时存储</span>
          <span className={`st-item-value ${settings.temp_available ? 'st-item-value--ok' : 'st-item-value--fail'}`}>
            {settings.temp_available ? '可用' : '不可用'}
          </span>
        </div>
        {settings.free_bytes != null && (
          <div className="st-item">
            <span className="st-item-label">可用空间</span>
            <span className="st-item-value">{formatBytes(settings.free_bytes)}</span>
          </div>
        )}
        {settings.used_bytes != null && (
          <div className="st-item">
            <span className="st-item-label">已用空间</span>
            <span className="st-item-value">{formatBytes(settings.used_bytes)}</span>
          </div>
        )}
        {settings.cleanup_policy && (
          <div className="st-item">
            <span className="st-item-label">清理策略</span>
            <span className="st-item-value">{settings.cleanup_policy}</span>
          </div>
        )}
      </div>
    </div>
  )
}
