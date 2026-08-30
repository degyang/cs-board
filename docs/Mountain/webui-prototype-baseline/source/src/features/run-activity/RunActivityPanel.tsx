import { useState } from 'react'
import { Tabs } from '../../components/ui/Tabs'
import { CopyButton } from '../../components/ui/CopyButton'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { useAsync } from '../../lib/api/queries'
import {
  fetchDiagnosticBundles,
  fetchErrorChains,
  fetchEvents,
  fetchLogs,
  fetchMetrics,
  submitCommand,
} from '../../lib/api/client'
import type { ErrorChainView, LogLevel } from '../../lib/api/types'
import { formatBytes, formatClock, formatMs, formatSeconds, percent } from '../../lib/formatting'

// 活动与诊断面板：活动 / 日志 / 指标 / 诊断 四页签（04 §6.6、13 号规格硬性要求）
// 事件按 cursor 增量读取；日志默认隐藏 debug；错误卡固定显示 error_code / retryable / 建议
type PanelTab = 'events' | 'logs' | 'metrics' | 'diagnostics'

const TAB_ITEMS = [
  { key: 'events', label: '活动' },
  { key: 'logs', label: '日志' },
  { key: 'metrics', label: '指标' },
  { key: 'diagnostics', label: '诊断' },
]

