/* ===========================================================================
   Runtime storage — health snapshot, presented read-only.
   =========================================================================== */

import { useEffect, useRef, useState } from 'react'
import { fetchStorageSettings } from '../lib/api/settings'
import type { StorageSettings } from '../lib/api/types'

type LogicalStorage = {
  key: 'assets' | 'tasks' | 'temp'
  label: string
  available: boolean
}

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return '未统计'
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  const value = bytes / Math.pow(1024, i)
  return `${value.toFixed(i > 1 ? 1 : 0)} ${units[i]}`
}

function hasValidCapacity(bytes: number | null | undefined): bytes is number {
  return bytes != null && Number.isFinite(bytes) && bytes >= 0
}

function StorageSkeleton() {
  return (
    <div className="ss-grid" aria-label="正在加载存储状态">
      {[0, 1, 2].map(index => (
        <div className="ss-card ss-card--skeleton" key={index} aria-hidden="true">
          <span className="ss-skeleton ss-skeleton--title" />
          <span className="ss-skeleton ss-skeleton--line" />
        </div>
      ))}
    </div>
  )
}

function StorageCard({ storage }: { storage: LogicalStorage }) {
  return (
    <article className="ss-card">
      <div className="ss-card-header">
        <h3 className="ss-card-name">{storage.label}</h3>
        <span className={`ss-status ss-status--${storage.available ? 'available' : 'unavailable'}`}>
          {storage.available ? '可用' : '不可用'}
        </span>
      </div>
      <p className="ss-card-purpose">
        {storage.available ? '逻辑存储已就绪。' : '尚不可用。'}
      </p>
    </article>
  )
}

export function StoragePage() {
  const [settings, setSettings] = useState<StorageSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const mounted = useRef(false)
  const requestId = useRef(0)

  const load = async () => {
    const currentRequest = ++requestId.current
    setLoading(true)
    setError(null)
    try {
      const data = await fetchStorageSettings()
      if (mounted.current && currentRequest === requestId.current) setSettings(data)
    } catch (cause) {
      if (mounted.current && currentRequest === requestId.current) {
        setError(cause instanceof Error ? cause.message : '加载存储状态失败')
      }
    } finally {
      if (mounted.current && currentRequest === requestId.current) setLoading(false)
    }
  }

  useEffect(() => {
    mounted.current = true
    void load()
    return () => {
      mounted.current = false
      requestId.current += 1
    }
  }, [])

  const storages: LogicalStorage[] = [
    { key: 'assets', label: '素材存储', available: settings?.assets_available ?? false },
    { key: 'tasks', label: '任务存储', available: settings?.tasks_available ?? false },
    { key: 'temp', label: '临时存储', available: settings?.temp_available ?? false },
  ]

  const freeValid = hasValidCapacity(settings?.free_bytes)
  const usedValid = hasValidCapacity(settings?.used_bytes)
  const total = freeValid && usedValid ? settings!.free_bytes! + settings!.used_bytes! : 0
  const ratio = freeValid && usedValid && total > 0 ? (settings!.used_bytes! / total) * 100 : null

  return (
    <section className="ss-panel" aria-labelledby="storage-title">
      <h2 className="ss-title" id="storage-title">运行时存储状态</h2>
      <p className="ss-description">
        以下为全局运行时存储健康状态，仅作只读展示；不暴露绝对路径、目录树或文件名，也不暗示具体任务上下文。
      </p>

      {loading && <StorageSkeleton />}
      {!loading && error && (
        <div className="ss-error" role="alert">
          <p>加载存储状态失败：{error}</p>
          <button className="btn btn-secondary" type="button" onClick={() => void load()}>重新加载</button>
        </div>
      )}
      {!loading && !error && settings && (
        <>
          <div className="ss-grid">
            {storages.map(s => <StorageCard key={s.key} storage={s} />)}
          </div>

          <div className="ss-writable-section">
            <article className={`ss-writable-card ss-writable-card--${settings.writable ? 'ok' : 'fail'}`}>
              <div className="ss-writable-header">
                <h3 className="ss-writable-label">整体可写状态</h3>
                <span className={`ss-status ss-status--${settings.writable ? 'available' : 'unavailable'}`}>
                  {settings.writable ? '正常' : '不可用'}
                </span>
              </div>
              {!settings.writable && (settings.error_code || settings.suggestion) && (
                <div className="ss-writable-detail">
                  {settings.error_code && <p className="ss-error-code">{settings.error_code}</p>}
                  {settings.suggestion && <p className="ss-suggestion">{settings.suggestion}</p>}
                </div>
              )}
              {!settings.writable && !settings.error_code && !settings.suggestion && (
                <p className="ss-suggestion">存储不可用，后端未提供详细原因。</p>
              )}
            </article>
          </div>

          <div className="ss-capacity-section">
            <article className="ss-capacity-card">
              <h3 className="ss-capacity-label">存储卷统计</h3>
              {freeValid || usedValid ? (
                <>
                  <div className="ss-capacity-grid">
                    <div className="ss-capacity-item">
                      <span className="ss-capacity-item-label">可用空间</span>
                      <span className="ss-capacity-item-value">{freeValid ? formatBytes(settings!.free_bytes!) : '未统计'}</span>
                    </div>
                    <div className="ss-capacity-item">
                      <span className="ss-capacity-item-label">已用空间</span>
                      <span className="ss-capacity-item-value">{usedValid ? formatBytes(settings!.used_bytes!) : '未统计'}</span>
                    </div>
                    {ratio !== null && (
                      <div className="ss-capacity-item">
                        <span className="ss-capacity-item-label">已用比例</span>
                        <span className="ss-capacity-item-value">{ratio.toFixed(1)}%</span>
                      </div>
                    )}
                  </div>
                  <p className="ss-capacity-note">以上为当前存储卷的总体统计，非 Mountain 独占空间。</p>
                </>
              ) : (
                <p className="ss-capacity-empty">未统计</p>
              )}
            </article>
          </div>

          {settings.cleanup_policy && (
            <div className="ss-policy-section">
              <article className="ss-policy-card">
                <h3 className="ss-policy-label">清理策略</h3>
                <p className="ss-policy-value">{settings.cleanup_policy}</p>
                <p className="ss-policy-note">策略由运行时统一管理，当前不可配置。</p>
              </article>
            </div>
          )}
        </>
      )}
    </section>
  )
}
