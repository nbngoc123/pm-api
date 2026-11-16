import { useMutation } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { useAuth } from '@/auth/useAuth'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { Field, Input } from '@/components/ui/form'
import { toFormErrors } from '@/lib/formErrors'

export function ChangePasswordDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const { logout } = useAuth()
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')

  const change = useMutation({
    mutationFn: () => api.post('/auth/change-password', { old_password: oldPassword, new_password: newPassword }),
    onSuccess: () => {
      // Backend thu hồi mọi token sau khi đổi mật khẩu nên phải đăng nhập lại.
      toast.success('Đã đổi mật khẩu. Đăng nhập lại để tiếp tục.')
      logout()
    },
  })
  const errors = change.error ? toFormErrors(change.error) : null

  function submit(e: FormEvent) {
    e.preventDefault()
    change.mutate()
  }

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="Đổi mật khẩu"
      description="Bạn sẽ cần đăng nhập lại sau khi đổi."
      footer={
        <>
          <Button onClick={() => onOpenChange(false)}>Hủy</Button>
          <Button variant="primary" type="submit" form="change-password" loading={change.isPending}>
            Đổi mật khẩu
          </Button>
        </>
      }
    >
      <form id="change-password" onSubmit={submit} className="flex flex-col gap-3">
        <Field label="Mật khẩu hiện tại">
          <Input type="password" autoComplete="current-password" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} required />
        </Field>
        <Field label="Mật khẩu mới" hint="Ít nhất 8 ký tự, có cả chữ và số." error={errors?.fields.new_password}>
          <Input type="password" autoComplete="new-password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={8} />
        </Field>
        {errors?.form ? <p className="text-sm text-danger">{errors.form}</p> : null}
      </form>
    </Dialog>
  )
}
