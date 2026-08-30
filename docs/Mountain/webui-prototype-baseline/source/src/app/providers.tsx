import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { fetchCurrentRun } from '../lib/api/client'
import type { CurrentRunInfo } from '../lib/api/types'

// 全局上下文：当前 Run 状态条（侧边栏底部展示），与页面数据互不重复轮询
const CurrentRunContext = createContext<CurrentRunInfo | null>(null)

export function AppProviders({ children }: { children: ReactNode }) {
  const [run, setRun] = useState<CurrentRunInfo | null>(null)
  useEffect(() => {
    let alive = true
    fetchCurrentRun().then((r) => {
      if (alive) setRun(r)
    })
    return () => {
      alive = false
    }
  }, [])
  return <CurrentRunContext.Provider value={run}>{children}</CurrentRunContext.Provider>
}

export function useCurrentRun(): CurrentRunInfo | null {
  return useContext(CurrentRunContext)
}

