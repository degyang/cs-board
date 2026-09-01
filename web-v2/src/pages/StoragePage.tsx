/* ===========================================================================
   Runtime storage — health snapshot, presented read-only.
   对齐原型 TaskStorageStatusTab: card → ss-storage-list → ss-storage-row
   =========================================================================== */

import { useEffect, useRef, useState } from 'react'
import { fetchStorageSettings } from '../lib/api/settings'
import type { StorageSettings } from '../lib/api/types'
import { hasValidCapacity, formatCapacityBytes } from '../lib/formatting'

type LogicalStorage = {
  key: 'assets' | 'tasks' | 'temp'
  label: string
  available: boolean
}

function StorageCard({ storage }: { storage: LogicalStorage }) {
  return (
    <div className="ss-card">
      <div className="ss-card-head">
        <h3 className="ss-card-name">{storage.label}</h3>
        <span className={`badge st-${storage.available ? 'succeeded' : 'failed'}`}>
          {storage.available ? '可用' : '不可用'}
        </span>
      </div>
      <p className="ss-card-purpose">
        {storage.available ? '逻辑存储已就绪。' : '尚不可用。'}
      </p>
    </div>
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
    <div className="ss-section">
      <div className="card">
        <h2 className="card-title">运行时存储状态</h2>
        <p className="card-sub">
          以下为全局运行时存储健康状态，仅作只读展示；不暴露绝对路径、目录树或文件名，也不暗示具体任务上下文。
        </p>

        <div className="ss-hint">
          存储策略由本地运行时统一管理；配额、保留和清理配置将在具备真实后端 API 与安全确认后开放。
        </div>

        {loading && (
          <div className="ss-grid" aria-label="正在加载存储状态">
            {[0, 1, 2].map(index => (
              <div className="ss-card ss-card--skeleton" key={index} aria-hidden="true">
                <span className="ss-skeleton ss-skeleton--title" />
                <span className="ss-skeleton ss-skeleton--line" />
              </div>
            ))}
          </div>
        )}

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

            <div className="ss-grid" style={{ marginTop: 16 }}>
              <div className="ss-card">
                <div className="ss-card-head">
                  <h3 className="ss-card-name">整体可写状态</h3>
                  <span className={`badge st-${settings.writable ? 'succeeded' : 'failed'}`}>
                    {settings.writable ? '正常' : '不可用'}
                  </span>
                </div>
                {!settings.writable && (settings.error_code || settings.suggestion) && (
                  <div className="ss-error">
                    <div className="ss-error-head">
                      {settings.error_code && <span className="ss-error-code mono">{settings.error_code}</span>}
                    </div>
                    {settings.suggestion && <p className="ss-error-suggestion">{settings.suggestion}</p>}
                  </div>
                )}
                {!settings.writable && !settings.error_code && !settings.suggestion && (
                  <p className="ss-error-suggestion">存储不可用，后端未提供详细原因。</p>
                )}
              </div>

              <div className="ss-card">
                <div className="ss-card-head">
                  <h3 className="ss-card-name">存储卷统计</h3>
                </div>
                {freeValid || usedValid ? (
                  <>
                    <div className="settings-row">
                      <span className="k">可用空间</span>
                      <span className="v">{freeValid ? formatCapacityBytes(settings!.free_bytes!) : '未统计'}</span>
                    </div>
                    <div className="settings-row">
                      <span className="k">已用空间</span>
                      <span className="v">{usedValid ? formatCapacityBytes(settings!.used_bytes!) : '未统计'}</span>
                    </div>
                    {ratio !== null && (
                      <div className="settings-row">
                        <span className="k">已用比例</span>
                        <span className="v">{ratio.toFixed(1)}%</span>
                      </div>
                    )}
                    <div className="ss-card-meta" style={{ fontSize: 11, marginTop: 4 }}>
                      以上为当前存储卷的总体统计，非 Mountain 独占空间。
                    </div>
                  </>
                ) : (
                  <div className="ss-card-meta">未统计</div>
                )}
              </div>
            </div>

            {settings.cleanup_policy && (
              <div className="settings-row" style={{ marginTop: 12 }}>
                <span className="k">清理策略</span>
                <span className="v">{settings.cleanup_policy}</span>
                <span className="note">策略由运行时统一管理，当前不可配置。</span>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
