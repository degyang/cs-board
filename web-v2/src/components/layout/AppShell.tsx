import { Outlet } from 'react-router-dom'
import { useState, useCallback, useEffect } from 'react'
import { Sidebar } from './Sidebar'

const PIN_KEY = 'mountain.ui.sidebarPinned'

export function AppShell() {
  const [pinned, setPinned] = useState(() => {
    try {
      const value = localStorage.getItem(PIN_KEY)
      return value === null ? true : value === '1'
    } catch {
      return true
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem(PIN_KEY, pinned ? '1' : '0')
    } catch {
      /* localStorage 不可用时忽略，仅本次会话生效 */
    }
  }, [pinned])

  const togglePin = useCallback(() => {
    setPinned((prev) => !prev)
  }, [])

  const shellClass = ['app-shell', pinned ? 'is-pinned' : 'is-rail'].join(' ')

  return (
    <div className={shellClass}>
      <Sidebar pinned={pinned} onTogglePin={togglePin} />
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
