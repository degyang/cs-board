import { NavLink, Outlet, useLocation } from 'react-router-dom'

const NAV_ITEMS = [
  { group: '项目', items: [
    { to: '/', label: '项目列表', icon: '📋' },
    { to: '/projects/new', label: '创建项目', icon: '➕' },
    { to: '#', label: '制作工作台', icon: '🎬', disabled: true },
  ]},
  { group: '设置', items: [
    { to: '/settings/providers', label: 'Provider 配置', icon: '⚙️' },
  ]},
  { group: '诊断', items: [
    { to: '#', label: '诊断', icon: '📊', disabled: true },
  ]},
]

export function AppShell() {
  const location = useLocation()

  // Generate breadcrumbs from location
  const crumbs = generateCrumbs(location.pathname)

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-row">
            <div className="brand-mark">山</div>
            <div className="brand-text">
              <p className="brand-name">Mountain</p>
              <div className="brand-sub">山野小读</div>
            </div>
          </div>
        </div>

        <nav className="nav">
          {NAV_ITEMS.map((group) => (
            <div key={group.group}>
              <div className="nav-group-label">{group.group}</div>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.disabled ? '#' : item.to}
                  end={item.to === '/'}
                  className={({ isActive }) =>
                    [
                      isActive && item.to !== '#' ? 'active' : '',
                      item.disabled ? 'disabled' : '',
                    ].filter(Boolean).join(' ')
                  }
                  onClick={item.disabled ? (e) => e.preventDefault() : undefined}
                >
                  <span className="nav-ico">{item.icon}</span>
                  <span className="lbl">{item.label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div style={{ fontSize: 11, color: 'var(--nt-text-muted)' }}>
            CS-Board v0.1.0
          </div>
        </div>
      </aside>

      <main className="main">
        <div className="topbar">
          <div className="crumb">
            <NavLink to="/">首页</NavLink>
            {crumbs.map((crumb, i) => (
              <span key={i}>
                <span style={{ margin: '0 4px' }}>/</span>
                {crumb.to ? <NavLink to={crumb.to}>{crumb.label}</NavLink> : crumb.label}
              </span>
            ))}
          </div>
        </div>
        <Outlet />
      </main>
    </div>
  )
}

interface Crumb {
  label: string
  to?: string
}

function generateCrumbs(pathname: string): Crumb[] {
  const crumbs: Crumb[] = []

  if (pathname === '/') {
    crumbs.push({ label: '项目列表' })
  } else if (pathname === '/projects/new') {
    crumbs.push({ label: '项目列表', to: '/' })
    crumbs.push({ label: '创建项目' })
  } else if (pathname.startsWith('/projects/')) {
    const id = pathname.split('/')[2]
    crumbs.push({ label: '项目列表', to: '/' })
    crumbs.push({ label: `项目 ${id?.slice(0, 8)}` })
  } else if (pathname === '/settings/providers') {
    crumbs.push({ label: 'Provider 配置' })
  } else if (pathname.startsWith('/settings/providers/')) {
    const name = pathname.split('/')[3]
    crumbs.push({ label: 'Provider 配置', to: '/settings/providers' })
    crumbs.push({ label: name ?? '' })
  }

  return crumbs
}
