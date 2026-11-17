import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'
import { errorMessage } from '@/api/client'
import type { Violation } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { Field, Input, Select, Textarea } from '@/components/ui/form'
import { useMembers } from '@/features/projects/queries'
import { useProjectTasks } from '@/features/tasks/queries'
import { toFormErrors } from '@/lib/formErrors'
import { useConclude, useCreateViolation, useExplain, useRules } from './queries'

/** Ghi nhận vi phạm mới ở trạng thái Nháp. Chỉ ghi được cho nhân viên thuộc dự án. */
export function CreateViolationDialog({ projectId, onClose }: { projectId: number; onClose: () => void }) {
  const create = useCreateViolation(projectId)
  const members = useMembers(projectId)
  const tasks = useProjectTasks(projectId)
  const rules = useRules()
  const [ma_cv, setTask] = useState('')
  const [ma_nd, setPerson] = useState('')
  const [ma_qd, setRule] = useState('')
  const [noi_dung, setNote] = useState('')
  const errors = create.error ? toFormErrors(create.error) : null
  const valid = !!ma_cv && !!ma_nd && !!ma_qd && noi_dung.trim().length >= 5

  function submit(e: FormEvent) {
    e.preventDefault()
    create.mutate(
      { ma_cv: Number(ma_cv), ma_nd: Number(ma_nd), ma_qd: Number(ma_qd), noi_dung: noi_dung.trim() },
      {
        onSuccess: () => {
          toast.success('Đã ghi nhận vi phạm ở dạng nháp. Gửi yêu cầu giải trình khi sẵn sàng.')
          onClose()
        },
      },
    )
  }

  return (
    <Dialog
      open
      onOpenChange={onClose}
      title="Ghi nhận vi phạm"
      description="Hồ sơ được lưu ở dạng nháp. Chưa gửi cho nhân viên cho đến khi bạn bấm Gửi yêu cầu giải trình."
      footer={
        <>
          <Button onClick={onClose}>Hủy</Button>
          <Button variant="primary" type="submit" form="create-violation" loading={create.isPending} disabledReason={valid ? null : 'Chọn công việc, người vi phạm, quy định và mô tả (ít nhất 5 ký tự).'}>
            Lưu nháp
          </Button>
        </>
      }
    >
      <form id="create-violation" onSubmit={submit} className="flex flex-col gap-3">
        <Field label="Công việc liên quan" error={errors?.fields.ma_cv}>
          <Select value={ma_cv} onChange={(e) => setTask(e.target.value)}>
            <option value="">Chọn công việc</option>
            {tasks.data?.map((t) => (
              <option key={t.ma_cv} value={t.ma_cv}>
                {t.ten_cv}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Nhân viên vi phạm" error={errors?.fields.ma_nd} hint="Trưởng nhóm và quản lý không thể bị ghi nhận vi phạm.">
          <Select value={ma_nd} onChange={(e) => setPerson(e.target.value)}>
            <option value="">Chọn nhân viên</option>
            {members.data?.map((m) => (
              <option key={m.ma_nguoi_dung} value={m.ma_nguoi_dung}>
                {m.ho_ten}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Quy định áp dụng" error={errors?.fields.ma_qd} hint="Điểm trừ sẽ được tính vào kỳ KPI khi kết luận xử phạt.">
          <Select value={ma_qd} onChange={(e) => setRule(e.target.value)}>
            <option value="">Chọn quy định</option>
            {rules.data?.map((r) => (
              <option key={r.ma_qd} value={r.ma_qd}>
                {r.ten_quy_dinh} (−{r.diem_tru} điểm)
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Mô tả vi phạm" error={errors?.fields.noi_dung}>
          <Textarea value={noi_dung} onChange={(e) => setNote(e.target.value)} placeholder="Ví dụ: Nộp báo cáo muộn 2 ngày so với hạn đã thống nhất" />
        </Field>
        {errors?.form ? <p className="text-sm text-danger">{errors.form}</p> : null}
      </form>
    </Dialog>
  )
}

/** Nhân viên nộp đơn giải trình. Có thể nộp nhiều đơn trước khi quản lý kết luận. */
export function ExplainDialog({ projectId, violation, onClose }: { projectId: number; violation: Violation; onClose: () => void }) {
  const explain = useExplain(projectId)
  const [noi_dung, setText] = useState('')
  const [link, setLink] = useState('')
  const errors = explain.error ? toFormErrors(explain.error) : null

  function submit(e: FormEvent) {
    e.preventDefault()
    explain.mutate(
      { id: violation.ma_vp, noi_dung: noi_dung.trim(), duong_dan_bang_chung: link.trim() || null },
      {
        onSuccess: () => {
          toast.success('Đã gửi giải trình')
          onClose()
        },
      },
    )
  }

  return (
    <Dialog
      open
      onOpenChange={onClose}
      title="Gửi giải trình"
      description="Bạn có thể gửi thêm đơn bổ sung cho đến khi quản lý kết luận."
      footer={
        <>
          <Button onClick={onClose}>Hủy</Button>
          <Button variant="primary" type="submit" form="explain" loading={explain.isPending} disabledReason={noi_dung.trim().length >= 5 ? null : 'Nhập giải trình (ít nhất 5 ký tự).'}>
            Gửi giải trình
          </Button>
        </>
      }
    >
      <form id="explain" onSubmit={submit} className="flex flex-col gap-3">
        <Field label="Nội dung giải trình" error={errors?.fields.noi_dung}>
          <Textarea value={noi_dung} onChange={(e) => setText(e.target.value)} rows={5} autoFocus />
        </Field>
        <Field label="Đường dẫn bằng chứng (không bắt buộc)" hint="Dán link tới tài liệu. Hệ thống hiện chưa nhận tệp tải lên cho phần này." error={errors?.fields.duong_dan_bang_chung}>
          <Input value={link} onChange={(e) => setLink(e.target.value)} placeholder="https://" type="url" />
        </Field>
        {errors?.form ? <p className="text-sm text-danger">{errors.form}</p> : null}
      </form>
    </Dialog>
  )
}

/** Quản lý kết luận: xử phạt hoặc bác bỏ. Ghi chú bắt buộc. */
export function ConcludeDialog({ projectId, violation, onClose }: { projectId: number; violation: Violation; onClose: () => void }) {
  const conclude = useConclude(projectId)
  const [result, setResult] = useState<'CONFIRMED' | 'DISMISSED'>('CONFIRMED')
  const [note, setNote] = useState('')
  const errors = conclude.error ? toFormErrors(conclude.error) : null

  function submit(e: FormEvent) {
    e.preventDefault()
    conclude.mutate(
      { id: violation.ma_vp, ket_luan: result, ghi_chu: note.trim() },
      {
        onSuccess: () => {
          toast.success(result === 'CONFIRMED' ? 'Đã xử phạt, điểm trừ được ghi nhận vào kỳ KPI' : 'Đã bác bỏ vi phạm')
          onClose()
        },
        onError: (err) => toast.error(errorMessage(err)),
      },
    )
  }

  return (
    <Dialog
      open
      onOpenChange={onClose}
      title="Kết luận vi phạm"
      description="Kết luận sẽ gửi thông báo cho nhân viên và trưởng nhóm."
      footer={
        <>
          <Button onClick={onClose}>Hủy</Button>
          <Button
            variant={result === 'CONFIRMED' ? 'danger' : 'primary'}
            type="submit"
            form="conclude"
            loading={conclude.isPending}
            disabledReason={note.trim().length >= 3 ? null : 'Nhập ghi chú kết luận (ít nhất 3 ký tự).'}
          >
            {result === 'CONFIRMED' ? 'Xử phạt' : 'Bác bỏ'}
          </Button>
        </>
      }
    >
      <form id="conclude" onSubmit={submit} className="flex flex-col gap-3">
        <fieldset className="flex gap-4">
          <legend className="mb-1 text-xs font-medium text-muted">Kết luận</legend>
          {(['CONFIRMED', 'DISMISSED'] as const).map((r) => (
            <label key={r} className="flex items-center gap-1.5 text-sm">
              <input type="radio" name="ket_luan" checked={result === r} onChange={() => setResult(r)} />
              {r === 'CONFIRMED' ? 'Xử phạt (trừ điểm)' : 'Bác bỏ (không trừ điểm)'}
            </label>
          ))}
        </fieldset>
        <Field label="Ghi chú kết luận" error={errors?.fields.ghi_chu}>
          <Textarea value={note} onChange={(e) => setNote(e.target.value)} rows={4} autoFocus />
        </Field>
        {errors?.form ? <p className="text-sm text-danger">{errors.form}</p> : null}
      </form>
    </Dialog>
  )
}
