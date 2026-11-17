export function formatDate(val?: string | Date | null): string {
  if (!val) return '—'
  try {
    const d = val instanceof Date ? val : new Date(val.includes('T') ? (val.endsWith('Z') ? val : val + 'Z') : val + 'T00:00:00Z')
    if (isNaN(d.getTime())) return String(val)
    return d.toLocaleDateString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', day: '2-digit', month: '2-digit', year: 'numeric' })
  } catch {
    return String(val)
  }
}

export function formatDateTime(val?: string | Date | null): string {
  if (!val) return '—'
  try {
    const d = val instanceof Date ? val : new Date(val.endsWith('Z') ? val : val + 'Z')
    if (isNaN(d.getTime())) return String(val)
    return d.toLocaleString('vi-VN', {
      timeZone: 'Asia/Ho_Chi_Minh',
      hour: '2-digit',
      minute: '2-digit',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
  } catch {
    return String(val)
  }
}

export function formatTime(val?: string | Date | null): string {
  if (!val) return '—'
  try {
    const d = val instanceof Date ? val : new Date(val.endsWith('Z') ? val : val + 'Z')
    if (isNaN(d.getTime())) return String(val)
    return d.toLocaleTimeString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', minute: '2-digit' })
  } catch {
    return String(val)
  }
}

export function fromNow(val?: string | Date | null): string {
  if (!val) return ''
  try {
    const d = val instanceof Date ? val : new Date(val.endsWith('Z') ? val : val + 'Z')
    const diff = Date.now() - d.getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return 'Vừa xong'
    if (mins < 60) return `${mins} phút trước`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours} giờ trước`
    const days = Math.floor(hours / 24)
    return `${days} ngày trước`
  } catch {
    return ''
  }
}

export function formatHours(hours?: number | null): string {
  if (hours == null) return '0h'
  return `${Number(hours).toLocaleString('vi-VN', { maximumFractionDigits: 1 })}h`
}

export function formatFileSize(bytes?: number | null): string {
  if (bytes == null || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

export function toDateInput(val?: string | Date | null): string {
  if (!val) return ''
  if (val instanceof Date) return val.toISOString().slice(0, 10)
  if (val.length === 10) return val
  return val.slice(0, 10)
}

export function toDateTimeInput(val?: string | Date | null): string {
  if (!val) return ''
  if (val instanceof Date) return val.toISOString().slice(0, 16)
  return val.slice(0, 16)
}

export function parseUtc(val: string): Date {
  return new Date(val.endsWith('Z') ? val : val + 'Z')
}
