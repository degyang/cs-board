import { NavLink } from 'react-router-dom'
import { useEffect, useState, useCallback } from 'react'
import { fetchTasks } from '../../lib/api/client'
import { statusText } from '../../lib/formatting'

export function Sidebar({ pinned, onTogglePin }: { pinned: boolean; onTogglePin: () => void }) {
  const [runInfo, setRunInfo] = useState<{ title: string; status: string } | null>(null)

  const loadRunInfo = useCallback(async () => {
    try {
      const { items } = await fetchTasks({ limit: 20 })
      const running = items.find((t) => t.status === 'running')
      setRunInfo(running ? { title: running.title, status: running.status } : null)
    } catch {
      // ignore — footer is non-critical
    }
  }, [])

  useEffect(() => {
    loadRunInfo()
    const t = setInterval(loadRunInfo, 30_000)
    return () => clearInterval(t)
  }, [loadRunInfo])

  return (
    <aside className="sidebar">
      <button className="pin-btn" onClick={onTogglePin} title={pinned ? '取消固定' : '固定侧栏'}>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path
            d="M11.5 1.5L14.5 4.5L10 9L9 14L8 14L7 9L2.5 4.5L5.5 1.5L8 3L11.5 1.5Z"
            stroke="currentColor"
            strokeWidth="1.2"
            fill={pinned ? 'currentColor' : 'none'}
          />
        </svg>
      </button>

      <div className="brand">
        <div className="brand-row">
          <div className="brand-mark">M</div>
          <div>
            <p className="brand-name">山野小读</p>
            <p className="brand-sub">Video Pipeline</p>
          </div>
        </div>
      </div>

      <nav className="nav">
        <p className="nav-group-label">任务</p>
        <NavLink to="/" end>
          <span className="nav-ico">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M3 4h12M3 9h12M3 14h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </span>
          <span>任务队列</span>
        </NavLink>
        <NavLink to="/tasks/new">
          <span className="nav-ico">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M9 3v12M3 9h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </span>
          <span>新建任务</span>
        </NavLink>

        <p className="nav-group-label">系统</p>
        <NavLink to="/settings/providers">
          <span className="nav-ico">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <circle cx="9" cy="9" r="3" stroke="currentColor" strokeWidth="1.5" />
              <path d="M9 1v2M9 15v2M1 9h2M15 9h2M3.3 3.3l1.4 1.4M13.3 13.3l1.4 1.4M3.3 14.7l1.4-1.4M13.3 4.7l1.4-1.4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </span>
          <span>设置</span>
        </NavLink>
        <NavLink to="/help">
          <span className="nav-ico">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <circle cx="9" cy="9" r="7" stroke="currentColor" strokeWidth="1.5" />
              <path d="M7 7a2 2 0 114 0c0 1.5-2 1.5-2 3M9 13h.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </span>
          <span>帮助</span>
        </NavLink>
      </nav>

      <div className="sidebar-footer">
        {runInfo ? (
          <div className="sidebar-footer-run">
            <span className="dot" />
            <span>
              {runInfo.title} — {statusText(runInfo.status)}
            </span>
          </div>
        ) : (
          <span style={{ color: 'var(--nt-text-muted)', fontSize: 12 }}>
            v2.0 — powered by Vite
          </span>
        )}
      </div>
    </aside>
  )
}
