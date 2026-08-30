import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { useCurrentRun } from '../../app/providers'
import { STAGE_NAMES } from '../../lib/api/types'

const IcoPlus = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
  </svg>
)
const IcoGear = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <circle cx="8" cy="8" r="2.4" stroke="currentColor" strokeWidth="1.4" />
    <path d="M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M12.6 3.4l-1.4 1.4M4.8 11.2l-1.4 1.4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
  </svg>
)
const IcoHelp = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M6 6a2 2 0 1 1 2.6 1.9c-.6.2-1 .8-1 1.4v.4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    <circle cx="7.6" cy="12.4" r="0.9" fill="currentColor" />
    <circle cx="8" cy="8" r="6.6" stroke="currentColor" strokeWidth="1.3" />
  </svg>
)
const IcoAssets = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M2 5l6-3 6 3-6 3-6-3z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
    <path d="M2 8l6 3 6-3M2 11l6 3 6-3" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
  </svg>
)
const IcoQueue = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <rect x="2.5" y="3" width="11" height="2.2" rx="1.1" stroke="currentColor" strokeWidth="1.4" />
    <rect x="2.5" y="7" width="11" height="2.2" rx="1.1" stroke="currentColor" strokeWidth="1.4" />
    <rect x="2.5" y="11" width="7.5" height="2.2" rx="1.1" stroke="currentColor" strokeWidth="1.4" />
  </svg>
)
const IcoPin = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M16,9V4l1,0c0.55,0,1-0.45,1-1v0c0-0.55-0.45-1-1-1H7C6.45,2,6,2.45,6,3v0 c0,0.55,0.45,1,1,1l1,0v5c0,1.66-1.34,3-3,3h0v2h5.97v7l1,1l1-1v-7H19v-2h0 C17.34,12,16,10.66,16,9z" />
  </svg>
)

const NAV_ITEMS = [
  { to: '/create', label: '新建任务', icon: <IcoPlus /> },
  { to: '/projects', label: '任务队列', icon: <IcoQueue /> },
  { to: '/assets', label: '资产管理', icon: <IcoAssets /> },
  { to: '/settings', label: '设置', icon: <IcoGear /> },
  { to: '/help', label: '帮助', icon: <IcoHelp /> },
]

interface SidebarProps {
  /** 钉住：侧边栏常驻展开，不折叠不隐藏 */
  pinned: boolean
  onTogglePin: () => void
}

export function Sidebar({ pinned, onTogglePin }: SidebarProps) {
  const run = useCurrentRun()
  const rail = !pinned
  const [peek, setPeek] = useState(false)
  // 简化且零抖动的展开策略：
  //  · 唯一的展开触发源是「品牌区 .brand」——即「山」图标及其下方分隔线这一整块，鼠标停留其上才展开整栏。
  //  · 其余一切（导航图标、空白、Run 条）都保持 64px 隐藏栏，不会触发展开，且图标可点击。
  //  · 鼠标离开整个侧边栏才收起（onMouseLeave）。
  // 只用一个 onMouseEnter（穿过边界触发一次、不随布局重排反复 firing）+ onMouseLeave，彻底避免 64↔264 抖动。
  const expand = () => { if (rail) setPeek(true) }
  const collapse = () => setPeek(false)
  return (
    <aside
      className={`sidebar${peek ? ' rail-peeking' : ''}`}
      data-pinned={pinned}
      onMouseLeave={collapse}
    >
      <div className="brand" onMouseEnter={expand}>
        <div className="brand-row">
          <div className="brand-mark" title="山野小读 Mountain Studio">山</div>
          <div className="brand-text">
            <h1 className="brand-name">山野小读</h1>
            <div className="brand-sub">Mountain Studio</div>
          </div>
          {/* 图钉按钮在 brand 区右侧；rail 模式默认隐藏，悬停展开浮层时可见 */}
          <button
            type="button"
            className={`pin-btn${pinned ? ' on' : ''}`}
            onClick={onTogglePin}
            title={pinned ? '已钉住：侧边栏常驻展开。点击取消钉住，收起为图标栏' : '未钉住：侧边栏收起为图标栏，悬停临时展开。点击钉住，常驻展开不再隐藏'}
            aria-pressed={pinned}
            aria-label={pinned ? '取消钉住侧边栏' : '钉住侧边栏'}
          >
            <IcoPin />
          </button>
        </div>
        {/* 视觉提示分隔线：整块品牌区（山 + 此分隔线）悬停即展开；钉住模式下隐藏 */}
        <div className="rail-handle" title="悬停品牌区展开导航" />
      </div>
      <nav className="nav">
        {NAV_ITEMS.map((item) => (
          <NavLink key={item.to} to={item.to} title={item.label}>
            <span className="nav-ico">{item.icon}</span>
            <span className="lbl">{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">
        {run ? (
          <Link className="runbar" to={`/projects/${run.project_id}`} title="进入工作台">
            <span className="dot" />
            <span>
              {run.project_name} · {STAGE_NAMES[run.current_stage]}
            </span>
          </Link>
        ) : (
          <div style={{ marginBottom: 10 }}>当前无运行中的任务</div>
        )}
        <div className="pipeline-note">pipeline mountain-av-v1 · WebUI v2</div>
      </div>
    </aside>
  )
}

