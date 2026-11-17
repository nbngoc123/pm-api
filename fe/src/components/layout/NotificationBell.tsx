import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell } from 'lucide-react'
import { Popover } from 'radix-ui'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/api/client'
import type { Notification, Page, Task } from '@/api/types'
import { EmptyState } from '@/components/ui/misc'
import { fromNow } from '@/lib/format'
import { cn } from '@/lib/utils'

/** Backend chưa có realtime nên hỏi lại định kỳ. */
const POLL_MS = 45_000

export function NotificationBell({ expanded }: { expanded: boolean }) {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  const list = useQuery({
    queryKey: ['notifications'],
    queryFn: () => api.get<Page<Notification>>('/me/notifications', { size: 30 }),
    refetchInterval: POLL_MS,
  })
  const items = list.data?.items ?? []
  const unread = items.filter((n) => !n.da_doc).length
  const refresh = () => qc.invalidateQueries({ queryKey: ['notifications'] })

  const readAll = useMutation({ mutationFn: () => api.post('/me/notifications/read-all'), onSuccess: refresh })
  const openItem = useMutation({
    mutationFn: async (n: Notification) => {
      if (!n.da_doc) await api.post(`/notifications/${n.ma_tb}/read`)
      return n.ma_cv ? api.get<Task>(`/tasks/${n.ma_cv}`).catch(() => null) : null
    },
    onSuccess: (task) => {
      refresh()
      if (task) {
        setOpen(false)
        navigate(`/projects/${task.ma_du_an}/tasks?task=${task.ma_cv}`)
      }
    },
  })

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger
        className="relative flex h-8 items-center gap-2 rounded-md px-2 hover:bg-rail-active hover:text-white"
        aria-label={unread ? `Thông báo, ${unread} chưa đọc` : 'Thông báo'}
      >
        <Bell className="size-4 shrink-0" />
        {expanded ? <span className="text-sm">Thông báo</span> : null}
        {unread ? (
          <span className={cn('rounded-full bg-danger px-1 text-[10px] leading-4 font-semibold text-white', expanded ? 'ml-auto' : 'absolute -top-0.5 right-0')}>
            {unread}
          </span>
        ) : null}
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content side="right" align="end" sideOffset={8} className="z-50 flex max-h-[70vh] w-80 flex-col rounded-lg border bg-surface shadow-xl">
          <div className="flex items-center justify-between border-b px-3 py-2">
            <span className="text-sm font-semibold">Thông báo</span>
            {unread ? (
              <button type="button" className="text-xs text-primary hover:underline" onClick={() => readAll.mutate()}>
                Đánh dấu đã đọc hết
              </button>
            ) : null}
          </div>
          <ul className="overflow-y-auto">
            {items.length === 0 ? <EmptyState title="Chưa có thông báo" /> : null}
            {items.map((n) => (
              <li key={n.ma_tb} className="border-b last:border-0">
                <button type="button" onClick={() => openItem.mutate(n)} className="flex w-full gap-2 px-3 py-2 text-left hover:bg-surface-2">
                  <span className={cn('mt-1.5 size-1.5 shrink-0 rounded-full', n.da_doc ? 'bg-transparent' : 'bg-primary')} />
                  <span className="min-w-0">
                    <span className={cn('block text-sm', !n.da_doc && 'font-medium')}>{n.tieu_de}</span>
                    {n.noi_dung ? <span className="block truncate text-xs text-muted">{n.noi_dung}</span> : null}
                    <span className="block text-xs text-subtle">{fromNow(n.created_at)}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
