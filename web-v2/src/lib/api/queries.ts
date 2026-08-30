import { useEffect, useState } from 'react'

export interface AsyncState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

export function useAsync<T>(loader: () => Promise<T>, deps: unknown[] = [], pollMs?: number): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout> | undefined

    const load = async () => {
      try {
        const d = await loader()
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
  }, deps)

  return { data, loading, error }
}
