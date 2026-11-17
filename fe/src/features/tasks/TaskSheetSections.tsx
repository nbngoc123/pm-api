import { Download, Paperclip, Plus, Trash2, X } from 'lucide-react'
import { useRef, useState, type FormEvent, type ReactNode } from 'react'
import { toast } from 'sonner'
import { api, errorMessage } from '@/api/client'
import type { AssignWarning, Task } from '@/api/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input, Select } from '@/components/ui/form'
import { Avatar, Spinner } from '@/components/ui/misc'
import { formatDateTime, formatFileSize, formatHours } from '@/lib/format'
import {
  useAssign,
  useAttachments,
  useCreateSubTask,
  useDeleteAttachment,
  useDeleteSubTask,
  useReviews,
  useSubTasks,
  useTaskTimesheets,
  useToggleSubTask,
  useUnassign,
  useUploadAttachment,
} from './queries'
import { canWorkOn } from './rules'
import { useTaskBoard } from './TaskBoardContext'

const onError = (e: unknown) => toast.error(errorMessage(e))

export function Section({ title, count, action, children }: { title: string; count?: number; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="border-t px-4 py-3">
      <header className="mb-2 flex h-7 items-center justify-between">
        <h3 className="text-sm font-semibold">
          {title}
          {count !== undefined ? <span className="ml-1.5 font-normal text-muted tabular-nums">{count}</span> : null}
        </h3>
        {action}
      </header>
      {children}
    </section>
  )
}

function Empty({ children }: { children: ReactNode }) {
  return <p className="text-sm text-subtle">{children}</p>
}

/** Lý do không sửa được task, dùng chung cho các phần cần quyền trưởng nhóm. */
function useLeadBlock(task: Task) {
  const { actor } = useTaskBoard()
  if (actor.readOnly) return 'Dự án đã hoàn thành hoặc đã đóng nên không thay đổi được.'
  if (task.trang_thai === 'DONE' || task.trang_thai === 'CANCELLED') return 'Công việc đã xong hoặc đã hủy nên không thay đổi được.'
  return null
}

export function AssigneeSection({ task }: { task: Task }) {
  const { projectId, actor, members } = useTaskBoard()
  const assign = useAssign(projectId)
  const unassign = useUnassign(projectId)
  const blocked = useLeadBlock(task) ?? (actor.can('task.assign') ? null : 'Cần quyền trưởng nhóm hoặc quản lý dự án.')
  // Quản lý dự án thuộc loại quản lý nên không nhận việc được (backend trả ASSIGNEE_MUST_BE_EMPLOYEE).
  const candidates = [...members.values()].filter((m) => m.vai_tro !== 'PM' && !task.assignees.includes(m.ma_nguoi_dung))

  function add(ma_nd: number) {
    assign.mutate(
      { id: task.ma_cv, ma_nd },
      {
        onSuccess: (res) => {
          toast.success('Đã phân công')
          // Cảnh báo không chặn: vượt ngân sách giờ, hạn đã qua.
          for (const w of res.warnings as unknown as AssignWarning[]) toast.warning(w.message)
        },
        onError,
      },
    )
  }

  return (
    <Section title="Người làm" count={task.assignees.length}>
      <ul className="flex flex-col gap-1.5">
        {task.assignees.length === 0 ? <Empty>Chưa giao cho ai. Phải có người làm thì mới bắt đầu được.</Empty> : null}
        {task.assignees.map((id) => {
          const name = members.get(id)?.ho_ten ?? `Người dùng #${id}`
          return (
            <li key={id} className="flex items-center gap-2">
              <Avatar name={name} />
              <span className="flex-1 truncate text-sm">{name}</span>
              <Button variant="ghost" size="icon" aria-label={`Bỏ phân công ${name}`} disabledReason={blocked} onClick={() => unassign.mutate({ id: task.ma_cv, ma_nd: id }, { onError })}>
                <X />
              </Button>
            </li>
          )
        })}
      </ul>
      {blocked ? null : (
        <Select
          className="mt-2"
          aria-label="Giao thêm người"
          value=""
          onChange={(e) => e.target.value && add(Number(e.target.value))}
          disabled={assign.isPending || candidates.length === 0}
        >
          <option value="">{candidates.length ? 'Giao thêm người…' : 'Mọi thành viên đã được giao'}</option>
          {candidates.map((m) => (
            <option key={m.ma_nguoi_dung} value={m.ma_nguoi_dung}>
              {m.ho_ten}
            </option>
          ))}
        </Select>
      )}
    </Section>
  )
}

