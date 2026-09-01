/* ==========================================================================
   Settings Layout — shared tab navigation for all /settings/* routes.
   Uses <Outlet /> to render child route pages.
   ========================================================================== */

import { NavLink, Outlet } from 'react-router-dom'

const SETTINGS_TABS = [
  { to: '/settings/models', label: '模型服务' },
  { to: '/settings/voice-alignment', label: '语音与对齐' },
  { to: '/settings/toolchain', label: '工具链' },
  { to: '/settings/storage', label: '存储' },
  { to: '/settings/diagnostics', label: '诊断' },
]

export function SettingsLayout() {
  return (
    <div className="page">
      <div className="page-head">
        <h1 className="page-title">设置</h1>
        <p className="page-desc">管理系统服务和配置</p>
      </div>

      <div className="set-tabs">
        {SETTINGS_TABS.map(tab => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) => `set-tab-btn${isActive ? ' active' : ''}`}
          >
            {tab.label}
          </NavLink>
        ))}
      </div>

      <div className="set-content">
        <Outlet />
      </div>
    </div>
  )
}
