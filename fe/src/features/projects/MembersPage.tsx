import { Plus, UserMinus } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'
import { errorMessage } from '@/api/client'
import type { ProjectRole, UserLookup } from '@/api/types'
import { Page } from '@/components/layout/Page'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { Field, Select } from '@/components/ui/form'
import { Avatar, Card, ErrorState, PageLoader } from '@/components/ui/misc'
import { formatDate } from '@/lib/format'
import { toFormErrors } from '@/lib/formErrors'
import { PROJECT_ROLE } from '@/lib/labels'
import { blockedReason, useProjectContext } from './projectContext'
import { useAddMember, useChangeMemberRole, useMembers, useRemoveMember } from './queries'
import { UserPicker } from './UserPicker'

/** Vai trò PM do hệ thống tự gán cho quản lý dự án, không chọn tay được. */
const ASSIGNABLE_ROLES: ProjectRole[] = ['TEAM_LEAD', 'MEMBER']

export function MembersPage() {
  const ctx = useProjectContext()
  const { project } = ctx
  const members = useMembers(project.ma_du_an)
  const changeRole = useChangeMemberRole(project.ma_du_an)
  const remove = useRemoveMember(project.ma_du_an)
  const [adding, setAdding] = useState(false)
  const blocked = blockedReason(ctx, 'member.manage', 'quản lý dự án')
  const onError = (e: unknown) => toast.error(errorMessage(e))

  return (
    <Page
      crumbs={[{ label: 'Dự án', to: '/projects' }, { label: project.ten_du_an, to: `/projects/${project.ma_du_an}` }, { label: 'Thành viên' }]}
      title="Thành viên"
      actions={
        <Button variant="primary" disabledReason={blocked} onClick={() => setAdding(true)}>
          <Plus />
          Thêm thành viên
        </Button>
      }
    >
      <Card className="mx-auto max-w-4xl overflow-hidden">
        {members.isPending ? (
          <PageLoader />
        ) : members.isError ? (
          <ErrorState error={members.error} onRetry={members.refetch} />
        ) : (
          <ul>
            {members.data.map((m) => {
              const isManager = m.ma_nguoi_dung === project.ma_quan_ly
              return (
                <li key={m.ma_nguoi_dung} className="flex items-center gap-3 border-b px-4 py-2.5 last:border-0">
                  <Avatar name={m.ho_ten} className="size-8 text-xs" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{m.ho_ten}</p>
                    <p className="truncate text-xs text-muted">
                      {m.email} · Tham gia {formatDate(m.ngay_tham_gia)}
                    </p>
                  </div>
                  {isManager || blocked ? (
                    <Badge tone={isManager ? 'primary' : 'neutral'}>{PROJECT_ROLE[m.vai_tro as ProjectRole]}</Badge>
                  ) : (
                    <Select
                      className="w-36"
                      aria-label={`Vai trò của ${m.ho_ten}`}
                      value={m.vai_tro}
                      onChange={(e) => changeRole.mutate({ ma_nd: m.ma_nguoi_dung, vai_tro: e.target.value as ProjectRole }, { onError })}
                    >
                      {ASSIGNABLE_ROLES.map((r) => (
                        <option key={r} value={r}>
                          {PROJECT_ROLE[r]}
                        </option>
                      ))}
                    </Select>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Xóa ${m.ho_ten} khỏi dự án`}
                    disabledReason={isManager ? 'Không xóa được quản lý dự án khỏi dự án.' : blocked}
                    onClick={() =>
                      confirm(`Xóa ${m.ho_ten} khỏi dự án?`) && remove.mutate(m.ma_nguoi_dung, { onSuccess: () => toast.success('Đã xóa thành viên'), onError })
                    }
                  >
                    <UserMinus />
                  </Button>
                </li>
              )
            })}
          </ul>
        )}
      </Card>
      {adding ? <AddMemberDialog onClose={() => setAdding(false)} /> : null}
    </Page>
  )
}

function AddMemberDialog({ onClose }: { onClose: () => void }) {
  const { project } = useProjectContext()
  const add = useAddMember(project.ma_du_an)
  const [user, setUser] = useState<UserLookup | null>(null)
  const [role, setRole] = useState<ProjectRole>('MEMBER')
  const errors = add.error ? toFormErrors(add.error) : null

  function submit(e: FormEvent) {
    e.preventDefault()
    if (!user) return
    add.mutate(
      { ma_nguoi_dung: user.ma_nd, vai_tro: role },
      {
        onSuccess: () => {
          toast.success(`Đã thêm ${user.ho_ten}`)
          onClose()
        },
      },
    )
  }

  return (
    <Dialog
      open
      onOpenChange={onClose}
      title="Thêm thành viên"
      footer={
        <>
          <Button onClick={onClose}>Hủy</Button>
          <Button variant="primary" type="submit" form="add-member" loading={add.isPending} disabledReason={user ? null : 'Chọn một người trước.'}>
            Thêm thành viên
          </Button>
        </>
      }
    >
      <form id="add-member" onSubmit={submit} className="flex flex-col gap-3">
        <Field label="Người dùng">
          <UserPicker value={user} onChange={setUser} />
        </Field>
        <Field label="Vai trò trong dự án">
          <Select value={role} onChange={(e) => setRole(e.target.value as ProjectRole)}>
            {ASSIGNABLE_ROLES.map((r) => (
              <option key={r} value={r}>
                {PROJECT_ROLE[r]}
              </option>
            ))}
          </Select>
        </Field>
        {errors?.form ? <p className="text-sm text-danger">{errors.form}</p> : null}
      </form>
    </Dialog>
  )
}
