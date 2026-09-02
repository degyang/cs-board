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
  const previousDepsRef = useRef<unknown[] | null>(null)
  const previousPollMsRef = useRef<number | undefined>(undefined)
  const loaderRef = useRef(loader)
  loaderRef.current = loader

  // A dependency change starts a new identity. Hide the previous result
  // synchronously during the render that observes the change; the effect
  // below then clears it and starts the new request. This prevents a route
  // transition from briefly showing data owned by the previous resource.
  const depsChanged = previousDepsRef.current === null
    || deps.length !== previousDepsRef.current.length
    || deps.some((value, index) => !Object.is(value, previousDepsRef.current?.[index]))
  if (depsChanged) previousDepsRef.current = deps
  const pollStopped = previousPollMsRef.current !== undefined && pollMs === undefined
  previousPollMsRef.current = pollMs

  const refetch = useCallback(() => setTrigger((n) => n + 1), [])

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout> | undefined

    // Drop the previous identity's state before starting this request. The
    // render-time guard above covers the transition frame; this keeps it
    // cleared while a slow successor is still pending. A poll stop is only a
    // timer lifecycle change and must not trigger another network request.
    if (depsChanged) {
      setData(null)
      setError(null)
      setLoading(true)
    }

    if (pollStopped) return () => {
      alive = false
      if (timer) clearTimeout(timer)
    }

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
  }, [...deps, trigger, pollMs])

  return {
    data: depsChanged ? null : data,
    loading: depsChanged ? true : loading,
    error: depsChanged ? null : error,
    refetch,
  }
}