export function SubTaskSection({ task }: { task: Task }) {
  const { projectId, actor } = useTaskBoard()
  const subs = useSubTasks(task.ma_cv)
  const create = useCreateSubTask(projectId)
  const toggle = useToggleSubTask(projectId)
  const remove = useDeleteSubTask(projectId)
  const [name, setName] = useState('')
  const canEdit = !actor.readOnly && actor.can('task.update')
  const canToggle = !actor.readOnly && canWorkOn(task, actor)

  function submit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    create.mutate({ id: task.ma_cv, ten_subtask: name.trim() }, { onSuccess: () => setName(''), onError })
  }

  return (
    <Section title="Việc con" count={subs.data?.length}>
      {subs.data?.length === 0 && !canEdit ? <Empty>Chưa có việc con.</Empty> : null}
      <ul className="flex flex-col">
        {subs.data?.map((s) => (
          <li key={s.ma_subtask} className="group flex items-center gap-2 py-0.5">
            <input
              type="checkbox"
              className="size-4"
              checked={s.trang_thai === 'DONE'}
              disabled={!canToggle}
              title={canToggle ? undefined : 'Chỉ người được giao hoặc trưởng nhóm mới đánh dấu được.'}
              onChange={() => toggle.mutate({ id: task.ma_cv, sub: s }, { onError })}
              aria-label={s.ten_subtask}
            />
            <span className={s.trang_thai === 'DONE' ? 'flex-1 text-sm text-subtle line-through' : 'flex-1 text-sm'}>{s.ten_subtask}</span>
            {canEdit ? (
              <button
                type="button"
                className="rounded p-1 text-subtle opacity-0 group-hover:opacity-100 hover:text-danger focus-visible:opacity-100"
                aria-label={`Xóa việc con ${s.ten_subtask}`}
                onClick={() => remove.mutate({ id: task.ma_cv, ma_subtask: s.ma_subtask }, { onError })}
              >
                <Trash2 className="size-3.5" />
              </button>
            ) : null}
          </li>
        ))}
      </ul>
      {canEdit ? (
        <form onSubmit={submit} className="mt-2 flex gap-2">
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Thêm việc con" maxLength={200} aria-label="Tên việc con" />
          <Button type="submit" size="icon" aria-label="Thêm việc con" loading={create.isPending}>
            <Plus />
          </Button>
        </form>
      ) : null}
    </Section>
  )
}

