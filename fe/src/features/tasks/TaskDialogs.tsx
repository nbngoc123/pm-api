import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'
import type { Priority, Task } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { Field, Input, Select, Textarea } from '@/components/ui/form'
import { useMilestones } from '@/features/projects/queries'
import { formatHours, toDateTimeInput } from '@/lib/format'
import { toFormErrors } from '@/lib/formErrors'
import { PRIORITY } from '@/lib/labels'
import { useCreateTask, useEpics, useLogTime, useReviewTask, useUpdateTask, type TaskInput } from './queries'

function FormError({ message }: { message: string | null | undefined }) {
  return message ? <p className="text-sm text-danger">{message}</p> : null
}

/** Tạo công việc mới, hoặc sửa khi truyền task. */
export function TaskFormDialog({ projectId, task, onClose }: { projectId: number; task?: Task; onClose: () => void }) {
  const milestones = useMilestones(projectId)
  const epics = useEpics(projectId)
  const create = useCreateTask(projectId)
  const update = useUpdateTask(projectId)
  const mutation = task ? update : create
  const [form, setForm] = useState({
    ten_cv: task?.ten_cv ?? '',
    mo_ta: task?.mo_ta ?? '',
    uu_tien: task?.uu_tien ?? ('MEDIUM' as Priority),
    ma_moc: task?.ma_moc ? String(task.ma_moc) : '',
    ma_epic: task?.ma_epic ? String(task.ma_epic) : '',
    ngay_bat_dau_du_kien: task?.ngay_bat_dau_du_kien ?? '',
    han_hoan_thanh: task?.han_hoan_thanh ?? '',
    gio_du_kien: task ? String(task.gio_du_kien) : '',
  })
  const set = (patch: Partial<typeof form>) => setForm((f) => ({ ...f, ...patch }))
  const errors = mutation.error ? toFormErrors(mutation.error) : null

  function submit(e: FormEvent) {
    e.preventDefault()
    const body: TaskInput = {
      ten_cv: form.ten_cv,
      mo_ta: form.mo_ta || null,
      uu_tien: form.uu_tien,
      ma_moc: form.ma_moc ? Number(form.ma_moc) : null,
      ma_epic: form.ma_epic ? Number(form.ma_epic) : null,
      ngay_bat_dau_du_kien: form.ngay_bat_dau_du_kien || null,
      han_hoan_thanh: form.han_hoan_thanh || null,
      gio_du_kien: Number(form.gio_du_kien) || 0,
    }
    const onSuccess = () => {
      toast.success(task ? 'Đã lưu công việc' : 'Đã tạo công việc')
      onClose()
    }
    if (task) update.mutate({ task, changes: body }, { onSuccess })
    else create.mutate(body, { onSuccess })
  }

  return (
    <Dialog
      open
      onOpenChange={onClose}
      title={task ? 'Sửa công việc' : 'Tạo công việc'}
      className="max-w-lg"
      footer={
        <>
          <Button onClick={onClose}>Hủy</Button>
          <Button variant="primary" type="submit" form="task-form" loading={mutation.isPending}>
            {task ? 'Lưu thay đổi' : 'Tạo công việc'}
          </Button>
        </>
      }
    >
      <form id="task-form" onSubmit={submit} className="flex flex-col gap-3">
        <Field label="Tên công việc" error={errors?.fields.ten_cv}>
          <Input value={form.ten_cv} onChange={(e) => set({ ten_cv: e.target.value })} required maxLength={200} autoFocus placeholder="Thiết kế màn đăng nhập" />
        </Field>
        <Field label="Mô tả" error={errors?.fields.mo_ta}>
          <Textarea value={form.mo_ta} onChange={(e) => set({ mo_ta: e.target.value })} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Ưu tiên">
            <Select value={form.uu_tien} onChange={(e) => set({ uu_tien: e.target.value as Priority })}>
              {Object.entries(PRIORITY).map(([k, v]) => (
                <option key={k} value={k}>
                  {v.text}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Mốc" error={errors?.fields.ma_moc}>
            <Select value={form.ma_moc} onChange={(e) => set({ ma_moc: e.target.value })}>
              <option value="">Không gắn mốc</option>
              {milestones.data?.map((m) => (
                <option key={m.ma_moc} value={m.ma_moc}>
                  {m.ten_moc}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Epic" error={errors?.fields.ma_epic}>
            <Select value={form.ma_epic} onChange={(e) => set({ ma_epic: e.target.value })}>
              <option value="">Không thuộc epic</option>
              {epics.data?.map((ep) => (
                <option key={ep.ma_epic} value={ep.ma_epic}>
                  {ep.ten_epic}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Ngày bắt đầu dự kiến" error={errors?.fields.ngay_bat_dau_du_kien}>
            <Input type="date" value={form.ngay_bat_dau_du_kien} onChange={(e) => set({ ngay_bat_dau_du_kien: e.target.value })} />
          </Field>
          <Field label="Hạn hoàn thành" error={errors?.fields.han_hoan_thanh}>
            <Input type="date" value={form.han_hoan_thanh} min={form.ngay_bat_dau_du_kien || undefined} onChange={(e) => set({ han_hoan_thanh: e.target.value })} />
          </Field>
        </div>
        <Field label="Số giờ dự kiến" error={errors?.fields.gio_du_kien}>
          <Input type="number" min={0} step="any" value={form.gio_du_kien} onChange={(e) => set({ gio_du_kien: e.target.value })} placeholder="8" />
        </Field>
        <FormError message={errors?.form} />
      </form>
    </Dialog>
  )
}

/** Duyệt hoặc từ chối một công việc đang chờ duyệt. Từ chối bắt buộc có nhận xét. */
export function ReviewDialog({ projectId, task, initial, onClose }: { projectId: number; task: Task; initial: 'APPROVED' | 'REJECTED'; onClose: () => void }) {
  const review = useReviewTask(projectId)
  const [result, setResult] = useState(initial)
  const [comment, setComment] = useState('')
  const errors = review.error ? toFormErrors(review.error) : null
  const missingComment = result === 'REJECTED' && !comment.trim()

  function submit(e: FormEvent) {
    e.preventDefault()
    review.mutate(
      { id: task.ma_cv, ket_qua: result, nhan_xet: comment.trim() || null },
      {
        onSuccess: () => {
          toast.success(result === 'APPROVED' ? 'Đã duyệt công việc' : 'Đã từ chối, công việc quay lại đang làm')
          onClose()
        },
      },
    )
  }

  return (
    <Dialog
      open
      onOpenChange={onClose}
      title="Xét duyệt công việc"
      description={task.ten_cv}
      footer={
        <>
          <Button onClick={onClose}>Hủy</Button>
          <Button
            variant={result === 'APPROVED' ? 'primary' : 'danger'}
            type="submit"
            form="review-form"
            loading={review.isPending}
            disabledReason={missingComment ? 'Nhập nhận xét để từ chối.' : null}
          >
            {result === 'APPROVED' ? 'Duyệt' : 'Từ chối'}
          </Button>
        </>
      }
    >
      <form id="review-form" onSubmit={submit} className="flex flex-col gap-3">
        <fieldset className="flex gap-4">
          <legend className="mb-1 text-xs font-medium text-muted">Kết quả</legend>
          {(['APPROVED', 'REJECTED'] as const).map((r) => (
            <label key={r} className="flex items-center gap-1.5 text-sm">
              <input type="radio" name="ket_qua" checked={result === r} onChange={() => setResult(r)} />
              {r === 'APPROVED' ? 'Đạt, chuyển sang Xong' : 'Chưa đạt, trả về Đang làm'}
            </label>
          ))}
        </fieldset>
        <Field label={result === 'REJECTED' ? 'Nhận xét (bắt buộc)' : 'Nhận xét'} error={errors?.fields.nhan_xet}>
          <Textarea value={comment} onChange={(e) => setComment(e.target.value)} autoFocus placeholder="Cần bổ sung xử lý khi nhập sai mật khẩu" />
        </Field>
        <FormError message={errors?.form} />
      </form>
    </Dialog>
  )
}

export function LogTimeDialog({ projectId, task, onClose }: { projectId: number; task: Task; onClose: () => void }) {
  const logTime = useLogTime(projectId)
  // Mặc định là một giờ vừa qua.
  const [start, setStart] = useState(() => toDateTimeInput(new Date(Date.now() - 60 * 60_000)))
  const [end, setEnd] = useState(() => toDateTimeInput(new Date()))
  const [note, setNote] = useState('')
  const errors = logTime.error ? toFormErrors(logTime.error) : null

  function submit(e: FormEvent) {
    e.preventDefault()
    // Ô nhập theo giờ máy người dùng; gửi ISO có múi giờ để backend tự quy về UTC.
    logTime.mutate(
      { id: task.ma_cv, body: { bat_dau: new Date(start).toISOString(), ket_thuc: new Date(end).toISOString(), noi_dung: note || null } },
      {
        onSuccess: (t) => {
          toast.success(`Đã ghi ${formatHours(t.so_gio)}`, {
            description: t.tong_gio_tich_luy_task != null ? `Tổng giờ của công việc: ${formatHours(t.tong_gio_tich_luy_task)}` : undefined,
          })
          onClose()
        },
      },
    )
  }

  return (
    <Dialog
      open
      onOpenChange={onClose}
      title="Ghi giờ làm"
      description={task.ten_cv}
      footer={
        <>
          <Button onClick={onClose}>Hủy</Button>
          <Button variant="primary" type="submit" form="log-time" loading={logTime.isPending}>
            Ghi giờ
          </Button>
        </>
      }
    >
      <form id="log-time" onSubmit={submit} className="flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Bắt đầu" error={errors?.fields.bat_dau}>
            <Input type="datetime-local" value={start} max={end} onChange={(e) => setStart(e.target.value)} required />
          </Field>
          <Field label="Kết thúc" error={errors?.fields.ket_thuc}>
            <Input type="datetime-local" value={end} min={start} onChange={(e) => setEnd(e.target.value)} required />
          </Field>
        </div>
        <Field label="Nội dung đã làm" hint="Không ghi giờ tương lai, không trùng bản ghi khác, tối đa 24 giờ mỗi lần.">
          <Textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Dựng giao diện form và kiểm tra dữ liệu nhập" />
        </Field>
        <FormError message={errors?.form} />
      </form>
    </Dialog>
  )
}
