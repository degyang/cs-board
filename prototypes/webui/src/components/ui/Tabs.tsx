export interface TabItem {
  key: string
  label: string
  count?: number
}

// Tabs 组件：仅用于页面内切换局部上下文（项目状态过滤、活动与诊断四页签、设置分页）
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

