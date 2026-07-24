/**
 * 格式化工具函数
 */

/**
 * 格式化 ISO 日期字符串 → "2026-07-24"
 */
export function formatDate(iso: string): string {
  const d = new Date(iso)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/**
 * 格式化 ISO 日期字符串 → "2026-07-24 14:30:00"
 */
export function formatDateTime(iso: string): string {
  const d = new Date(iso)
  const date = formatDate(iso)
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  const s = String(d.getSeconds()).padStart(2, '0')
  return `${date} ${h}:${min}:${s}`
}

/**
 * 相对时间描述 → "2小时前" / "昨天" / "3天前" / "2026-07-24"
 */
export function formatRelativeTime(iso: string): string {
  const now = Date.now()
  const target = new Date(iso).getTime()
  const diff = now - target
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (seconds < 60) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days === 1) return '昨天'
  if (days <= 30) return `${days}天前`
  return formatDate(iso)
}

/**
 * 数字千分位 → "1,234"
 */
export function formatNumber(n: number): string {
  return n.toLocaleString('en-US')
}

/**
 * 百分比 → "87%"
 */
export function formatPercent(value: number, total: number): string {
  if (total === 0) return '0%'
  return `${Math.round((value / total) * 100)}%`
}

/**
 * 截断字符串
 */
export function truncate(s: string, max: number): string {
  if (s.length <= max) return s
  return s.slice(0, max) + '...'
}
