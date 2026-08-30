import { useParams, Link } from 'react-router-dom'
import { useState, useCallback } from 'react'
import { useAsync } from '../lib/api/queries'
import { fetchProject, fetchUnits, fetchArtifacts, cancelRun, retryRun, getFinalUrl, fetchStages } from '../lib/api/client'
import { formatTime, shortId, formatBytes, statusText } from '../lib/formatting'
import { StatusBadge } from '../components/ui/StatusBadge'
import { CopyButton } from '../components/ui/CopyButton'
import { BackButton } from '../components/ui/BackButton'
import { STAGE_KEYS, STAGE_NAMES } from '../lib/api/types'

export function ProjectWorkbenchPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [showActivity, setShowActivity] = useState(false)

  const projectLoader = useCallback(() => fetchProject(projectId!), [projectId])
  const { data: projectData, loading: projectLoading, error: projectError } = useAsync(projectLoader, [projectId], 15_000)

  const project = projectData?.project
  const run = projectData?.run

  const runId = run?.run_id

  const unitsLoader = useCallback(() => {
    if (!projectId || !runId) return Promise.resolve({ items: [] })
    return fetchUnits(projectId, runId)
  }, [projectId, runId])
  const { data: unitsData } = useAsync(unitsLoader, [projectId, runId], 15_000)

  const artifactsLoader = useCallback(() => {
    if (!projectId || !runId) return Promise.resolve({ items: [] })
    return fetchArtifacts(projectId, runId)
  }, [projectId, runId])
  const { data: artifactsData } = useAsync(artifactsLoader, [projectId, runId], 15_000)

  const stagesLoader = useCallback(() => {
    if (!projectId || !runId) return Promise.resolve({ items: [] })
    return fetchStages(projectId, runId)
  }, [projectId, runId])
  const { data: stagesData } = useAsync(stagesLoader, [projectId, runId], 15_000)

  const units = unitsData?.items ?? []
  const artifacts = artifactsData?.items ?? []
  const stages = stagesData?.items ?? []

  const [actionLoading, setActionLoading] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  async function handleCancel() {
    if (!projectId || !runId) return
    setActionLoading(true)
    setActionError(null)
    try {
      await cancelRun(projectId, runId)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : '取消失败')
    } finally {
      setActionLoading(false)
    }
  }

  async function handleRetry() {
    if (!projectId || !runId) return
    setActionLoading(true)
    setActionError(null)
    try {
      await retryRun(projectId, runId)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : '重试失败')
    } finally {
      setActionLoading(false)
    }
  }

  if (projectLoading && !projectData) {
    return (
      <div className="page">
        <p className="loading"><span className="spinner" />加载中…</p>
      </div>
    )
  }

  if (projectError) {
    return (
      <div className="page">
        <BackButton to="/" label="返回任务队列" />
        <div className="error-card"><span className="code">加载失败</span><p className="sug">{projectError}</p></div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="page">
        <BackButton to="/" label="返回任务队列" />
        <div className="empty-state">
          <div className="empty-illu">🔍</div>
          <div className="empty-title">任务不存在</div>
        </div>
      </div>
    )
  }

  // Derive stage statuses from stages data
  const stageStatuses: Record<string, string> = {}
  for (const s of stages) {
    stageStatuses[s.stage] = (s as Record<string, unknown>).status as string ?? 'pending'
  }
  // Fill missing stages as pending
  for (const key of STAGE_KEYS) {
    if (!stageStatuses[key]) stageStatuses[key] = 'pending'
  }

  const completedCount = STAGE_KEYS.filter((k) => stageStatuses[k] === 'succeeded').length
  const hasFinal = artifacts.some((a) => a.stage === 'compose-video' && a.status === 'succeeded')

  return (
    <div className="page">
      <BackButton to="/" label="返回任务队列" />

      {/* Top bar */}
      <div className="topbar" style={{ position: 'static', padding: 0, border: 'none', background: 'none', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <h1 className="page-title">{project.title || `任务 ${shortId(project.project_id)}`}</h1>
          <StatusBadge status={run?.status ?? project.status} />
          <span style={{ fontSize: 12, color: 'var(--nt-text-muted)' }}>
            创建于 {formatTime(project.created_at)}
          </span>
        </div>

        {/* IDs */}
        <div className="chip-ids">
          <span className="id-chip">
            project: {shortId(project.project_id)}
            <CopyButton text={project.project_id} />
          </span>
          {run && (
            <>
              <span className="id-chip">
                run: {shortId(run.run_id)}
                <CopyButton text={run.run_id} />
              </span>
              <span className="id-chip">
                trace: {shortId(run.trace_id)}
                <CopyButton text={run.trace_id} />
              </span>
            </>
          )}
        </div>

        {/* Actions */}
        <div className="run-actions">
          {run && (run.status === 'pending' || run.status === 'running') && (
            <button className="btn btn-danger btn-sm" onClick={handleCancel} disabled={actionLoading}>
              取消
            </button>
          )}
          {run && (run.status === 'failed' || run.status === 'cancelled') && (
            <button className="btn btn-primary btn-sm" onClick={handleRetry} disabled={actionLoading}>
              重试
            </button>
          )}
          {hasFinal && run && (
            <a href={getFinalUrl(project.project_id, run.run_id)} className="btn btn-ghost btn-sm" download>
              下载成片
            </a>
          )}
          {run && (
            <Link to={`/projects/${project.project_id}/runs/${run.run_id}/diagnostics`} className="btn btn-ghost btn-sm">
              诊断
            </Link>
          )}
        </div>

        {actionError && <div className="error-card" style={{ marginTop: 8 }}><span className="code">{actionError}</span></div>}
      </div>

      {/* Stage Timeline */}
      <div className="timeline">
        {STAGE_KEYS.map((key, i) => (
          <div key={key} style={{ display: 'contents' }}>
            <div className={`timeline-node st-${stageStatuses[key]}`}>
              <span className="node-label">{STAGE_NAMES[key]}</span>
            </div>
            {i < STAGE_KEYS.length - 1 && <div className="timeline-connector" />}
          </div>
        ))}
      </div>

      {/* 3-column workbench grid */}
      <div className="workbench-grid">
        {/* Left: Units */}
        <div className="panel">
          <div className="panel-title">
            配音单元
            {units.length > 0 && <span className="badge">{units.length}</span>}
          </div>
          {units.length === 0 ? (
            <div className="empty-state" style={{ padding: '24px 0' }}>
              <div className="empty-sub">暂无配音单元</div>
            </div>
          ) : (
            <ul className="unit-list">
              {units.map((u) => (
                <li key={u.unit_id} className="unit-item">
                  <div className="unit-label">单元 {u.order + 1}</div>
                  <div className="unit-text">{u.text}</div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Center: Stage Workspace */}
        <div className="panel">
          <div className="panel-title">
            阶段工作区
            <span className="badge">{completedCount}/{STAGE_KEYS.length}</span>
          </div>
          {run ? (
            <div>
              {STAGE_KEYS.map((key) => {
                const st = stageStatuses[key]
                return (
                  <div key={key} style={{ padding: '10px 0', borderBottom: '1px solid var(--nt-border)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <StatusBadge status={st} />
                      <span style={{ fontSize: 13, fontWeight: 600 }}>{STAGE_NAMES[key]}</span>
                    </div>
                    {run.stages?.[key]?.error && (
                      <div className="error-card" style={{ marginTop: 6 }}>
                        <span className="code">{run.stages[key].error}</span>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="empty-state" style={{ padding: '24px 0' }}>
              <div className="empty-sub">任务尚未启动运行</div>
            </div>
          )}
        </div>

        {/* Right: Artifacts */}
        <div className="panel">
          <div className="panel-title">
            产物
            {artifacts.length > 0 && <span className="badge">{artifacts.length}</span>}
          </div>
          {artifacts.length === 0 ? (
            <div className="empty-state" style={{ padding: '24px 0' }}>
              <div className="empty-sub">暂无产物</div>
            </div>
          ) : (
            <table className="artifact-table">
              <thead>
                <tr>
                  <th>文件</th>
                  <th>状态</th>
                  <th>大小</th>
                </tr>
              </thead>
              <tbody>
                {artifacts.map((a) => (
                  <tr key={a.artifact_key}>
                    <td style={{ fontFamily: 'var(--nt-font-mono)', fontSize: 12 }}>{a.artifact_key}</td>
                    <td><StatusBadge status={a.status} /></td>
                    <td style={{ fontSize: 12 }}>{formatBytes(a.size_bytes ?? undefined)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Activity Panel */}
      <div className="activity-panel">
        <button className="activity-toggle" onClick={() => setShowActivity(!showActivity)}>
          <span className={`chevron ${showActivity ? 'open' : ''}`}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M5 2l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
          运行日志
        </button>
        {showActivity && (
          <div className="activity-body">
            {run ? (
              <p style={{ fontSize: 12, color: 'var(--nt-text-muted)', padding: 8 }}>
                运行 {shortId(run.run_id)} — {statusText(run.status)}
                {run.started_at && <>，开始于 {formatTime(run.started_at)}</>}
              </p>
            ) : (
              <p style={{ fontSize: 12, color: 'var(--nt-text-muted)', padding: 8 }}>暂无运行记录</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
