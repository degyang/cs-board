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
  return (
    <div className="tabs-bar" role="tablist">
      {items.map((t) => (
        <button
          key={t.key}
          type="button"
          role="tab"
          aria-selected={t.key === active}
          className={'tab-btn' + (t.key === active ? ' on' : '')}
          onClick={() => onChange(t.key)}
        >
          {t.label}
          {typeof t.count === 'number' && <span className="tab-count">{t.count}</span>}
        </button>
      ))}
    </div>
  )
}
