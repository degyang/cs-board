import { Outlet } from 'react-router-dom'
import { useState, useCallback } from 'react'
import { Sidebar } from './Sidebar'

const PIN_KEY = 'mountain.ui.sidebarPinned'

export function AppShell() {
  const [pinned, setPinned] = useState(() => {
    try {
      // Full sidebar is the product default. Only an explicit user choice of
      // "0" switches to the compact rail.
      return localStorage.getItem(PIN_KEY) !== '0'
    } catch {
      return true
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
