import { useParams } from 'react-router-dom'
import { useState, useCallback } from 'react'
import { useAsync } from '../lib/api/queries'
import { fetchRun, fetchEvents, fetchLogs } from '../lib/api/client'
import { formatTime, shortId } from '../lib/formatting'
import { BackButton } from '../components/ui/BackButton'
import { CopyButton } from '../components/ui/CopyButton'

export function RunDiagnosticsPage() {
  const { taskId, runId } = useParams<{ taskId: string; runId: string }>()

  const runLoader = useCallback(() => {
    if (!taskId || !runId) return Promise.resolve(null)
    return fetchRun(taskId, runId)
  }, [taskId, runId])
  const { data: run, loading, error } = useAsync(runLoader, [taskId, runId])

  const eventsLoader = useCallback(() => {
    if (!taskId || !runId) return Promise.resolve({ items: [], next_cursor: 0 })
    return fetchEvents(taskId, runId)
  }, [taskId, runId])
  const { data: eventsData } = useAsync(eventsLoader, [taskId, runId], 10_000)

  const logsLoader = useCallback(() => {
    if (!taskId || !runId) return Promise.resolve({ items: [] })
    return fetchLogs(taskId, runId)
  }, [taskId, runId])
  const { data: logsData } = useAsync(logsLoader, [taskId, runId], 10_000)

  const events = eventsData?.items ?? []
  const logs = logsData?.items ?? []

  const [logFilter, setLogFilter] = useState('all')

  const filteredLogs = logFilter === 'all' ? logs : logs.filter((l) => l.level === logFilter)

  if (loading && !run) {
    return (
      <div className="page">
        <p className="loading"><span className="spinner" />加载中…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="page">
        <BackButton to={taskId ? `/tasks/${taskId}` : '/'} label="返回工作台" />
        <div className="error-card"><span className="code">加载失败</span><p className="sug">{error}</p></div>
      </div>
    )
  }

  if (!run) {
    return (
      <div className="page">
        <BackButton to={taskId ? `/tasks/${taskId}` : '/'} label="返回工作台" />
        <div className="empty-state">
          <div className="empty-illu">🔍</div>
          <div className="empty-title">运行不存在</div>
          <div className="empty-sub">找不到指定的运行记录</div>
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      <BackButton to={taskId ? `/tasks/${taskId}` : '/'} label="返回工作台" />

      <div className="page-head">
        <h1 className="page-title">运行诊断</h1>
        <p className="page-desc">
          运行 {shortId(run.run_id)}
        </p>
      </div>

      {/* IDs */}
      <div className="chip-ids">
        <span className="id-chip">
          run: {shortId(run.run_id)}
          <CopyButton text={run.run_id} />
        </span>
        <span className="id-chip">
          trace: {shortId(run.trace_id)}
          <CopyButton text={run.trace_id} />
        </span>
        <span className="id-chip">
          entrypoint: {run.entrypoint}
        </span>
      </div>

      {/* Run info */}
      <div className="card" style={{ marginTop: 16 }}>
        <div className="settings-row">
          <span className="k">状态</span>
          <span className="v">{run.status}</span>
        </div>
        <div className="settings-row">
          <span className="k">目标阶段</span>
          <span className="v">{run.target_stage ?? '—'}</span>
        </div>
        <div className="settings-row">
          <span className="k">开始时间</span>
          <span className="v">{run.started_at ? formatTime(run.started_at) : '—'}</span>
        </div>
        <div className="settings-row">
          <span className="k">完成时间</span>
          <span className="v">{run.finished_at ? formatTime(run.finished_at) : '—'}</span>
        </div>
      </div>

      {/* Stages */}
      <div className="card" style={{ marginTop: 16 }}>
        <h3 className="card-title">阶段状态</h3>
        {Object.keys(run.stages).length === 0 ? (
          <p style={{ fontSize: 13, color: 'var(--nt-text-muted)', padding: '8px 0' }}>暂无阶段数据</p>
        ) : (
          <div>
            {Object.entries(run.stages).map(([stage, state]) => (
              <div key={stage} style={{ padding: '6px 0', borderBottom: '1px solid var(--nt-border)', display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
                <span style={{ fontWeight: 600, minWidth: 160 }}>{stage}</span>
                <span>{state.status}</span>
                <span style={{ color: 'var(--nt-text-muted)', fontSize: 12 }}>attempt {state.attempt}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Events */}
      <div className="card" style={{ marginTop: 16 }}>
        <h3 className="card-title">事件流</h3>
        {events.length === 0 ? (
          <p style={{ fontSize: 13, color: 'var(--nt-text-muted)', padding: '8px 0' }}>暂无事件</p>
        ) : (
          <div style={{ maxHeight: 300, overflowY: 'auto' }}>
            {events.map((ev, i) => (
              <div key={i} style={{ padding: '6px 0', borderBottom: '1px solid var(--nt-border)', fontSize: 12 }}>
                <span style={{ color: 'var(--nt-text-muted)', fontFamily: 'var(--nt-font-mono)', marginRight: 8 }}>
                  {ev.timestamp ? formatTime(String(ev.timestamp)) : ''}
                </span>
                <span style={{ fontWeight: 600, marginRight: 8 }}>{String(ev.event_type ?? '')}</span>
                {ev.stage != null && <span style={{ color: 'var(--nt-text-secondary)' }}>[{String(ev.stage)}]</span>}
                {ev.action != null && <span style={{ marginLeft: 8 }}>{String(ev.action)}</span>}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Logs */}
      <div className="card" style={{ marginTop: 16 }}>
        <h3 className="card-title">日志</h3>
        <div className="filter-row" style={{ marginBottom: 8 }}>
          <select className="select" value={logFilter} onChange={(e) => setLogFilter(e.target.value)} style={{ width: 120 }}>
            <option value="all">全部</option>
            <option value="ERROR">ERROR</option>
            <option value="WARN">WARN</option>
            <option value="INFO">INFO</option>
          </select>
          <span style={{ fontSize: 12, color: 'var(--nt-text-muted)' }}>{filteredLogs.length} 条</span>
        </div>
        {filteredLogs.length === 0 ? (
          <p style={{ fontSize: 13, color: 'var(--nt-text-muted)', padding: '8px 0' }}>暂无日志</p>
        ) : (
          <div className="activity-body" style={{ maxHeight: 400 }}>
            {filteredLogs.map((log, i) => (
              <div key={i} className="log-line">
                <span className="log-ts">{log.timestamp ? formatTime(String(log.timestamp)) : ''}</span>
                <span className={`log-level-${String(log.level ?? '')}`}>[{String(log.level ?? '')}]</span>
                {log.component != null && <span> {String(log.component)}</span>}
                {log.stage != null && <span> [{String(log.stage)}]</span>}
                <span> {String(log.message ?? '')}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
