/* ==========================================================================
   任务队列 — real task queue backed by GET /api/v1/tasks
   ========================================================================== */

import { useEffect, useRef, useState, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { fetchTasks, getFinalUrl } from '../lib/api/client'
import { formatTime, shortId } from '../lib/formatting'
import { StatusBadge } from '../components/ui/StatusBadge'
import { Tabs } from '../components/ui/Tabs'
import { STAGE_NAMES } from '../lib/api/types'
import type { TaskQueueItem, TaskListResponse } from '../lib/api/types'

const STATUS_TABS = [
  { key: 'all', label: '全部' },
  { key: 'running', label: '进行中' },
  { key: 'succeeded', label: '已完成' },
  { key: 'failed', label: '失败' },
  { key: 'cancelled', label: '已取消' },
  { key: 'pending', label: '待执行' },
]

function stageLabel(stage: string | null | undefined): string {
  if (!stage) return ''
  return STAGE_NAMES[stage as keyof typeof STAGE_NAMES] ?? stage
}

function runStatusLabel(status: string): string {
  const map: Record<string, string> = {
    running: '运行中',
    succeeded: '已完成',
    failed: '失败',
    cancelled: '已取消',
    pending: '待执行',
  }
  return map[status] ?? status
}

/** Encode task/run IDs for URL path segments. */
function encodeId(id: string): string {
  return encodeURIComponent(id)
}

function taskWorkbenchPath(taskId: string): string {
  return `/tasks/${encodeId(taskId)}`
}

function runDiagnosticsPath(taskId: string, runId: string): string {
  return `/tasks/${encodeId(taskId)}/runs/${encodeId(runId)}/diagnostics`
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
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pageError, setPageError] = useState<string | null>(null)
  const mounted = useRef(false)
  const generation = useRef(0)
  const pendingCursor = useRef<string | null>(null)

  const load = useCallback(async (cursor?: string, append = false) => {
    // Prevent duplicate cursor requests
    if (append && cursor && pendingCursor.current === cursor) return
    if (append) pendingCursor.current = cursor ?? null

    const gen = generation.current
    if (append) {
      setLoadingMore(true)
      setPageError(null)
    } else {
      setLoading(true)
      setError(null)
      setPageError(null)
    }
    try {
      const params: Record<string, string | number> = { limit: 20 }
      if (status !== 'all') params.status = status
      if (appliedSearch) params.q = appliedSearch
      if (cursor) params.cursor = cursor
      const data: TaskListResponse = await fetchTasks(params as any)
      if (mounted.current && gen === generation.current) {
        if (append) {
          // Dedup by task_id, preserve server order
          setItems(prev => {
            const seen = new Set(prev.map(t => t.task_id))
            const newItems = data.items.filter(t => !seen.has(t.task_id))
            return [...prev, ...newItems]
          })
        } else {
          setItems(data.items)
        }
        setNextCursor(data.next_cursor)
      }
    } catch (cause) {
      if (mounted.current && gen === generation.current) {
        const msg = cause instanceof Error ? cause.message : '加载任务列表失败'
        if (append) {
          // Pagination failure: keep existing items, show local error
          setPageError(msg)
        } else {
          setError(msg)
        }
      }
    } finally {
      if (mounted.current && gen === generation.current) {
        if (append) {
          setLoadingMore(false)
          pendingCursor.current = null
        } else {
          setLoading(false)
        }
      }
    }
  }, [status, appliedSearch])

  // Reset on status/search change (skip initial — mount effect handles it)
  const isInitialMount = useRef(true)
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false
      return
    }
    generation.current += 1
    setItems([])
    setNextCursor(null)
    pendingCursor.current = null
    void load()
  }, [load])

  // Mount/unmount lifecycle
  useEffect(() => {
    mounted.current = true
    void load()
    return () => {
      mounted.current = false
      generation.current += 1
    }
  }, [])

  // Debounced search: 300ms delay after typing stops
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const applySearch = useCallback((value: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setAppliedSearch(value.trim())
    }, 300)
  }, [])

  useEffect(() => () => { if (debounceRef.current) clearTimeout(debounceRef.current) }, [])

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (debounceRef.current) clearTimeout(debounceRef.current)
      setAppliedSearch(search.trim())
    }
  }

  const handleLoadMore = () => {
    if (nextCursor && !loadingMore) void load(nextCursor, true)
  }

  return (
    <section className="page" aria-labelledby="tasks-title">
      <div className="page-head">
        <h1 className="page-title" id="tasks-title">任务队列</h1>
        <p className="page-desc">查看制作任务、当前工序、状态和最终成果。</p>
      </div>

      <div className="filter-row">
        <div className="search">
          <input
            className="input"
            style={{ borderRadius: 'var(--nt-radius-full)', paddingLeft: 16 }}
            placeholder="搜索任务名…"
            value={search}
            onChange={e => { setSearch(e.target.value); applySearch(e.target.value) }}
            onKeyDown={handleSearchKeyDown}
          />
        </div>
      </div>

      <Tabs items={STATUS_TABS} active={status} onChange={setStatus} />

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
              ? '还没有制作任务'
              : '当前筛选下没有任务'}
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
            <TaskCard
              key={t.task_id}
              task={t}
              onOpen={() => navigate(taskWorkbenchPath(t.task_id))}
            />
          ))}
          {nextCursor && (
            <div className="load-more-row">
              <button
                className="btn btn-secondary"
                onClick={handleLoadMore}
                disabled={loadingMore}
                style={{ marginTop: 12 }}
              >
                {loadingMore ? '加载中…' : '加载更多'}
              </button>
              {pageError && (
                <p className="page-error" role="alert">
                  加载下一页失败：{pageError}
                  <button className="btn btn-link" onClick={handleLoadMore}>重试</button>
                </p>
              )}
            </div>
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
  const runStatus = t.active_run?.status
  const currentStage = t.active_run?.current_stage
  const retryable = t.active_run?.retryable ?? false
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
        {hasRun && runStatus && (
          <span className="m">
            运行状态：<StatusBadge status={runStatus} label={runStatusLabel(runStatus)} />
          </span>
        )}
        {hasRun && currentStage && (
          <span className="m">当前阶段：{stageLabel(currentStage)}</span>
        )}
        {hasRun && retryable && (
          <span className="m task-meta--hint">可重试</span>
        )}
        {!hasRun && <span className="m task-meta--muted">尚未运行</span>}
      </div>
      <div className="task-actions">
        <button className="btn btn-primary btn-sm" onClick={onOpen}>
          进入工作台
        </button>
        {hasRun && runId && (
          <Link
            to={runDiagnosticsPath(t.task_id, runId)}
            className="btn btn-ghost btn-sm"
          >
            运行诊断
          </Link>
        )}
        {finalAvailable && runId && (
          <a
            href={getFinalUrl(t.task_id, runId)}
            className="btn btn-ghost btn-sm"
            target="_blank"
            rel="noopener noreferrer"
          >
            成片
          </a>
        )}
      </div>
    </article>
  )
}
