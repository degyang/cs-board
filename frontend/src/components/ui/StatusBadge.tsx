import { statusText } from '../../lib/formatting'

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  return (
    <span className={'badge st-' + status}>
      <span className="dot" />
      {label ?? statusText(status)}
    </span>
  )
}