export function RunActivityPanel({
  projectId,
  runId,
  traceId,
  defaultTab = 'events',
  collapsible = false,
  initialOpen = true,
}: {
  projectId: string
  runId: string
  traceId: string
  defaultTab?: PanelTab
  collapsible?: boolean
  initialOpen?: boolean
}) {
  const [tab, setTab] = useState<PanelTab>(defaultTab)
  const [open, setOpen] = useState(initialOpen)
  const [logLevel, setLogLevel] = useState<'all' | LogLevel>('all')
  const [exportedBundle, setExportedBundle] = useState<string | null>(null)

  const events = useAsync(() => fetchEvents(projectId, runId), [projectId, runId])
  const logs = useAsync(() => fetchLogs(projectId, runId), [projectId, runId])
  const metrics = useAsync(() => fetchMetrics(projectId, runId), [projectId, runId])
  const errors = useAsync(() => fetchErrorChains(projectId), [projectId])
  const bundles = useAsync(() => fetchDiagnosticBundles(projectId, runId), [projectId, runId])

  const exportBundle = async () => {
    const r = await submitCommand('export_diagnostics', { project_id: projectId, run_id: runId })
    if (r.ok) setExportedBundle('db-20260829-2')
  }

  const body = (
    <div className="panel-body">
      <Tabs items={TAB_ITEMS} active={tab} onChange={(k) => setTab(k as PanelTab)} />

      {tab === 'events' && (
        <div className="row-list" style={{ marginTop: 10 }}>
          <p style={{ fontSize: 12, color: 'var(--nt-text-muted)', margin: '8px 0' }}>
            事件按 cursor 增量读取（当前 cursor ≤ {events.data?.at(-1)?.cursor ?? 0}）；断线后以最后 cursor 恢复。
          </p>
          {(events.data ?? []).map((e) => (
            <div key={e.cursor} className="row">
              <span className="ts">
                #{e.cursor} {formatClock(e.ts)}
              </span>
              <span className="kind mono">{e.kind}</span>
              <span style={{ color: 'var(--nt-text-secondary)' }}>{e.message}</span>
            </div>
          ))}
        </div>
      )}

      {tab === 'logs' && (
        <div style={{ marginTop: 10 }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 8 }}>
            <label style={{ fontSize: 12.5, color: 'var(--nt-text-muted)' }}>级别筛选</label>
            <select className="select" style={{ width: 130 }} value={logLevel} onChange={(e) => setLogLevel(e.target.value as 'all' | LogLevel)}>
              <option value="all">全部（隐藏 debug）</option>
              <option value="debug">debug</option>
              <option value="info">info</option>
              <option value="warn">warn</option>
              <option value="error">error</option>
            </select>
            <span style={{ fontSize: 12, color: 'var(--nt-text-muted)' }}>日志已由服务端脱敏，不含 Secret</span>
          </div>
          <div className="row-list">
            {(logs.data ?? [])
              .filter((l) => (logLevel === 'all' ? l.level !== 'debug' : l.level === logLevel))
              .map((l, i) => (
                <div key={i} className="row">
                  <span className="ts">{formatClock(l.ts)}</span>
                  <span className={'kind mono lv-' + l.level}>{l.level}</span>
                  <span className="mono" style={{ flex: 'none', color: 'var(--nt-text-muted)' }}>{l.component}</span>
                  <span style={{ color: 'var(--nt-text-secondary)' }}>{l.message}</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {tab === 'metrics' && metrics.data && (
        <div style={{ marginTop: 12 }}>
          <table className="metric-table">
            <thead>
              <tr>
                <th>阶段耗时</th>
                <th style={{ textAlign: 'right' }}>耗时</th>
                <th>Provider 延迟 / 重试</th>
                <th style={{ textAlign: 'right' }}>P50</th>
                <th style={{ textAlign: 'right' }}>P95</th>
                <th style={{ textAlign: 'right' }}>重试</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="num">文案分割</td>
                <td className="num" style={{ textAlign: 'right' }}>{formatSeconds(metrics.data.stage_durations_s['split'])}</td>
                <td className="num">tts-provider</td>
                <td className="num" style={{ textAlign: 'right' }}>{formatMs(metrics.data.provider_latency_ms['tts-provider']?.p50 ?? 0)}</td>
                <td className="num" style={{ textAlign: 'right' }}>{formatMs(metrics.data.provider_latency_ms['tts-provider']?.p95 ?? 0)}</td>
                <td className="num" style={{ textAlign: 'right' }}>{metrics.data.provider_latency_ms['tts-provider']?.retries ?? 0}</td>
              </tr>
              <tr>
                <td className="num">克隆配音</td>
                <td className="num" style={{ textAlign: 'right' }}>{formatSeconds(metrics.data.stage_durations_s['voice'])}</td>
                <td className="num">whisper-local</td>
                <td className="num" style={{ textAlign: 'right' }}>{formatMs(metrics.data.provider_latency_ms['whisper-local']?.p50 ?? 0)}</td>
                <td className="num" style={{ textAlign: 'right' }}>{formatMs(metrics.data.provider_latency_ms['whisper-local']?.p95 ?? 0)}</td>
                <td className="num" style={{ textAlign: 'right' }}>{metrics.data.provider_latency_ms['whisper-local']?.retries ?? 0}</td>
              </tr>
              <tr>
                <td className="num">拆分分镜</td>
                <td className="num" style={{ textAlign: 'right' }}>{formatSeconds(metrics.data.stage_durations_s['storyboard'])}</td>
                <td className="num">image-provider</td>
                <td className="num" style={{ textAlign: 'right' }}>{formatMs(metrics.data.provider_latency_ms['image-provider']?.p50 ?? 0)}</td>
                <td className="num" style={{ textAlign: 'right' }}>{formatMs(metrics.data.provider_latency_ms['image-provider']?.p95 ?? 0)}</td>
                <td className="num" style={{ textAlign: 'right' }}>{metrics.data.provider_latency_ms['image-provider']?.retries ?? 0}</td>
              </tr>
              <tr>
                <td className="num">生成插画（进行中）</td>
                <td className="num" style={{ textAlign: 'right' }}>{formatSeconds(metrics.data.stage_durations_s['illustration'])}</td>
                <td className="num">—</td>
                <td className="num" />
                <td className="num" />
                <td className="num" />
              </tr>
            </tbody>
          </table>
          <div className="cost-hint" style={{ marginTop: 12 }}>
            <span>TTS 累计 <b>{formatSeconds(metrics.data.tts_total_s)}</b></span>
            <span>Whisper 累计 <b>{formatSeconds(metrics.data.whisper_total_s)}</b></span>
            <span>fallback 比例 <b>{percent(metrics.data.fallback_ratio)}</b></span>
            <span>音画时差 <b>{metrics.data.av_drift_ms}ms</b></span>
          </div>
        </div>
      )}

      {tab === 'diagnostics' && (
        <div style={{ marginTop: 12 }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 14 }}>
            <span className="trace-chip">
              trace_id <span className="mono">{traceId}</span>
              <CopyButton text={traceId} />
            </span>
            <button type="button" className="btn btn-ghost btn-sm" onClick={exportBundle}>
              导出脱敏诊断包
            </button>
            {exportedBundle && (
              <span style={{ fontSize: 12.5, color: 'var(--nt-primary-700)' }}>
                已生成 <span className="mono">{exportedBundle}</span>（自动脱敏，不含 Secret）
              </span>
            )}
          </div>
          {(errors.data ?? []).map((err: ErrorChainView, i) => (
            <div key={i} className="error-card">
              <span className="code">{err.error_code}</span>
              <StatusBadge status={err.retryable ? 'running' : 'failed'} label={err.retryable ? '可重试' : '不可重试'} />
              <div style={{ marginTop: 6 }}>{err.message}</div>
              {err.stage && <div style={{ fontSize: 12, color: 'var(--nt-text-muted)', marginTop: 2 }}>失败阶段：{err.stage}{err.unit_id ? ` · ${err.unit_id}` : ''}{err.visual_id ? ` · ${err.visual_id}` : ''}</div>}
              <div className="sug">建议：{err.suggestion}</div>
            </div>
          ))}
          {(bundles.data ?? []).length > 0 && (
            <div style={{ fontSize: 12.5, color: 'var(--nt-text-muted)', marginTop: 8 }}>
              历史诊断包：
              {(bundles.data ?? []).map((b) => (
                <span key={b.bundle_id} className="mono" style={{ marginRight: 14 }}>
                  {b.bundle_id}（{formatBytes(b.size_bytes)}，{b.redacted ? '已脱敏' : '未脱敏'}）
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )

  if (!collapsible) return <div className="wb-panel">{body}</div>

  return (
    <div className="wb-panel">
      <div
        className={'panel-head' + (open ? ' open' : '')}
        onClick={() => setOpen((v) => !v)}
        role="button"
        aria-expanded={open}
      >
        活动与诊断
        <span style={{ fontWeight: 400, fontSize: 12, color: 'var(--nt-text-muted)' }}>事件 / 日志 / 指标 / 诊断包</span>
        <span className="caret">▼</span>
      </div>
      {open && body}
    </div>
  )
}

