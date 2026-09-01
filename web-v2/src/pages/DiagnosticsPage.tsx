/* ==========================================================================
   系统诊断 — read-only system-level summary
   对齐原型 SystemDiagnosticsTab: card → ss-grid → ss-card
   ========================================================================== */

import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchDiagnosticsSettings } from '../lib/api/settings'
import type { DiagnosticsSettings } from '../lib/api/types'
import { hasValidCapacity, formatCapacityBytes } from '../lib/formatting'

function mapApiStatus(raw: string): { label: string; kind: string } {
  const lower = raw.toLowerCase()
  if (lower === 'healthy' || lower === 'ok') return { label: '正常', kind: 'succeeded' }
  if (lower === 'degraded') return { label: '降级', kind: 'running' }
  if (lower === 'failed' || lower === 'down' || lower === 'unavailable') return { label: '不可用', kind: 'failed' }
  return { label: raw, kind: 'pending' }
}

function DiagnosticsSkeleton() {
  return (
    <div className="ss-grid" aria-label="正在加载诊断信息">
      {[0, 1, 2, 3, 4, 5].map(i => (
        <div className="ss-card" key={i} aria-hidden="true">
          <span className="ss-skeleton ss-skeleton--title" />
          <span className="ss-skeleton ss-skeleton--line" />
        </div>
      ))}
    </div>
  )
}

export function DiagnosticsPage() {
  const [settings, setSettings] = useState<DiagnosticsSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const mounted = useRef(false)
  const requestId = useRef(0)

  const load = async () => {
    const currentRequest = ++requestId.current
    setLoading(true)
    setError(null)
    try {
      const data = await fetchDiagnosticsSettings()
      if (mounted.current && currentRequest === requestId.current) setSettings(data)
    } catch (cause) {
      if (mounted.current && currentRequest === requestId.current) {
        setError(cause instanceof Error ? cause.message : '加载诊断信息失败')
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

  const apiStatus = settings ? mapApiStatus(settings.api.status) : null
  const freeValid = hasValidCapacity(settings?.storage.free_bytes)
  const usedValid = hasValidCapacity(settings?.storage.used_bytes)

  return (
    <div className="ss-section">
      <div className="card">
        <h2 className="card-title">系统诊断</h2>
        <p className="card-sub">
          以下为当前运行环境的系统级摘要，仅作只读展示。
          具体任务的事件、日志、Trace 和产物诊断请进入任务工作台查看。
        </p>

        {loading && <DiagnosticsSkeleton />}
        {!loading && error && (
          <div className="ss-error" role="alert">
            <p>加载诊断信息失败：{error}</p>
            <button className="btn btn-secondary" type="button" onClick={() => void load()}>重新加载</button>
          </div>
        )}
        {!loading && !error && settings && (
          <>
            <div className="ss-grid">
              <article className="ss-card">
                <div className="ss-card-head">
                  <h3 className="ss-card-name">API</h3>
                  <span className={`badge st-${apiStatus!.kind}`}>{apiStatus!.label}</span>
                </div>
              </article>

              <article className="ss-card">
                <div className="ss-card-head">
                  <h3 className="ss-card-name">动态服务</h3>
                </div>
                <p className="ss-card-meta">
                  总计 {settings.services.total} · 可用 {settings.services.available} · 不可用 {settings.services.unavailable}
                </p>
              </article>

              <article className="ss-card">
                <div className="ss-card-head">
                  <h3 className="ss-card-name">工具链</h3>
                </div>
                <p className="ss-card-meta">
                  总计 {settings.toolchain.total} · 可用 {settings.toolchain.available} · 缺失 {settings.toolchain.missing}
                </p>
              </article>

              <article className="ss-card">
                <div className="ss-card-head">
                  <h3 className="ss-card-name">存储</h3>
                  <span className={`badge st-${settings.storage.writable ? 'succeeded' : 'failed'}`}>
                    {settings.storage.writable ? '可写' : '不可写'}
                  </span>
                </div>
                <p className="ss-card-meta">
                  {freeValid && <>可用 {formatCapacityBytes(settings.storage.free_bytes)}</>}
                  {freeValid && usedValid && ' · '}
                  {usedValid && <>已用 {formatCapacityBytes(settings.storage.used_bytes)}</>}
                </p>
              </article>

              <article className="ss-card">
                <div className="ss-card-head">
                  <h3 className="ss-card-name">遥测</h3>
                </div>
                <p className="ss-card-meta">
                  {settings.telemetry ? (settings.telemetry.enabled ? '已启用' : '未启用') : '未配置'}
                </p>
              </article>

              <article className="ss-card">
                <div className="ss-card-head">
                  <h3 className="ss-card-name">近期错误</h3>
                  <span className={`badge st-${settings.logs && settings.logs.recent_errors > 0 ? 'running' : 'succeeded'}`}>
                    {settings.logs ? settings.logs.recent_errors : 0}
                  </span>
                </div>
              </article>
            </div>

            <div className="ss-hint" style={{ marginTop: 16 }}>
              系统摘要不包含端点地址、日志路径、错误详情或敏感配置。任务级诊断请前往任务队列。
            </div>

            <div className="ss-card-actions" style={{ marginTop: 12 }}>
              <Link to="/tasks" className="btn btn-secondary btn-sm">前往任务队列</Link>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
