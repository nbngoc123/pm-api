import { Clock, Pencil, Trash2 } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { toast } from 'sonner'
import { errorMessage } from '@/api/client'
import type { Task } from '@/api/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Sheet } from '@/components/ui/dialog'
import { ErrorState, PageLoader } from '@/components/ui/misc'
import { useMilestones } from '@/features/projects/queries'
import { formatHours } from '@/lib/format'
import { PRIORITY, TASK_STATUS } from '@/lib/labels'
import { useDeleteTask, useSetProgress, useTask } from './queries'
import { canWorkOn, isAssignee } from './rules'
import { Deadline, TaskActionButtons } from './TaskBits'
import { useTaskBoard } from './TaskBoardContext'
import { LogTimeDialog, TaskFormDialog } from './TaskDialogs'
import { AssigneeSection, AttachmentSection, ReviewSection, SubTaskSection, TimesheetSection } from './TaskSheetSections'

export function TaskSheet({ taskId, onClose }: { taskId: number; onClose: () => void }) {
  const task = useTask(taskId)
  return (
    <Sheet
      open
      onOpenChange={onClose}
      title={task.data?.ten_cv ?? 'Công việc'}
      description={task.data ? `Mã công việc #${task.data.ma_cv}` : undefined}
      footer={task.data ? <Footer task={task.data} onClose={onClose} /> : undefined}
    >
      {task.isPending ? <PageLoader /> : task.isError ? <ErrorState error={task.error} onRetry={task.refetch} /> : <Body task={task.data} />}
    </Sheet>
  )
}

function Meta({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 text-sm">{children}</dd>
    </div>
  )
}

function Body({ task }: { task: Task }) {
  const { projectId, members } = useTaskBoard()
  const milestones = useMilestones(projectId)
  const milestone = milestones.data?.find((m) => m.ma_moc === task.ma_moc)
  return (
    <>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-3 px-4 py-3">
        <Meta label="Trạng thái">
          <Badge tone={TASK_STATUS[task.trang_thai].tone}>{TASK_STATUS[task.trang_thai].text}</Badge>
        </Meta>
        <Meta label="Ưu tiên">
          <Badge tone={PRIORITY[task.uu_tien].tone}>{PRIORITY[task.uu_tien].text}</Badge>
        </Meta>
        <Meta label="Hạn hoàn thành">
          <Deadline task={task} />
        </Meta>
        <Meta label="Số giờ dự kiến">{task.gio_du_kien ? formatHours(task.gio_du_kien) : '—'}</Meta>
        <Meta label="Mốc">{milestone?.ten_moc ?? '—'}</Meta>
        <Meta label="Người tạo">{members.get(task.ma_nguoi_tao)?.ho_ten ?? `#${task.ma_nguoi_tao}`}</Meta>
      </dl>
      {task.mo_ta ? <p className="border-t px-4 py-3 text-sm whitespace-pre-wrap">{task.mo_ta}</p> : null}
      {/* key: khi backend trả % mới thì thanh kéo nhận lại giá trị gốc. */}
      <ProgressControl key={task.ty_le_hoan_thanh} task={task} />
      <AssigneeSection task={task} />
      <SubTaskSection task={task} />
      <TimesheetSection task={task} />
      <AttachmentSection task={task} />
      <ReviewSection task={task} />
    </>
  )
}

/** Thanh kéo % hoàn thành. Backend chỉ nhận khi task đang làm và người sửa là người được giao hoặc trưởng nhóm. */
function ProgressControl({ task }: { task: Task }) {
  const { projectId, actor } = useTaskBoard()
  const setProgress = useSetProgress(projectId)
  const [value, setValue] = useState(task.ty_le_hoan_thanh)

  if (task.trang_thai !== 'IN_PROGRESS') return null
  const editable = !actor.readOnly && canWorkOn(task, actor)
  const commit = () => {
    if (value !== task.ty_le_hoan_thanh) setProgress.mutate({ id: task.ma_cv, pct: value }, { onError: (e) => toast.error(errorMessage(e)) })
  }
  return (
    <div className="border-t px-4 py-3">
      <label className="flex items-center gap-3 text-sm">
        <span className="w-20 shrink-0 font-semibold">Tiến độ</span>
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={value}
          disabled={!editable}
          title={editable ? undefined : 'Chỉ người được giao hoặc trưởng nhóm mới cập nhật được.'}
          onChange={(e) => setValue(Number(e.target.value))}
          onPointerUp={commit}
          onKeyUp={commit}
          className="flex-1"
        />
        <span className="w-10 text-right tabular-nums">{value}%</span>
      </label>
    </div>
  )
}

function Footer({ task, onClose }: { task: Task; onClose: () => void }) {
  const { projectId, actor } = useTaskBoard()
  const remove = useDeleteTask(projectId)
  const [dialog, setDialog] = useState<'edit' | 'log' | null>(null)

  const closed = task.trang_thai === 'DONE' || task.trang_thai === 'CANCELLED'
  const readOnlyReason = actor.readOnly ? 'Dự án đã hoàn thành hoặc đã đóng nên không thay đổi được.' : null
  const logReason =
    readOnlyReason ?? (closed ? 'Không ghi giờ cho công việc đã xong hoặc đã hủy.' : isAssignee(task, actor) ? null : 'Chỉ ghi giờ được cho công việc giao cho bạn.')
  const editReason =
    readOnlyReason ??
    (closed ? 'Công việc đã xong hoặc đã hủy nên không sửa được.' : actor.can('task.update') ? null : 'Cần quyền trưởng nhóm hoặc quản lý dự án.')

  return (
    <>
      <TaskActionButtons task={task} includeSecondary />
      <div className="flex-1" />
      <Button size="sm" disabledReason={logReason} onClick={() => setDialog('log')}>
        <Clock />
        Ghi giờ
      </Button>
      <Button size="sm" disabledReason={editReason} onClick={() => setDialog('edit')}>
        <Pencil />
        Sửa
      </Button>
      {task.trang_thai === 'TODO' ? (
        <Button
          size="sm"
          variant="danger"
          disabledReason={editReason}
          onClick={() =>
            confirm(`Xóa công việc "${task.ten_cv}"? Thao tác này không hoàn tác được.`) &&
            remove.mutate(task.ma_cv, {
              onSuccess: () => {
                toast.success('Đã xóa công việc')
                onClose()
              },
              onError: (e) => toast.error(errorMessage(e)),
            })
          }
        >
          <Trash2 />
          Xóa
        </Button>
      ) : null}
      {/* key theo version: khi dữ liệu mới được tải lại (sau 409), form dựng lại từ server, không giữ bản nháp cũ. */}
      {dialog === 'edit' ? <TaskFormDialog key={task.version} projectId={projectId} task={task} onClose={() => setDialog(null)} /> : null}
      {dialog === 'log' ? <LogTimeDialog projectId={projectId} task={task} onClose={() => setDialog(null)} /> : null}
    </>
  )
}
