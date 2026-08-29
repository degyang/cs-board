import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProject } from '../lib/api/client'
import type { ProjectDetail } from '../lib/api/types'
import { formatTime, statusText, statusClass, shortId } from '../lib/formatting'

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [detail, setDetail] = useState<ProjectDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    fetchProject(id)
      .then(setDetail)
      .catch((e) => setError(e instanceof Error ? e.message : '加载失败'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="page">
        <div className="loading">
          <span className="spinner" />
          加载中…
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="page">
        <div className="error-card">
          <div className="code">加载失败</div>
          <div className="sug">{error}</div>
        </div>
        <Link to="/" className="btn btn-ghost" style={{ marginTop: 12 }}>
          ← 返回项目列表
        </Link>
      </div>
    )
  }

  if (!detail) return null

  const { project, run } = detail

  return (
    <div className="page">
      <div className="page-head">
        <h1 className="page-title">{project.title}</h1>
        <p className="page-desc">
          项目 ID: <code>{project.project_id}</code>
        </p>
      </div>

      <div className="card">
        <div className="card-title">项目信息</div>
        <div className="settings-row">
          <span className="k">状态</span>
          <span className="v">
            <span className={`badge ${statusClass(project.status)}`}>
              <span className="dot" />
              {statusText(project.status)}
            </span>
          </span>
        </div>
        <div className="settings-row">
          <span className="k">引擎</span>
          <span className="v">{project.engine}</span>
        </div>
        <div className="settings-row">
          <span className="k">Pipeline</span>
          <span className="v mono">{project.pipeline_id}</span>
        </div>
        <div className="settings-row">
          <span className="k">创建时间</span>
          <span className="v">{formatTime(project.created_at)}</span>
        </div>
        <div className="settings-row">
          <span className="k">更新时间</span>
          <span className="v">{formatTime(project.updated_at)}</span>
        </div>
      </div>

      {run && (
        <div className="card">
          <div className="card-title">当前运行</div>
          <div className="settings-row">
            <span className="k">Run ID</span>
            <span className="v mono">{shortId(run.run_id, 16)}</span>
          </div>
          <div className="settings-row">
            <span className="k">状态</span>
            <span className="v">
              <span className={`badge ${statusClass(run.status)}`}>
                <span className="dot" />
                {statusText(run.status)}
              </span>
            </span>
          </div>
          <div className="settings-row">
            <span className="k">Trace ID</span>
            <span className="v mono">{shortId(run.trace_id, 16)}</span>
          </div>
          <div className="settings-row">
            <span className="k">入口</span>
            <span className="v">{run.entrypoint}</span>
          </div>
          <div className="settings-row">
            <span className="k">目标阶段</span>
            <span className="v">{run.target_stage ?? '—'}</span>
          </div>
          <div className="settings-row">
            <span className="k">启动时间</span>
            <span className="v">{formatTime(run.started_at)}</span>
          </div>

          {Object.keys(run.stages).length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div className="card-title" style={{ marginBottom: 8 }}>阶段状态</div>
              {Object.entries(run.stages).map(([name, state]) => (
                <div key={name} className="settings-row">
                  <span className="k">{name}</span>
                  <span className="v">
                    <span className={`badge ${statusClass(state.status)}`}>
                      <span className="dot" />
                      {statusText(state.status)}
                    </span>
                    <span style={{ marginLeft: 8, fontSize: 12, color: 'var(--nt-text-muted)' }}>
                      尝试 {state.attempt}
                    </span>
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {!run && (
        <div className="card">
          <div className="empty-state" style={{ padding: '32px 20px' }}>
            <div className="empty-illu" style={{ fontSize: 32 }}>🎬</div>
            <div className="empty-title">尚未启动运行</div>
            <div className="empty-sub">上传文案与参考音频后，可启动制作流程。</div>
          </div>
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        <Link to="/" className="btn btn-ghost">
          ← 返回项目列表
        </Link>
      </div>
    </div>
  )
}
