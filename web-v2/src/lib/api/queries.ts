import { useEffect, useState, useCallback, useRef } from 'react'

export interface AsyncState<T> {
  data: T | null
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useAsync<T>(loader: () => Promise<T>, deps: unknown[] = [], pollMs?: number): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [trigger, setTrigger] = useState(0)
  const loaderRef = useRef(loader)
  loaderRef.current = loader

  const refetch = useCallback(() => setTrigger((n) => n + 1), [])

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout> | undefined

    const load = async () => {
      try {
        const d = await loaderRef.current()
        if (!alive) return
        setData(d)
        setError(null)
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : String(e))
      } finally {
        if (alive) setLoading(false)
      }
      if (alive && pollMs) {
        timer = setTimeout(load, pollMs)
      }
    }
    load()
    return () => {
      alive = false
      if (timer) clearTimeout(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, trigger])

  return { data, loading, error, refetch }
}
