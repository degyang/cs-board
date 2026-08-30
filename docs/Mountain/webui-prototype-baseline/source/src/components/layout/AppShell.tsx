import { Outlet } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Sidebar } from './Sidebar'

const PIN_KEY = 'mountain.ui.sidebarPinned'

function readPinned(): boolean {
  // 默认钉住：侧边栏常驻展开（与既有行为一致），取消钉住后才进入图标栏模式
  try {
    const v = localStorage.getItem(PIN_KEY)
    return v === null ? true : v === '1'
  } catch {
    return true
  }
}

export function AppShell() {
  const [pinned, setPinned] = useState<boolean>(readPinned)

  useEffect(() => {
    try {
      localStorage.setItem(PIN_KEY, pinned ? '1' : '0')
    } catch {
      /* localStorage 不可用时忽略，仅本次会话生效 */
    }
  }, [pinned])

  return (
    <div className={`app-shell ${pinned ? 'is-pinned' : 'is-rail'}`}>
      <Sidebar pinned={pinned} onTogglePin={() => setPinned((p) => !p)} />
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}

