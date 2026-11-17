import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import type { UserLookup } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { Field, Input, Textarea } from '@/components/ui/form'
import { toDateInput } from '@/lib/format'
import { toFormErrors } from '@/lib/formErrors'
import { useCreateProject } from './queries'
import { UserPicker } from './UserPicker'

export function CreateProjectDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const navigate = useNavigate()
  const create = useCreateProject()
  const [name, setName] = useState('')
  const [goal, setGoal] = useState('')
  const [start, setStart] = useState(() => toDateInput(new Date()))
  const [end, setEnd] = useState('')
  const [budget, setBudget] = useState('')
  const [manager, setManager] = useState<UserLookup | null>(null)
  const errors = create.error ? toFormErrors(create.error) : null

  function submit(e: FormEvent) {
    e.preventDefault()
    if (!manager) return
    create.mutate(
      { ten_du_an: name, muc_tieu: goal || null, ngay_bat_dau: start, ngay_ket_thuc_du_kien: end, ngan_sach_gio: Number(budget) || 0, ma_quan_ly: manager.ma_nd },
      {
        onSuccess: (p) => {
          toast.success('Đã tạo dự án')
          onOpenChange(false)
          navigate(`/projects/${p.ma_du_an}`)
        },
      },
    )
  }

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="Tạo dự án"
      footer={
        <>
          <Button onClick={() => onOpenChange(false)}>Hủy</Button>
          <Button variant="primary" type="submit" form="create-project" loading={create.isPending} disabledReason={manager ? null : 'Chọn quản lý dự án trước.'}>
            Tạo dự án
          </Button>
        </>
      }
    >
      <form id="create-project" onSubmit={submit} className="flex flex-col gap-3">
        <Field label="Tên dự án" error={errors?.fields.ten_du_an}>
          <Input value={name} onChange={(e) => setName(e.target.value)} required minLength={3} maxLength={200} placeholder="Website bán hàng" />
        </Field>
        <Field label="Mục tiêu" error={errors?.fields.muc_tieu}>
          <Textarea value={goal} onChange={(e) => setGoal(e.target.value)} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Ngày bắt đầu" error={errors?.fields.ngay_bat_dau}>
            <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} required />
          </Field>
          <Field label="Ngày kết thúc dự kiến" error={errors?.fields.ngay_ket_thuc_du_kien}>
            <Input type="date" value={end} min={start} onChange={(e) => setEnd(e.target.value)} required />
          </Field>
        </div>
        <Field label="Ngân sách giờ" hint="Để trống nếu không giới hạn." error={errors?.fields.ngan_sach_gio}>
          <Input type="number" min={0} step="any" value={budget} onChange={(e) => setBudget(e.target.value)} />
        </Field>
        <Field label="Quản lý dự án" hint="Phải là người dùng loại quản lý." error={errors?.fields.ma_quan_ly}>
          <UserPicker value={manager} onChange={setManager} />
        </Field>
        {errors?.form ? <p className="text-sm text-danger">{errors.form}</p> : null}
      </form>
    </Dialog>
  )
}
