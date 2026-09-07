/* ==========================================================================
   应用级 Provider 组合层（全局 Context + Query Provider）
   ========================================================================== */

import { useState, useEffect, useCallback, createContext, useContext, type ReactNode } from 'react'
import type { HealthResponse } from '../lib/api/types'
import { fetchHealth, MountainApiError } from '../lib/api/client'

/** 全局应用状态 */
export interface AppState {
  health: HealthResponse | null
  healthError: string | null
  healthLoading: boolean
  refreshHealth: () => void
}

const defaultState: AppState = {
  health: null,
  healthError: null,
  healthLoading: true,
  refreshHealth: () => {},
}

const AppContext = createContext<AppState>(defaultState)

export function useAppState(): AppState {
  return useContext(AppContext)
}

export function AppProviders({ children }: { children: ReactNode }) {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)
  const [healthLoading, setHealthLoading] = useState(true)

  const loadHealth = useCallback(async () => {
    try {
      setHealthLoading(true)
      setHealthError(null)
      const data = await fetchHealth()
      setHealth(data)
    } catch (err) {
      if (err instanceof MountainApiError) {
        setHealthError(err.apiError?.message ?? err.message)
      } else {
        setHealthError(err instanceof Error ? err.message : '未知错误')
      }
    } finally {
      setHealthLoading(false)
    }
  }, [])

  useEffect(() => {
    loadHealth()
    const t = setInterval(loadHealth, 30_000)
    return () => clearInterval(t)
  }, [loadHealth])

  return (
    <AppContext.Provider
      value={{
        health,
        healthError,
        healthLoading,
        refreshHealth: loadHealth,
      }}
    >
      {children}
    </AppContext.Provider>
  )
}
