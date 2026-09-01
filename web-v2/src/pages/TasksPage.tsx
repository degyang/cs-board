import { Link, useNavigate } from 'react-router-dom'
import { useState, useCallback } from 'react'
import { useAsync } from '../lib/api/queries'
import { fetchTasks } from '../lib/api/client'
import { formatTime, shortId } from '../lib/formatting'
import { StatusBadge } from '../components/ui/StatusBadge'
import { Tabs } from '../components/ui/Tabs'
import type { TaskQueueItem } from '../lib/api/types'

const STATUS_TABS = [
  { key: 'all', label: '全部' },
  { key: 'running', label: '运行中' },
  { key: 'succeeded', label: '已完成' },
  { key: 'failed', label: '失败' },
  { key: 'cancelled', label: '已取消' },
]

export function TasksPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState('all')
  const [search, setSearch] = useState('')

  const loader = useCallback(() => fetchTasks({ limit: 50 }), [])
  const { data, loading, error } = useAsync(loader, [], 15_000)

  const tasks = data?.items ?? []
  const filtered = tasks.filter((t) => {
    if (tab !== 'all' && t.status !== tab) return false
    if (search && !t.title.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const tabItems = STATUS_TABS.map((tabDef) => ({
    ...tabDef,
    count: tabDef.key === 'all' ? tasks.length : tasks.filter((t) => t.status === tabDef.key).length,
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
        <Link to="/tasks/new" className="btn btn-primary">
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
            <Link to="/tasks/new" className="btn btn-primary" style={{ marginTop: 8 }}>
              + 新建任务
            </Link>
          )}
        </div>
      )}

      {filtered.map((t) => (
        <TaskCard key={t.task_id} task={t} onOpen={() => navigate(`/tasks/${t.task_id}`)} />
      ))}
    </div>
  )
}

function TaskCard({ task: t, onOpen }: { task: TaskQueueItem; onOpen: () => void }) {
  return (
    <div className="task-card">
      <div className="task-top">
        <h3 className="task-name">{t.title || `任务 ${shortId(t.task_id)}`}</h3>
        <StatusBadge status={t.status} />
        <span className="task-time">{formatTime(t.updated_at)}</span>
      </div>
      <div className="task-meta">
        <span className="m">ID: {shortId(t.task_id)}</span>
        {t.engine && <span className="m">引擎: {t.engine}</span>}
        {t.pipeline_id && <span className="m">流水线: {t.pipeline_id}</span>}
      </div>
      <div className="task-actions">
        <button className="btn btn-primary btn-sm" onClick={onOpen}>
          进入工作台
        </button>
        <Link
          to={`/tasks/${t.task_id}/runs/${t.active_run_id ?? ''}/diagnostics`}
          className="btn btn-ghost btn-sm"
          style={!t.active_run_id ? { pointerEvents: 'none', opacity: 0.4 } : undefined}
        >
          诊断
        </Link>
      </div>
    </div>
  )
}
