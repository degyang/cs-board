/* ==========================================================================
   任务队列 — real task queue backed by GET /api/v1/tasks
   ========================================================================== */

import { useEffect, useRef, useState, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { fetchTasks } from '../lib/api/client'
import { formatTime, shortId } from '../lib/formatting'
import { StatusBadge } from '../components/ui/StatusBadge'
import { STAGE_NAMES } from '../lib/api/types'
import type { TaskQueueItem, TaskListResponse } from '../lib/api/types'

const STATUS_TABS = [
  { key: 'all', label: '全部' },
  { key: 'running', label: '运行中' },
  { key: 'succeeded', label: '已完成' },
  { key: 'failed', label: '失败' },
  { key: 'cancelled', label: '已取消' },
]

function stageLabel(stage: string | null | undefined): string {
  if (!stage) return ''
  return STAGE_NAMES[stage as keyof typeof STAGE_NAMES] ?? stage
}

function TasksSkeleton() {
  return (
    <div className="task-list" aria-label="正在加载任务列表">
      {[0, 1, 2].map(i => (
        <div className="task-card task-card--skeleton" key={i} aria-hidden="true">
          <span className="task-skeleton task-skeleton--title" />
          <span className="task-skeleton task-skeleton--line" />
        </div>
      ))}
    </div>
  )
}

export function TasksPage() {
  const navigate = useNavigate()
  const [status, setStatus] = useState('all')
  const [search, setSearch] = useState('')
  const [appliedSearch, setAppliedSearch] = useState('')
  const [items, setItems] = useState<TaskQueueItem[]>([])
  const [nextCursor, setNextCursor] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const mounted = useRef(false)
  const requestId = useRef(0)

  const load = useCallback(async (cursor?: string, append = false) => {
    const currentRequest = requestId.current
    if (!append) setLoading(true)
    setError(null)
    try {
      const params: Record<string, string | number> = { limit: 20 }
      if (status !== 'all') params.status = status
      if (appliedSearch) params.q = appliedSearch
      if (cursor) params.cursor = cursor
      const data: TaskListResponse = await fetchTasks(params as any)
      if (mounted.current && currentRequest === requestId.current) {
        setItems(prev => append ? [...prev, ...data.items] : data.items)
        setNextCursor(data.next_cursor)
      }
    } catch (cause) {
      if (mounted.current && currentRequest === requestId.current) {
        setError(cause instanceof Error ? cause.message : '加载任务列表失败')
      }
    } finally {
      if (mounted.current && currentRequest === requestId.current) setLoading(false)
    }
  }, [status, appliedSearch])

  // Reset on status/search change (skip initial — mount effect handles it)
  const isInitialMount = useRef(true)
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false
      return
    }
    requestId.current += 1
    setItems([])
    setNextCursor(null)
    void load()
  }, [load])

  // Mount/unmount lifecycle
  useEffect(() => {
    mounted.current = true
    void load()
    return () => {
      mounted.current = false
      requestId.current += 1
    }
  }, [])

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setAppliedSearch(search.trim())
  }

  const handleLoadMore = () => {
    if (nextCursor) void load(nextCursor, true)
  }

  return (
    <section className="page" aria-labelledby="tasks-title">
      <div className="page-head">
        <h1 className="page-title" id="tasks-title">任务队列</h1>
        <p className="page-desc">所有视频制作任务，按状态筛选和搜索。</p>
      </div>

      <div className="filter-row">
        <div className="status-tabs" role="tablist">
          {STATUS_TABS.map(t => (
            <button
              key={t.key}
              role="tab"
              aria-selected={status === t.key}
              className={`tab-btn ${status === t.key ? 'tab-btn--active' : ''}`}
              onClick={() => setStatus(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>
        <form className="search-form" onSubmit={handleSearchSubmit}>
          <input
            className="input"
            type="text"
            placeholder="搜索标题或 Task ID…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          <button className="btn btn-secondary" type="submit">搜索</button>
        </form>
        <Link to="/tasks/new" className="btn btn-primary">+ 新建任务</Link>
      </div>

      {loading && <TasksSkeleton />}
      {!loading && error && (
        <div className="error-card" role="alert">
          <p>加载失败：{error}</p>
          <button className="btn btn-secondary" type="button" onClick={() => void load()}>重新加载</button>
        </div>
      )}
      {!loading && !error && items.length === 0 && (
        <div className="empty-state">
          <div className="empty-illu">📭</div>
          <div className="empty-title">暂无任务</div>
          <div className="empty-sub">
            {status === 'all' && !appliedSearch
              ? '点击"新建任务"开始制作第一个视频'
              : '当前筛选条件下没有任务'}
          </div>
          {(status !== 'all' || appliedSearch) && (
            <button className="btn btn-secondary" style={{ marginTop: 8 }} onClick={() => { setStatus('all'); setSearch(''); setAppliedSearch('') }}>
              清除筛选
            </button>
          )}
        </div>
      )}

      {!loading && !error && items.length > 0 && (
        <div className="task-list">
          {items.map(t => (
            <TaskCard key={t.task_id} task={t} onOpen={() => navigate(`/tasks/${t.task_id}`)} />
          ))}
          {nextCursor && (
            <button className="btn btn-secondary" onClick={handleLoadMore} style={{ marginTop: 12 }}>
              加载更多
            </button>
          )}
          {!nextCursor && items.length > 0 && (
            <p className="list-end">已显示全部任务</p>
          )}
        </div>
      )}
    </section>
  )
}

function TaskCard({ task: t, onOpen }: { task: TaskQueueItem; onOpen: () => void }) {
  const hasRun = !!t.active_run
  const runId = t.active_run?.run_id
  const currentStage = t.active_run?.current_stage
  const finalAvailable = t.active_run?.final_available ?? false

  return (
    <article className="task-card">
      <div className="task-top">
        <h3 className="task-name">{t.title || `任务 ${shortId(t.task_id)}`}</h3>
        <StatusBadge status={t.status} />
        <span className="task-time">{formatTime(t.updated_at)}</span>
      </div>
      <div className="task-meta">
        <span className="m">ID: {shortId(t.task_id)}</span>
        {hasRun && currentStage && (
          <span className="m">当前阶段：{stageLabel(currentStage)}</span>
        )}
        {!hasRun && <span className="m task-meta--muted">尚未运行</span>}
      </div>
      <div className="task-actions">
        <button className="btn btn-primary btn-sm" onClick={onOpen}>
          进入工作台
        </button>
        {hasRun && runId && (
          <Link
            to={`/tasks/${encodeURIComponent(t.task_id)}/runs/${encodeURIComponent(runId)}/diagnostics`}
            className="btn btn-ghost btn-sm"
          >
            运行诊断
          </Link>
        )}
        {finalAvailable && runId && (
          <Link
            to={`/tasks/${encodeURIComponent(t.task_id)}/runs/${encodeURIComponent(runId)}/final`}
            className="btn btn-ghost btn-sm"
          >
            成片
          </Link>
        )}
      </div>
    </article>
  )
}
