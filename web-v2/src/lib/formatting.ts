/* ==========================================================================
   Formatting utilities
   ========================================================================== */

/** Format ISO timestamp to readable local string */
export function formatTime(iso: string): string {
  try {
    const d = new Date(iso)
    if (isNaN(d.getTime())) return iso
    return d.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

/** Shorten ID to first N chars */
export function shortId(id: string, len = 8): string {
  return id.length > len ? id.slice(0, len) + '…' : id
}

/** Status display text */
export function statusText(status: string): string {
  const map: Record<string, string> = {
    pending: '待处理',
    running: '进行中',
    succeeded: '已完成',
    failed: '失败',
    cancelled: '已取消',
    ready: '就绪',
  }
  return map[status] ?? status
}

/** Status badge class */
export function statusClass(status: string): string {
  const map: Record<string, string> = {
    pending: 'st-pending',
    running: 'st-running',
    succeeded: 'st-succeeded',
    failed: 'st-failed',
    cancelled: 'st-cancelled',
    ready: 'st-pending',
  }
  return map[status] ?? 'st-pending'
}
