import { ChevronRight } from 'lucide-react'
import { Fragment, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'

export interface Crumb {
  label: string
  to?: string
}

interface PageProps {
  crumbs: Crumb[]
  title: string
  actions?: ReactNode
  /** Hàng tab hoặc bộ lọc nằm ngay dưới tiêu đề. */
  toolbar?: ReactNode
  children: ReactNode
  /** Bỏ padding và cuộn mặc định, cho màn hình tự quản lý vùng cuộn như Kanban. */
  flush?: boolean
}

export function Page({ crumbs, title, actions, toolbar, children, flush }: PageProps) {
  return (
    <main className="flex min-w-0 flex-1 flex-col">
      <header className="shrink-0 border-b bg-surface px-5 pt-3">
        <nav aria-label="Đường dẫn" className="flex items-center gap-1 text-xs text-muted">
          {crumbs.map((c, i) => (
            <Fragment key={c.label}>
              {i > 0 ? <ChevronRight className="size-3" /> : null}
              {c.to ? (
                <Link to={c.to} className="hover:text-fg hover:underline">
                  {c.label}
                </Link>
              ) : (
                <span>{c.label}</span>
              )}
            </Fragment>
          ))}
        </nav>
        <div className={cn('flex min-h-10 items-center justify-between gap-3', !toolbar && 'pb-2')}>
          <h1 className="truncate text-lg font-semibold">{title}</h1>
          <div className="flex shrink-0 items-center gap-2">{actions}</div>
        </div>
        {toolbar}
      </header>
      <div className={cn('min-h-0 flex-1', flush ? 'flex flex-col' : 'overflow-y-auto p-5')}>{children}</div>
    </main>
  )
}
