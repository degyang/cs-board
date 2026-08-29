import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProjects } from '../lib/api/client'
import type { Project } from '../lib/api/types'
import { formatTime, statusText, statusClass } from '../lib/formatting'

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchProjects()
      .then((res) => setProjects(res.items))
      .catch((e) => setError(e instanceof Error ? e.message : '加载失败'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="page">
      <div className="page-head">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h1 className="page-title">项目列表</h1>
            <p className="page-desc">全部项目与运行状态。</p>
          </div>
          <Link to="/projects/new" className="btn btn-primary">
            ➕ 创建项目
          </Link>
        </div>
      </div>

      {loading && (
        <div className="loading">
          <span className="spinner" />
          加载中…
        </div>
      )}

      {error && (
        <div className="error-card">
          <div className="code">加载失败</div>
          <div className="sug">{error}</div>
        </div>
      )}

      {!loading && !error && projects.length === 0 && (
        <div className="empty-state">
          <div className="empty-illu">📋</div>
          <div className="empty-title">还没有项目</div>
          <div className="empty-sub">创建第一个项目开始制作视频。</div>
          <Link to="/projects/new" className="btn btn-primary" style={{ marginTop: 8 }}>
            ➕ 创建项目
          </Link>
        </div>
      )}

      {!loading && !error && projects.map((project) => (
        <Link
          key={project.project_id}
          to={`/projects/${project.project_id}`}
          className="proj-card"
          style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}
        >
          <div className="proj-top">
            <h3 className="proj-name">{project.title}</h3>
            <span className={`badge ${statusClass(project.status)}`}>
              <span className="dot" />
              {statusText(project.status)}
            </span>
            <span className="proj-time">更新于 {formatTime(project.updated_at)}</span>
          </div>
          <div className="proj-meta">
            <span className="m">引擎: {project.engine}</span>
            <span className="m mono">Pipeline: {project.pipeline_id}</span>
            {project.active_run_id && (
              <span className="m mono" title={project.active_run_id}>
                Run: {project.active_run_id.slice(0, 8)}…
              </span>
            )}
          </div>
          <div className="proj-actions">
            <span className="btn btn-ghost btn-sm">查看详情</span>
          </div>
        </Link>
      ))}
    </div>
  )
}
