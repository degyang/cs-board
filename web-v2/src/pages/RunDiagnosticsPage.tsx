import { useParams } from 'react-router-dom'
import { useState, useCallback } from 'react'
import { useAsync } from '../lib/api/queries'
import { fetchProject, fetchRun, fetchEvents, fetchLogs } from '../lib/api/client'
import { formatTime, shortId } from '../lib/formatting'
import { BackButton } from '../components/ui/BackButton'
import { CopyButton } from '../components/ui/CopyButton'

export function RunDiagnosticsPage() {
  const { projectId, runId } = useParams<{ projectId: string; runId: string }>()

  const projectLoader = useCallback(() => fetchProject(projectId!), [projectId])
  const { data: projectData } = useAsync(projectLoader, [projectId])

  const runLoader = useCallback(() => {
    if (!projectId || !runId) return Promise.resolve(null)
    return fetchRun(projectId, runId)
  }, [projectId, runId])
  const { data: run, loading, error } = useAsync(runLoader, [projectId, runId])

  const eventsLoader = useCallback(() => {
    if (!projectId || !runId) return Promise.resolve({ items: [], next_cursor: 0 })
    return fetchEvents(projectId, runId)
  }, [projectId, runId])
  const { data: eventsData } = useAsync(eventsLoader, [projectId, runId], 10_000)

  const logsLoader = useCallback(() => {
    if (!projectId || !runId) return Promise.resolve({ items: [] })
    return fetchLogs(projectId, runId)
  }, [projectId, runId])
  const { data: logsData } = useAsync(logsLoader, [projectId, runId], 10_000)

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
        <BackButton to={projectId ? `/projects/${projectId}` : '/'} label="返回工作台" />
        <div className="error-card"><span className="code">加载失败</span><p className="sug">{error}</p></div>
      </div>
    )
  }

  if (!run) {
    return (
      <div className="page">
        <BackButton to={projectId ? `/projects/${projectId}` : '/'} label="返回工作台" />
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
      <BackButton to={projectId ? `/projects/${projectId}` : '/'} label="返回工作台" />

      <div className="page-head">
        <h1 className="page-title">运行诊断</h1>
        <p className="page-desc">
          {projectData?.project?.title ?? '—'} · 运行 {shortId(run.run_id)}
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
          <span className="k">开始时间</span>
          <span className="v">{run.started_at ? formatTime(run.started_at) : '—'}</span>
        </div>
        <div className="settings-row">
          <span className="k">完成时间</span>
          <span className="v">{run.completed_at ? formatTime(run.completed_at) : '—'}</span>
        </div>
        <div className="settings-row">
          <span className="k">命令数</span>
          <span className="v">{run.command_ids?.length ?? 0}</span>
        </div>
      </div>

      {/* Events */}
      <div className="card" style={{ marginTop: 16 }}>
        <h3 className="card-title">事件流</h3>
        {events.length === 0 ? (
          <p style={{ fontSize: 13, color: 'var(--nt-text-muted)', padding: '8px 0' }}>暂无事件</p>
        ) : (
          <div style={{ maxHeight: 300, overflowY: 'auto' }}>
            {events.map((ev) => (
              <div key={ev.sequence} style={{ padding: '6px 0', borderBottom: '1px solid var(--nt-border)', fontSize: 12 }}>
                <span style={{ color: 'var(--nt-text-muted)', fontFamily: 'var(--nt-font-mono)', marginRight: 8 }}>
                  {ev.timestamp ? formatTime(ev.timestamp) : ''}
                </span>
                <span style={{ fontWeight: 600, marginRight: 8 }}>{ev.event_type}</span>
                {ev.stage && <span style={{ color: 'var(--nt-text-secondary)' }}>[{ev.stage}]</span>}
                <span style={{ marginLeft: 8 }}>{ev.action}</span>
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
                <span className="log-ts">{log.timestamp ? formatTime(log.timestamp) : ''}</span>
                <span className={`log-level-${log.level}`}>[{log.level}]</span>
                {log.component && <span> {log.component}</span>}
                {log.stage && <span> [{log.stage}]</span>}
                <span> {log.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
