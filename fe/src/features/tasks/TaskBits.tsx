import { useQuery } from '@tanstack/react-query'
import { CalendarDays } from 'lucide-react'
import { api } from '@/api/client'
import type { Assignment, Task, Urgency } from '@/api/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Avatar } from '@/components/ui/misc'
import { formatDate } from '@/lib/format'
import { URGENCY } from '@/lib/labels'
import { cn } from '@/lib/utils'
import { taskActions } from './rules'
import { useTaskBoard } from './TaskBoardContext'

export function Assignees({ task, max = 3 }: { task: Task; max?: number }) {
  const { members } = useTaskBoard()
  // Backend chỉ trả người đang được giao; task đã xong hoặc đã hủy thì danh sách này rỗng.
  const closed = task.trang_thai === 'DONE' || task.trang_thai === 'CANCELLED'
  // Việc đã xong không còn người được giao, nên lấy người đã hoàn thành từ lịch sử phân công.
  const history = useQuery({
    queryKey: ['task', task.ma_cv, 'assignments'],
    queryFn: () => api.get<Assignment[]>(`/tasks/${task.ma_cv}/assignments`),
    enabled: closed,
  })
  const ids = closed ? (history.data ?? []).filter((a) => a.trang_thai_phan_cong === 'COMPLETED').map((a) => a.ma_nd) : task.assignees
  if (ids.length === 0) return closed ? null : <span className="text-xs text-subtle">Chưa giao</span>
  return (
    <span className="flex -space-x-1.5">
      {ids.slice(0, max).map((id) => (
        <Avatar key={id} name={members.get(id)?.ho_ten ?? `#${id}`} className="ring-2 ring-surface" />
      ))}
      {ids.length > max ? (
        <span className="inline-flex size-6 items-center justify-center rounded-full bg-neutral-soft text-[10px] font-medium ring-2 ring-surface">
          +{ids.length - max}
        </span>
      ) : null}
    </span>
  )
}

/** Hạn hoàn thành, tô màu theo mức độ gấp do backend tính. */
export function Deadline({ task }: { task: Task }) {
  if (!task.han_hoan_thanh) return <span className="text-xs text-subtle">Chưa có hạn</span>
  const urgency = task.muc_do_khan as Urgency | null
  const hot = urgency === 'OVERDUE' || urgency === 'URGENT'
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted tabular-nums">
      <CalendarDays className={cn('size-3.5', urgency === 'OVERDUE' && 'text-danger')} />
      {formatDate(task.han_hoan_thanh)}
      {hot ? <Badge tone={URGENCY[urgency].tone}>{URGENCY[urgency].text}</Badge> : null}
    </span>
  )
}

/** Các nút hành động hợp lệ với trạng thái hiện tại. Thiếu quyền thì hiện mờ kèm lý do. */
export function TaskActionButtons({ task, includeSecondary = false }: { task: Task; includeSecondary?: boolean }) {
  const { actor, run } = useTaskBoard()
  const actions = taskActions(task, actor).filter((a) => includeSecondary || !a.secondary)
  return (
    <>
      {actions.map((a) => (
        <Button
          key={a.key}
          size="sm"
          // Trên thẻ chỉ nút Duyệt được tô đậm, để bảng nhiều thẻ không nặng mắt.
          variant={(includeSecondary ? a.primary : a.key === 'approve') ? 'primary' : a.key === 'cancel' ? 'danger' : 'secondary'}
          disabledReason={a.reason}
          onClick={(e) => {
            e.stopPropagation()
            run(task, a)
          }}
        >
          {a.label}
        </Button>
      ))}
    </>
  )
}
