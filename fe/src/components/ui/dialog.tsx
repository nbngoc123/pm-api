import { X } from 'lucide-react'
import { Dialog as Primitive } from 'radix-ui'
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface OverlayProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  children: ReactNode
  footer?: ReactNode
  className?: string
}

function Header({ title, description }: Pick<OverlayProps, 'title' | 'description'>) {
  return (
    <div className="flex items-start justify-between gap-4 border-b px-4 py-3">
      <div className="min-w-0">
        <Primitive.Title className="truncate text-base font-semibold">{title}</Primitive.Title>
        {description ? (
          <Primitive.Description className="text-xs text-muted">{description}</Primitive.Description>
        ) : (
          <Primitive.Description className="sr-only">{title}</Primitive.Description>
        )}
      </div>
      <Primitive.Close className="rounded p-1 text-muted hover:bg-surface-2 hover:text-fg" aria-label="Đóng">
        <X className="size-4" />
      </Primitive.Close>
    </div>
  )
}

/** Hộp thoại giữa màn hình, dùng cho form ngắn và xác nhận. */
export function Dialog({ open, onOpenChange, title, description, children, footer, className }: OverlayProps) {
  return (
    <Primitive.Root open={open} onOpenChange={onOpenChange}>
      <Primitive.Portal>
        <Primitive.Overlay className="fixed inset-0 z-40 bg-black/40" />
        <Primitive.Content
          className={cn(
            'fixed top-1/2 left-1/2 z-40 flex max-h-[85vh] w-[calc(100vw-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 flex-col rounded-lg border bg-surface shadow-xl',
            className,
          )}
        >
          <Header title={title} description={description} />
          <div className="overflow-y-auto p-4">{children}</div>
          {footer ? <div className="flex justify-end gap-2 border-t px-4 py-3">{footer}</div> : null}
        </Primitive.Content>
      </Primitive.Portal>
    </Primitive.Root>
  )
}

/** Khung trượt từ cạnh phải, dùng để xem chi tiết mà không rời danh sách. */
export function Sheet({ open, onOpenChange, title, description, children, footer, className }: OverlayProps) {
  return (
    <Primitive.Root open={open} onOpenChange={onOpenChange}>
      <Primitive.Portal>
        <Primitive.Overlay className="fixed inset-0 z-30 bg-black/20" />
        <Primitive.Content
          className={cn('fixed inset-y-0 right-0 z-30 flex w-full max-w-xl flex-col border-l bg-surface shadow-xl', className)}
        >
          <Header title={title} description={description} />
          <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
          {footer ? <div className="flex flex-wrap gap-2 border-t px-4 py-3">{footer}</div> : null}
        </Primitive.Content>
      </Primitive.Portal>
    </Primitive.Root>
  )
}
