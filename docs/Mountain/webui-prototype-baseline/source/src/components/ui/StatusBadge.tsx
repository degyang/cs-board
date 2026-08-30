const STATUS_TEXT: Record<string, string> = {
  pending: '待执行',
  running: '运行中',
  succeeded: '已成功',
  failed: '失败',
  cancelled: '已取消',
  stale: '已过期',
  skipped: '已跳过',
}

export function statusText(status: string): string {
  return STATUS_TEXT[status] ?? status
}

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  return (
    <span className={'badge st-' + status}>
      <span className="dot" />
      {label ?? statusText(status)}
    </span>
  )
}

