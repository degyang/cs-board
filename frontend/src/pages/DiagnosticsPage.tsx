/* ==========================================================================
   系统诊断 — read-only system-level summary
   ========================================================================== */

import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchDiagnosticsSettings } from '../lib/api/settings'
import type { DiagnosticsSettings } from '../lib/api/types'
import { hasValidCapacity, formatCapacityBytes } from '../lib/formatting'

function mapApiStatus(raw: string): { label: string; cls: string } {
  const lower = raw.toLowerCase()
  if (lower === 'healthy' || lower === 'ok') return { label: '正常', cls: 'dg-status--ok' }
  if (lower === 'degraded') return { label: '降级', cls: 'dg-status--warn' }
  if (lower === 'failed' || lower === 'down' || lower === 'unavailable') return { label: '不可用', cls: 'dg-status--fail' }
  return { label: raw, cls: 'dg-status--unknown' }
}

function DiagnosticsSkeleton() {
  return (
    <div className="dg-grid" aria-label="正在加载诊断信息">
      {[0, 1, 2, 3, 4, 5].map(i => (
        <div className="dg-card dg-card--skeleton" key={i} aria-hidden="true">
          <span className="dg-skeleton dg-skeleton--title" />
          <span className="dg-skeleton dg-skeleton--line" />
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
    <section className="dg-panel" aria-labelledby="diagnostics-title">
      <h2 className="dg-title" id="diagnostics-title">系统诊断</h2>
      <p className="dg-description">
        以下为当前运行环境的系统级摘要，仅作只读展示。
        具体任务的事件、日志、Trace 和产物诊断请进入任务工作台查看。
      </p>

      {loading && <DiagnosticsSkeleton />}
      {!loading && error && (
        <div className="dg-error" role="alert">
          <p>加载诊断信息失败：{error}</p>
          <button className="btn btn-secondary" type="button" onClick={() => void load()}>重新加载</button>
        </div>
      )}
      {!loading && !error && settings && (
        <>
          <div className="dg-grid">
            {/* API */}
            <article className="dg-card">
              <h3 className="dg-card-title">API</h3>
              <span className={`dg-status ${apiStatus!.cls}`}>{apiStatus!.label}</span>
            </article>

            {/* Services */}
            <article className="dg-card">
              <h3 className="dg-card-title">动态服务</h3>
              <p className="dg-card-value">
                总计 {settings.services.total} · 可用 {settings.services.available} · 不可用 {settings.services.unavailable}
              </p>
            </article>

            {/* Toolchain */}
            <article className="dg-card">
              <h3 className="dg-card-title">工具链</h3>
              <p className="dg-card-value">
                总计 {settings.toolchain.total} · 可用 {settings.toolchain.available} · 缺失 {settings.toolchain.missing}
              </p>
            </article>

            {/* Storage */}
            <article className="dg-card">
              <h3 className="dg-card-title">存储</h3>
              <p className="dg-card-value">
                {settings.storage.writable ? '可写' : '不可写'}
                {freeValid && (
                  <> · 可用 {formatCapacityBytes(settings.storage.free_bytes)}</>
                )}
                {usedValid && (
                  <> · 已用 {formatCapacityBytes(settings.storage.used_bytes)}</>
                )}
              </p>
            </article>

            {/* Telemetry */}
            <article className="dg-card">
              <h3 className="dg-card-title">遥测</h3>
              <p className="dg-card-value">
                {settings.telemetry ? (settings.telemetry.enabled ? '已启用' : '未启用') : '未配置'}
              </p>
            </article>

            {/* Logs */}
            <article className="dg-card">
              <h3 className="dg-card-title">近期错误</h3>
              <p className={`dg-card-value ${settings.logs && settings.logs.recent_errors > 0 ? 'dg-card-value--warn' : ''}`}>
                {settings.logs ? settings.logs.recent_errors : 0}
              </p>
            </article>
          </div>

          <div className="dg-redaction">
            <p>系统摘要不包含端点地址、日志路径、错误详情或敏感配置。任务级诊断请前往任务队列。</p>
            <Link to="/tasks" className="btn btn-secondary">前往任务队列</Link>
          </div>
        </>
      )}
    </section>
  )
}
