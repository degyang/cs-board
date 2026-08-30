import { Link, useNavigate } from 'react-router-dom'
import { useState, useCallback } from 'react'
import { useAsync } from '../lib/api/queries'
import { fetchProjects } from '../lib/api/client'
import { formatTime, shortId } from '../lib/formatting'
import { StatusBadge } from '../components/ui/StatusBadge'
import { Tabs } from '../components/ui/Tabs'
import type { Project } from '../lib/api/types'

const STATUS_TABS = [
  { key: 'all', label: '全部' },
  { key: 'running', label: '运行中' },
  { key: 'succeeded', label: '已完成' },
  { key: 'failed', label: '失败' },
  { key: 'cancelled', label: '已取消' },
]

export function ProjectsPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState('all')
  const [search, setSearch] = useState('')

  const loader = useCallback(() => fetchProjects(50), [])
  const { data, loading, error } = useAsync(loader, [], 15_000)

  const projects = data?.items ?? []
  const filtered = projects.filter((p) => {
    if (tab !== 'all' && p.status !== tab) return false
    if (search && !p.title.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const tabItems = STATUS_TABS.map((t) => ({
    ...t,
    count: t.key === 'all' ? projects.length : projects.filter((p) => p.status === t.key).length,
  }))

  return (
    <div className="page">
      <div className="page-head">
        <h1 className="page-title">任务队列</h1>
        <p className="page-desc">所有视频制作任务，按状态筛选和搜索</p>
      </div>

      <div className="filter-row">
        <div style={{ flex: 1 }}>
          <Tabs items={tabItems} active={tab} onChange={setTab} />
        </div>
        <input
          className="input"
          type="text"
          placeholder="搜索任务名称…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: 220 }}
        />
        <Link to="/projects/new" className="btn btn-primary">
          + 新建任务
        </Link>
      </div>

      {loading && !data && <p className="loading"><span className="spinner" />加载中…</p>}
      {error && <div className="error-card"><span className="code">加载失败</span><p className="sug">{error}</p></div>}

      {!loading && filtered.length === 0 && (
        <div className="empty-state">
          <div className="empty-illu">📭</div>
          <div className="empty-title">暂无任务</div>
          <div className="empty-sub">
            {tab === 'all' ? '点击"新建任务"开始制作第一个视频' : `没有${STATUS_TABS.find((t) => t.key === tab)?.label ?? ''}状态的任务`}
          </div>
          {tab === 'all' && (
            <Link to="/projects/new" className="btn btn-primary" style={{ marginTop: 8 }}>
              + 新建任务
            </Link>
          )}
        </div>
      )}

      {filtered.map((p) => (
        <ProjectCard key={p.project_id} project={p} onOpen={() => navigate(`/projects/${p.project_id}`)} />
      ))}
    </div>
  )
}

function ProjectCard({ project: p, onOpen }: { project: Project; onOpen: () => void }) {
  return (
    <div className="proj-card">
      <div className="proj-top">
        <h3 className="proj-name">{p.title || `任务 ${shortId(p.project_id)}`}</h3>
        <StatusBadge status={p.status} />
        <span className="proj-time">{formatTime(p.updated_at)}</span>
      </div>
      <div className="proj-meta">
        <span className="m">ID: {shortId(p.project_id)}</span>
        {p.engine && <span className="m">引擎: {p.engine}</span>}
        {p.pipeline_id && <span className="m">流水线: {p.pipeline_id}</span>}
      </div>
      <div className="proj-actions">
        <button className="btn btn-primary btn-sm" onClick={onOpen}>
          进入工作台
        </button>
        <Link
          to={`/projects/${p.project_id}/runs/${p.active_run_id ?? ''}/diagnostics`}
          className="btn btn-ghost btn-sm"
          style={!p.active_run_id ? { pointerEvents: 'none', opacity: 0.4 } : undefined}
        >
          诊断
        </Link>
      </div>
    </div>
  )
}
