import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building2, ShieldCheck, User as UserIcon, Users, type LucideIcon } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import type { Page as Paged, User } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { Field, Input, Select } from '@/components/ui/form'
import { toFormErrors } from '@/lib/formErrors'
import { cn } from '@/lib/utils'

type SystemRole = 'EMPLOYEE' | 'MANAGER' | 'DIRECTOR' | 'ADMIN'

/** Mô tả lấy từ ma trận quyền của backend (seed.py). */
const ROLES: { code: SystemRole; label: string; icon: LucideIcon; text: string }[] = [
  { code: 'EMPLOYEE', label: 'Nhân viên', icon: UserIcon, text: 'Nhận việc, ghi giờ làm, xem KPI của mình.' },
  { code: 'MANAGER', label: 'Quản lý', icon: Users, text: 'Làm quản lý dự án, duyệt KPI, kết luận vi phạm.' },
  { code: 'DIRECTOR', label: 'Ban giám đốc', icon: Building2, text: 'Tạo và đóng dự án, xem mọi dự án và báo cáo tổng.' },
  { code: 'ADMIN', label: 'Quản trị hệ thống', icon: ShieldCheck, text: 'Toàn quyền, kể cả quản lý tài khoản.' },
]

const PASSWORD_HINT = 'Ít nhất 8 ký tự, có cả chữ và số.'

export function CreateUserDialog({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient()
  const [role, setRole] = useState<SystemRole>('EMPLOYEE')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [managerId, setManagerId] = useState('')
  const [rate, setRate] = useState('')
  const isEmployee = role === 'EMPLOYEE'

  // Quản lý trực tiếp phải là người dùng loại quản lý.
  const managers = useQuery({
    queryKey: ['users', 'managers'],
    queryFn: async () => (await api.get<Paged<User>>('/users', { size: 100 })).items.filter((u) => u.loai === 'QUAN_LY' && u.trang_thai === 'ACTIVE'),
    enabled: isEmployee,
  })

  const create = useMutation({
    mutationFn: () =>
      api.post<User>('/users', {
        email,
        ho_ten: name,
        password,
        vai_tro_he_thong: role,
        ...(isEmployee ? { ma_quan_ly: managerId ? Number(managerId) : null, don_gia_gio: Number(rate) || 0 } : {}),
      }),
    onSuccess: (u) => {
      toast.success(`Đã tạo tài khoản cho ${u.ho_ten}`)
      qc.invalidateQueries({ queryKey: ['users'] })
      onClose()
    },
  })
  const errors = create.error ? toFormErrors(create.error) : null

  function submit(e: FormEvent) {
    e.preventDefault()
    create.mutate()
  }

  return (
    <Dialog
      open
      onOpenChange={onClose}
      title="Tạo tài khoản"
      description="Chọn vai trò trước, rồi điền thông tin người dùng."
      className="max-w-xl"
      footer={
        <>
          <Button onClick={onClose}>Hủy</Button>
          <Button variant="primary" type="submit" form="create-user" loading={create.isPending}>
            Tạo tài khoản
          </Button>
        </>
      }
    >
      <form id="create-user" onSubmit={submit} className="flex flex-col gap-4">
        <fieldset>
          <legend className="mb-1.5 text-xs font-medium text-muted">Vai trò hệ thống</legend>
          <div className="grid grid-cols-2 gap-2">
            {ROLES.map((r) => (
              <label
                key={r.code}
                className={cn(
                  'flex cursor-pointer gap-2.5 rounded-md border p-2.5 has-focus-visible:outline-2 has-focus-visible:outline-primary',
                  role === r.code ? 'border-primary bg-primary-soft' : 'border-border-strong hover:bg-surface-2',
                )}
              >
                <input type="radio" name="vai_tro" className="sr-only" checked={role === r.code} onChange={() => setRole(r.code)} />
                <r.icon className={cn('mt-0.5 size-4 shrink-0', role === r.code ? 'text-primary' : 'text-muted')} />
                <span>
                  <span className="block text-sm font-medium">{r.label}</span>
                  <span className="block text-xs text-muted">{r.text}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Họ tên" error={errors?.fields.ho_ten}>
            <Input value={name} onChange={(e) => setName(e.target.value)} required minLength={2} maxLength={150} placeholder="Nguyễn Văn An" />
          </Field>
          <Field label="Email" error={errors?.fields.email}>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="an@congty.vn" autoComplete="off" />
          </Field>
        </div>
        <Field label="Mật khẩu ban đầu" hint={PASSWORD_HINT} error={errors?.fields.password}>
          <Input type="text" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoComplete="off" />
        </Field>

        {isEmployee ? (
          <div className="grid grid-cols-2 gap-3">
            <Field label="Quản lý trực tiếp" hint="Người này được duyệt KPI của nhân viên." error={errors?.fields.ma_quan_ly}>
              <Select value={managerId} onChange={(e) => setManagerId(e.target.value)}>
                <option value="">Chưa có</option>
                {managers.data?.map((m) => (
                  <option key={m.ma_nd} value={m.ma_nd}>
                    {m.ho_ten}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Đơn giá giờ (đồng)" hint="Dùng để tính chi phí giờ làm." error={errors?.fields.don_gia_gio}>
              <Input type="number" min={0} step={1000} value={rate} onChange={(e) => setRate(e.target.value)} placeholder="120000" />
            </Field>
          </div>
        ) : null}
        {errors?.form ? <p className="text-sm text-danger">{errors.form}</p> : null}
      </form>
    </Dialog>
  )
}

export function ResetPasswordDialog({ user, onClose }: { user: User; onClose: () => void }) {
  const [password, setPassword] = useState('')
  const reset = useMutation({
    mutationFn: () => api.post(`/users/${user.ma_nd}/reset-password`, { new_password: password }),
    onSuccess: () => {
      toast.success(`Đã đặt lại mật khẩu cho ${user.ho_ten}`)
      onClose()
    },
  })
  const errors = reset.error ? toFormErrors(reset.error) : null

  function submit(e: FormEvent) {
    e.preventDefault()
    reset.mutate()
  }

  return (
    <Dialog
      open
      onOpenChange={onClose}
      title="Đặt lại mật khẩu"
      description={`${user.ho_ten} sẽ bị đăng xuất khỏi mọi thiết bị.`}
      footer={
        <>
          <Button onClick={onClose}>Hủy</Button>
          <Button variant="primary" type="submit" form="reset-password" loading={reset.isPending}>
            Đặt lại mật khẩu
          </Button>
        </>
      }
    >
      <form id="reset-password" onSubmit={submit} className="flex flex-col gap-3">
        <Field label="Mật khẩu mới" hint={PASSWORD_HINT} error={errors?.fields.new_password}>
          <Input type="text" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoComplete="off" autoFocus />
        </Field>
        {errors?.form ? <p className="text-sm text-danger">{errors.form}</p> : null}
      </form>
    </Dialog>
  )
}
