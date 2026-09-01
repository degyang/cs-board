import { Link, useParams } from 'react-router-dom'
import { CopyButton } from '../components/ui/CopyButton'
import { BackButton } from '../components/ui/BackButton'
import { useAsync } from '../lib/api/queries'
import { fetchProjectDetail } from '../lib/api/client'
import { RunActivityPanel } from '../features/run-activity/RunActivityPanel'

// 运行诊断 /projects/:projectId/runs/:runId/diagnostics（04 §3、13 号规格）
// 与工作台底部面板同链路（同一 API View），双入口不重复轮询
export function RunDiagnosticsPage() {
  const { projectId, runId } = useParams<{ projectId: string; runId: string }>()
  const { data, loading } = useAsync(() => fetchProjectDetail(projectId ?? ''), [projectId])

  if (loading || !data) return <div className="page"><p style={{ color: 'var(--nt-text-muted)' }}>加载中…</p></div>

  const { project, run } = data
  const traceId = runId === run.run_id ? run.trace_id : 'tr-unknown'

  return (
    <>
      <div className="topbar">
        <BackButton to={`/projects/${project.project_id}`} label="返回工作台" />
        <span className="crumb">
          <a href="/projects">任务队列</a> / <Link to={`/projects/${project.project_id}`}>{project.name}</Link> /{' '}
          <span style={{ color: 'var(--nt-text)' }}>运行诊断</span>
        </span>
        <span className="crumb mono" style={{ marginLeft: 'auto', fontSize: 12 }}>
          run {runId}
        </span>
      </div>

      <div className="page">
        <div className="page-head">
          <h1 className="page-title">运行诊断</h1>
          <p className="page-desc">
            活动、日志、指标与诊断包；trace_id 可复制。Web 创建的 Run 可由 Skill 通过同一 trace_id 继续，反向亦然。
          </p>
        </div>
        <div style={{ marginBottom: 16 }}>
          <span className="trace-chip">
            trace_id <span className="mono">{traceId}</span>
            <CopyButton text={traceId} />
          </span>
        </div>
        <RunActivityPanel
          projectId={project.project_id}
          runId={runId ?? run.run_id}
          traceId={traceId}
          defaultTab="diagnostics"
        />
      </div>
    </>
  )
}