export function AttachmentSection({ task }: { task: Task }) {
  const { projectId, actor } = useTaskBoard()
  const files = useAttachments(task.ma_cv)
  const upload = useUploadAttachment(projectId)
  const remove = useDeleteAttachment(projectId)
  const input = useRef<HTMLInputElement>(null)
  const uploadBlocked = actor.readOnly
    ? 'Dự án đã hoàn thành hoặc đã đóng nên không thay đổi được.'
    : canWorkOn(task, actor)
      ? null
      : 'Chỉ người được giao hoặc trưởng nhóm mới đính kèm được.'

  return (
    <Section
      title="Tệp đính kèm"
      count={files.data?.length}
      action={
        <Button size="sm" disabledReason={uploadBlocked} loading={upload.isPending} onClick={() => input.current?.click()}>
          {upload.isPending ? <Spinner /> : <Paperclip />}
          Đính kèm
        </Button>
      }
    >
      <input
        ref={input}
        type="file"
        hidden
        accept=".pdf,.png,.jpg,.jpeg,.docx,.xlsx,.pptx,.txt,.csv,.zip"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) upload.mutate({ id: task.ma_cv, file }, { onSuccess: () => toast.success('Đã tải tệp lên'), onError })
          e.target.value = ''
        }}
      />
      {files.data?.length === 0 ? <Empty>Chưa có tệp nào. Nhận pdf, ảnh, tài liệu Office, txt, csv, zip, tối đa 10 MB.</Empty> : null}
      <ul className="flex flex-col gap-1">
        {files.data?.map((f) => (
          <li key={f.ma_tep} className="flex items-center gap-2 text-sm">
            <span className="min-w-0 flex-1 truncate">{f.ten_tep}</span>
            <span className="text-xs text-subtle tabular-nums">{formatFileSize(f.kich_thuoc)}</span>
            <Button variant="ghost" size="icon" aria-label={`Tải ${f.ten_tep}`} onClick={() => api.download(`/attachments/${f.ma_tep}/download`, f.ten_tep).catch(onError)}>
              <Download />
            </Button>
            {!actor.readOnly && (f.ma_nguoi_tai === actor.userId || actor.can('task.update')) ? (
              <Button variant="ghost" size="icon" aria-label={`Xóa ${f.ten_tep}`} onClick={() => remove.mutate(f.ma_tep, { onError })}>
                <Trash2 />
              </Button>
            ) : null}
          </li>
        ))}
      </ul>
    </Section>
  )
}

export function TimesheetSection({ task }: { task: Task }) {
  const { members, actor } = useTaskBoard()
  const sheets = useTaskTimesheets(task.ma_cv)
  const total = sheets.data?.reduce((n, s) => n + s.so_gio, 0) ?? 0
  return (
    <Section title={actor.can('report.project') ? 'Giờ làm' : 'Giờ làm của bạn'} count={sheets.data?.length}>
      {sheets.data?.length === 0 ? <Empty>Chưa có giờ làm nào được ghi.</Empty> : null}
      <ul className="flex flex-col gap-1.5">
        {sheets.data?.map((s) => (
          <li key={s.ma_nk} className="text-sm">
            <div className="flex justify-between gap-2">
              <span className="text-muted tabular-nums">
                {formatDateTime(s.bat_dau)} · {members.get(s.ma_nd)?.ho_ten ?? `#${s.ma_nd}`}
              </span>
              <span className="font-medium tabular-nums">{formatHours(s.so_gio)}</span>
            </div>
            {s.noi_dung ? <p className="text-xs text-subtle">{s.noi_dung}</p> : null}
          </li>
        ))}
      </ul>
      {sheets.data?.length ? <p className="mt-2 border-t pt-2 text-right text-sm font-medium tabular-nums">Tổng: {formatHours(total)}</p> : null}
    </Section>
  )
}

export function ReviewSection({ task }: { task: Task }) {
  const { members } = useTaskBoard()
  const reviews = useReviews(task.ma_cv)
  if (!reviews.data?.length) return null
  return (
    <Section title="Lịch sử duyệt" count={reviews.data.length}>
      <ul className="flex flex-col gap-2">
        {reviews.data.map((r) => (
          <li key={r.ma_duyet} className="text-sm">
            <div className="flex items-center gap-2">
              <Badge tone={r.ket_qua === 'APPROVED' ? 'success' : 'danger'}>{r.ket_qua === 'APPROVED' ? 'Đạt' : 'Từ chối'}</Badge>
              <span className="text-muted">
                {members.get(r.ma_nguoi_duyet)?.ho_ten ?? `#${r.ma_nguoi_duyet}`} · {formatDateTime(r.thoi_diem_duyet)}
              </span>
            </div>
            {r.nhan_xet ? <p className="mt-0.5 whitespace-pre-wrap">{r.nhan_xet}</p> : null}
          </li>
        ))}
      </ul>
    </Section>
  )
}
