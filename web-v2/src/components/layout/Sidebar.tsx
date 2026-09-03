import { Link, NavLink } from 'react-router-dom'
import { useEffect, useState, useCallback } from 'react'
import { fetchTasks } from '../../lib/api/tasks'
import { statusText } from '../../lib/formatting'

export function Sidebar({ pinned, onTogglePin }: { pinned: boolean; onTogglePin: () => void }) {
  const [runInfo, setRunInfo] = useState<{ taskId: string; title: string; status: string } | null>(null)
  const [peek, setPeek] = useState(false)
  const rail = !pinned

  const loadRunInfo = useCallback(async (signal: AbortSignal) => {
    try {
      const tasks = await fetchTasks(signal)
      if (signal.aborted) return
      const running = tasks.find((t) => t.status === 'running')
      setRunInfo(
        running
          ? {
              taskId: running.task_id,
              title: running.title,
              status: running.status,
            }
          : null,
      )
    } catch {
      // ignore — footer is non-critical
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    void loadRunInfo(controller.signal)
    const t = setInterval(() => void loadRunInfo(controller.signal), 30_000)
    return () => {
      controller.abort()
      clearInterval(t)
    }
  }, [loadRunInfo])

  useEffect(() => {
    if (pinned) {
      setPeek(false)
    }
  }, [pinned])

  const expand = () => {
    if (rail) {
      setPeek(true)
    }
  }
  const collapse = () => {
    if (rail) {
      setPeek(false)
    }
  }

  return (
    <aside
      id="mountain-sidebar"
      className={`sidebar${peek ? ' rail-peeking' : ''}`}
      data-pinned={pinned}
      aria-label="山野小读侧边栏"
      onMouseLeave={collapse}
    >
      <div className="brand">
        <div className="brand-row">
          <button
            type="button"
            className="brand-mark"
            onMouseEnter={expand}
            onFocus={expand}
            onClick={expand}
            aria-label={rail ? '展开侧边栏' : '山野小读'}
            aria-expanded={rail ? peek : undefined}
            aria-controls="mountain-sidebar"
            title={rail ? '悬停或聚焦展开侧边栏' : '山野小读'}
          >
            山
          </button>
          <div>
            <p className="brand-name">山野小读</p>
            <p className="brand-sub">Video Pipeline</p>
          </div>
          <button
            type="button"
            className={`pin-btn${pinned ? ' on' : ''}`}
            onClick={() => {
              setPeek(false)
              onTogglePin()
            }}
            title={pinned ? '已钉住：侧边栏常驻展开。点击取消钉住，收起为图标栏' : '未钉住：侧边栏收起为图标栏，悬停临时展开。点击钉住，常驻展开不再隐藏'}
            aria-pressed={pinned}
            aria-label={pinned ? '取消钉住侧边栏' : '钉住侧边栏'}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path
                d="M11.5 1.5L14.5 4.5L10 9L9 14L8 14L7 9L2.5 4.5L5.5 1.5L8 3L11.5 1.5Z"
                stroke="currentColor"
                strokeWidth="1.2"
                fill={pinned ? 'currentColor' : 'none'}
              />
            </svg>
          </button>
        </div>
        <button
          type="button"
          className="rail-handle"
          onMouseEnter={expand}
          onFocus={expand}
          onClick={expand}
          aria-label="展开侧边栏"
          aria-expanded={peek}
          aria-controls="mountain-sidebar"
          title="悬停或聚焦展开侧边栏"
        />
      </div>

      <nav className="nav" aria-label="主导航">
        <p className="nav-group-label">任务</p>
        <NavLink to="/" end title="任务队列" aria-label="任务队列">
          <span className="nav-ico">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M3 4h12M3 9h12M3 14h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </span>
          <span className="lbl">任务队列</span>
        </NavLink>
        <NavLink to="/tasks/new" title="新建任务" aria-label="新建任务">
          <span className="nav-ico">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M9 3v12M3 9h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </span>
          <span className="lbl">新建任务</span>
        </NavLink>

        <p className="nav-group-label">素材</p>
        <NavLink to="/assets" title="素材管理" aria-label="素材管理">
          <span className="nav-ico">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <rect x="3" y="3" width="12" height="12" rx="2" stroke="currentColor" strokeWidth="1.5" />
              <path d="M3 12l3-3 2 2 4-4 3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
          <span className="lbl">素材管理</span>
        </NavLink>

        <p className="nav-group-label">系统</p>
        <NavLink to="/settings" title="设置" aria-label="设置">
          <span className="nav-ico">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <circle cx="9" cy="9" r="3" stroke="currentColor" strokeWidth="1.5" />
              <path d="M9 1v2M9 15v2M1 9h2M15 9h2M3.3 3.3l1.4 1.4M13.3 13.3l1.4 1.4M3.3 14.7l1.4-1.4M13.3 4.7l1.4-1.4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </span>
          <span className="lbl">设置</span>
        </NavLink>
        <NavLink to="/help" title="帮助" aria-label="帮助">
          <span className="nav-ico">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <circle cx="9" cy="9" r="7" stroke="currentColor" strokeWidth="1.5" />
              <path d="M7 7a2 2 0 114 0c0 1.5-2 1.5-2 3M9 13h.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </span>
          <span className="lbl">帮助</span>
        </NavLink>
      </nav>

      <div className="sidebar-footer">
        {runInfo ? (
          <Link
            className="runbar"
            to={`/tasks/${runInfo.taskId}`}
            title="进入工作台"
          >
            <span className="dot" />
            <span>
              {runInfo.title} — {statusText(runInfo.status)}
            </span>
          </Link>
        ) : (
          <div className="runbar">
            <span className="dot" />
            <span>v2.0 — powered by Vite</span>
          </div>
        )}
      </div>
    </aside>
  )
}
