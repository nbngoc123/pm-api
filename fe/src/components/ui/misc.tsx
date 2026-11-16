import { Loader2 } from 'lucide-react'
import type { ReactNode } from 'react'
import { ApiError, errorMessage } from '@/api/client'
import { cn, initials } from '@/lib/utils'
import { Button } from './button'

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn('size-4 animate-spin text-muted', className)} aria-label="Đang tải" />
}

export function PageLoader() {
  return (
    <div className="flex h-full min-h-40 items-center justify-center">
      <Spinner className="size-6" />
    </div>
  )
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <section className={cn('rounded-lg border bg-surface', className)}>{children}</section>
}

export function CardHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <header className="flex h-11 items-center justify-between gap-2 border-b px-4">
      <h2 className="text-sm font-semibold">{title}</h2>
      {action}
    </header>
  )
}

type StatTone = 'primary' | 'success' | 'warning' | 'danger' | 'purple'

const STAT_ACCENT: Record<StatTone, string> = {
  primary: 'border-l-primary',
  success: 'border-l-success-soft-fg',
  warning: 'border-l-warning-soft-fg',
  danger: 'border-l-danger',
  purple: 'border-l-purple-soft-fg',
}

export function Stat({ label, value, hint, tone }: { label: string; value: ReactNode; hint?: string; tone?: StatTone }) {
  return (
    <Card className={cn('border-l-[3px] px-4 py-3', tone ? STAT_ACCENT[tone] : 'border-l-border-strong')}>
      <p className="text-xs text-muted">{label}</p>
      <p className={cn('mt-0.5 text-2xl font-semibold tabular-nums', tone === 'danger' && 'text-danger')}>{value}</p>
      {hint ? <p className="text-xs text-subtle">{hint}</p> : null}
    </Card>
  )
}

export function Progress({ value, className }: { value: number; className?: string }) {
  const pct = Math.max(0, Math.min(100, value))
  return (
    <div className={cn('h-1.5 overflow-hidden rounded-full bg-neutral-soft', className)} role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
      <div className={cn('h-full rounded-full', value > 100 ? 'bg-danger' : 'bg-primary')} style={{ width: `${pct}%` }} />
    </div>
  )
}

export function Avatar({ name, className }: { name: string; className?: string }) {
  return (
    <span
      title={name}
      className={cn('inline-flex size-6 shrink-0 items-center justify-center rounded-full bg-primary-soft text-[10px] font-semibold text-primary-soft-fg', className)}
    >
      {initials(name)}
    </span>
  )
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 px-4 py-10 text-center">
      <p className="font-medium">{title}</p>
      {description ? <p className="max-w-sm text-sm text-muted">{description}</p> : null}
      {action}
    </div>
  )
}

/** Trạng thái lỗi của một truy vấn. 404 nghĩa là không tồn tại hoặc không có quyền xem. */
export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const notFound = error instanceof ApiError && error.status === 404
  return (
    <EmptyState
      title={notFound ? 'Không tìm thấy trang này' : 'Không tải được dữ liệu'}
      description={notFound ? 'Nội dung không tồn tại hoặc bạn không có quyền xem.' : errorMessage(error)}
      action={!notFound && onRetry ? <Button onClick={onRetry}>Thử lại</Button> : undefined}
    />
  )
}
