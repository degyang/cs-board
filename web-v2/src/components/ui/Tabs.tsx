import { useRef } from 'react'

export interface TabItem {
  key: string
  label: string
  count?: number
}

export function Tabs({
  items,
  active,
  onChange,
}: {
  items: TabItem[]
  active: string
  onChange: (key: string) => void
}) {
  const keys = items.map((item) => item.key)
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({})
  function move(current: string, direction: number) {
    const index = keys.indexOf(current)
    const next = direction === -Infinity ? 0 : direction === Infinity ? keys.length - 1 : (index + direction + keys.length) % keys.length
    onChange(keys[next])
    tabRefs.current[keys[next]]?.focus()
  }
  return (
    <div className="tabs-bar" role="tablist">
      {items.map((t) => (
        <button
          key={t.key}
          id={`tab-${t.key}`}
          type="button"
          role="tab"
          aria-selected={t.key === active}
          aria-controls={`tab-panel-${t.key}`}
          tabIndex={t.key === active ? 0 : -1}
          className={'tab-btn' + (t.key === active ? ' on' : '')}
          ref={(element) => { tabRefs.current[t.key] = element }}
          onClick={() => onChange(t.key)}
          onKeyDown={(event) => {
            if (event.key === 'ArrowRight') move(t.key, 1)
            else if (event.key === 'ArrowLeft') move(t.key, -1)
            else if (event.key === 'Home') move(t.key, -Infinity)
            else if (event.key === 'End') move(t.key, Infinity)
          }}
        >
          {t.label}
          {typeof t.count === 'number' && <span className="tab-count">{t.count}</span>}
        </button>
      ))}
    </div>
  )
}
