import { DndContext, DragOverlay, PointerSensor, useDraggable, useDroppable, useSensor, useSensors, type DragEndEvent } from '@dnd-kit/core'
import { useState } from 'react'
import type { Task, TaskStatus } from '@/api/types'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/misc'
import { BOARD_COLUMNS, PRIORITY, TASK_STATUS } from '@/lib/labels'
import { cn } from '@/lib/utils'
import { dropAction } from './rules'
import { Assignees, Deadline, TaskActionButtons } from './TaskBits'
import { useTaskBoard } from './TaskBoardContext'

const COLUMN_ACCENT: Record<TaskStatus, string> = {
  TODO: 'border-t-subtle',
  IN_PROGRESS: 'border-t-primary',
  IN_REVIEW: 'border-t-purple-soft-fg',
  DONE: 'border-t-success-soft-fg',
  CANCELLED: 'border-t-subtle',
}

export function KanbanBoard({ tasks }: { tasks: Task[] }) {
  const { actor, run } = useTaskBoard()
  const [dragging, setDragging] = useState<Task | null>(null)
  // Phải kéo quá 6px mới tính là kéo, để bấm vào thẻ vẫn mở được chi tiết.
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }))

  function onDragEnd(e: DragEndEvent) {
    const task = dragging
    setDragging(null)
    const to = e.over?.id as TaskStatus | undefined
    if (!task || !to || to === task.trang_thai) return
    const action = dropAction(task, to, actor)
    if (action && !action.reason) run(task, action)
  }

  return (
    <DndContext
      sensors={sensors}
      onDragStart={(e) => setDragging(tasks.find((t) => t.ma_cv === e.active.id) ?? null)}
      onDragEnd={onDragEnd}
      onDragCancel={() => setDragging(null)}
    >
      <div className="flex min-h-0 flex-1 gap-3 overflow-x-auto p-4">
        {BOARD_COLUMNS.map((status) => (
          <Column key={status} status={status} tasks={tasks.filter((t) => t.trang_thai === status)} dragging={dragging} />
        ))}
      </div>
      <DragOverlay>{dragging ? <CardBody task={dragging} className="w-64 rotate-2 shadow-lg" /> : null}</DragOverlay>
    </DndContext>
  )
}

function Column({ status, tasks, dragging }: { status: TaskStatus; tasks: Task[]; dragging: Task | null }) {
  const { actor } = useTaskBoard()
  const { setNodeRef, isOver } = useDroppable({ id: status })

  // Khi đang kéo: cột nào không nhận được thẻ thì làm mờ và nêu lý do.
  const isSource = dragging?.trang_thai === status
  const action = dragging && !isSource ? dropAction(dragging, status, actor) : null
  const blocked = dragging && !isSource ? (action ? action.reason : 'Không chuyển thẳng sang cột này được.') : null
  const accepts = !!dragging && !isSource && !blocked

  return (
    <section
      ref={setNodeRef}
      aria-label={TASK_STATUS[status].text}
      className={cn(
        'flex min-w-40 flex-1 basis-0 flex-col rounded-lg border border-t-[3px] bg-surface-2 transition-opacity',
        COLUMN_ACCENT[status],
        blocked && 'opacity-45',
        accepts && 'border-dashed border-primary',
        accepts && isOver && 'bg-primary-soft',
      )}
    >
      <header className="flex h-9 shrink-0 items-center gap-2 px-3">
        <Badge tone={TASK_STATUS[status].tone}>{TASK_STATUS[status].text}</Badge>
        <span className="text-xs text-muted tabular-nums">{tasks.length}</span>
      </header>
      <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto px-2 pb-2">
        {blocked ? <p className="rounded-md border border-dashed px-2 py-1.5 text-xs text-muted">{blocked}</p> : null}
        {accepts && action?.key === 'approve' ? (
          <p className="rounded-md border border-dashed border-primary px-2 py-1.5 text-xs text-primary">Thả vào đây để mở hộp duyệt.</p>
        ) : null}
        {tasks.map((t) => (
          <DraggableCard key={t.ma_cv} task={t} />
        ))}
        {tasks.length === 0 && !dragging ? <p className="px-1 py-2 text-xs text-subtle">Không có công việc nào.</p> : null}
      </div>
    </section>
  )
}

function DraggableCard({ task }: { task: Task }) {
  const { openTask } = useTaskBoard()
  const { setNodeRef, attributes, listeners, isDragging } = useDraggable({ id: task.ma_cv })
  return (
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      onClick={() => openTask(task.ma_cv)}
      onKeyDown={(e) => e.key === 'Enter' && openTask(task.ma_cv)}
      className={cn('cursor-grab touch-none rounded-md', isDragging && 'opacity-30')}
    >
      <CardBody task={task} />
    </div>
  )
}

function CardBody({ task, className }: { task: Task; className?: string }) {
  return (
    <article className={cn('flex flex-col gap-2 rounded-md border bg-surface p-2.5 hover:border-border-strong', className)}>
      <div className="flex flex-wrap items-start justify-between gap-x-2 gap-y-1">
        <p className="min-w-0 text-sm leading-snug font-medium">{task.ten_cv}</p>
        <Badge tone={PRIORITY[task.uu_tien].tone}>{PRIORITY[task.uu_tien].text}</Badge>
      </div>
      {task.trang_thai === 'IN_PROGRESS' ? (
        <div className="flex items-center gap-2">
          <Progress className="flex-1" value={task.ty_le_hoan_thanh} />
          <span className="text-xs text-muted tabular-nums">{task.ty_le_hoan_thanh}%</span>
        </div>
      ) : null}
      <div className="flex flex-wrap items-center justify-between gap-x-2.5 gap-y-1">
        <Deadline task={task} />
        <Assignees task={task} />
      </div>
      <div className="flex flex-wrap gap-1.5" onPointerDown={(e) => e.stopPropagation()}>
        <TaskActionButtons task={task} />
      </div>
    </article>
  )
}
