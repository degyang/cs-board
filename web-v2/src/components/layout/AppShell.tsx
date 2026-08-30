import { Outlet } from 'react-router-dom'
import { useState, useCallback } from 'react'
import { Sidebar } from './Sidebar'

const PIN_KEY = 'mountain.ui.sidebarPinned'

export function AppShell() {
  const [pinned, setPinned] = useState(() => {
    try {
      return localStorage.getItem(PIN_KEY) === '1'
    } catch {
      return false
    }
  })

  const togglePin = useCallback(() => {
    setPinned((prev) => {
      const next = !prev
      try {
        localStorage.setItem(PIN_KEY, next ? '1' : '0')
      } catch {
        // ignore
      }
      return next
    })
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
