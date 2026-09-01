/* ==========================================================================
   Formatting utilities
   ========================================================================== */

export function formatBytes(n?: number): string {
  if (!n || n <= 0) return '—'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`
}

export function formatSeconds(s?: number): string {
  if (s == null || s <= 0) return '—'
  if (s < 60) return `${s.toFixed(1)}s`
  const m = Math.floor(s / 60)
  const rest = Math.round(s % 60)
  if (m < 60) return `${m}m${rest.toString().padStart(2, '0')}s`
  return `${Math.floor(m / 60)}h${(m % 60).toString().padStart(2, '0')}m`
}

export function formatMs(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`
}

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

export function formatClock(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleTimeString('zh-CN', { hour12: false })
}

/** Shorten ID to first N chars */
export function shortId(id: string, len = 8): string {
  return id.length > len ? id.slice(0, len) + '…' : id
}

export function percent(ratio: number): string {
  return `${(ratio * 100).toFixed(1)}%`
}

/** Check if a byte value is safe to display (not null, finite, non-negative) */
export function hasValidCapacity(bytes: number | null | undefined): bytes is number {
  return bytes != null && Number.isFinite(bytes) && bytes >= 0
}

/** Format bytes with safe fallback for null/NaN/Infinity/negative → "未统计" */
export function formatCapacityBytes(bytes: number | null | undefined): string {
  if (!hasValidCapacity(bytes)) return '未统计'
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  const value = bytes / Math.pow(1024, i)
  return `${value.toFixed(i > 1 ? 1 : 0)} ${units[i]}`
}

/** Status display text */
export function statusText(status: string): string {
  const map: Record<string, string> = {
    pending: '待执行',
    running: '运行中',
    succeeded: '已成功',
    failed: '失败',
    cancelled: '已取消',
    stale: '已过期',
    skipped: '已跳过',
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
    stale: 'st-stale',
    skipped: 'st-skipped',
    ready: 'st-pending',
  }
  return map[status] ?? 'st-pending'
}
