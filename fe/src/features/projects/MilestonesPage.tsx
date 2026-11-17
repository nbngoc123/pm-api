import { Plus, Trash2 } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'
import { errorMessage } from '@/api/client'
import type { MilestoneStatus } from '@/api/types'
import { Page } from '@/components/layout/Page'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { Field, Input, Select } from '@/components/ui/form'
import { Card, EmptyState, ErrorState, PageLoader } from '@/components/ui/misc'
import { formatDate } from '@/lib/format'
import { toFormErrors } from '@/lib/formErrors'
import { MILESTONE_STATUS } from '@/lib/labels'
import { blockedReason, useProjectContext } from './projectContext'
import { useCreateMilestone, useDeleteMilestone, useMilestones, useUpdateMilestone } from './queries'

export function MilestonesPage() {
  const ctx = useProjectContext()
  const { project } = ctx
  const milestones = useMilestones(project.ma_du_an)
  const update = useUpdateMilestone(project.ma_du_an)
  const remove = useDeleteMilestone(project.ma_du_an)
  const [creating, setCreating] = useState(false)
  const blocked = blockedReason(ctx, 'milestone.manage', 'quản lý dự án')
  const onError = (e: unknown) => toast.error(errorMessage(e))

  return (
    <Page
      crumbs={[{ label: 'Dự án', to: '/projects' }, { label: project.ten_du_an, to: `/projects/${project.ma_du_an}` }, { label: 'Mốc' }]}
      title="Mốc dự án"
      actions={
        <Button variant="primary" disabledReason={blocked} onClick={() => setCreating(true)}>
          <Plus />
          Thêm mốc
        </Button>
      }
    >
      <Card className="mx-auto max-w-4xl overflow-hidden">
        {milestones.isPending ? (
          <PageLoader />
        ) : milestones.isError ? (
          <ErrorState error={milestones.error} onRetry={milestones.refetch} />
        ) : milestones.data.length === 0 ? (
          <EmptyState title="Đặt mốc đầu tiên cho dự án" description="Mốc đánh dấu các điểm bàn giao quan trọng. Công việc có thể gắn vào mốc." />
        ) : (
          <ul>
            {milestones.data.map((m) => (
              <li key={m.ma_moc} className="flex items-center gap-3 border-b px-4 py-2.5 last:border-0">
                <span className="min-w-0 flex-1 truncate font-medium">{m.ten_moc}</span>
                <span className="text-sm text-muted tabular-nums">Hạn {formatDate(m.han_hoan_thanh)}</span>
                {blocked ? (
                  <Badge tone={MILESTONE_STATUS[m.trang_thai].tone}>{MILESTONE_STATUS[m.trang_thai].text}</Badge>
                ) : (
                  <Select
                    className="w-32"
                    aria-label={`Trạng thái mốc ${m.ten_moc}`}
                    value={m.trang_thai}
                    onChange={(e) => update.mutate({ ma_moc: m.ma_moc, trang_thai: e.target.value as MilestoneStatus }, { onError })}
                  >
                    {Object.entries(MILESTONE_STATUS).map(([k, v]) => (
                      <option key={k} value={k}>
                        {v.text}
                      </option>
                    ))}
                  </Select>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Xóa mốc ${m.ten_moc}`}
                  disabledReason={blocked}
                  onClick={() => confirm(`Xóa mốc "${m.ten_moc}"?`) && remove.mutate(m.ma_moc, { onSuccess: () => toast.success('Đã xóa mốc'), onError })}
                >
                  <Trash2 />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Card>
      {creating ? <CreateMilestoneDialog onClose={() => setCreating(false)} /> : null}
    </Page>
  )
}

function CreateMilestoneDialog({ onClose }: { onClose: () => void }) {
  const { project } = useProjectContext()
  const create = useCreateMilestone(project.ma_du_an)
  const [name, setName] = useState('')
  const [due, setDue] = useState('')
  const errors = create.error ? toFormErrors(create.error) : null

  function submit(e: FormEvent) {
    e.preventDefault()
    create.mutate(
      { ten_moc: name, han_hoan_thanh: due },
      {
        onSuccess: () => {
          toast.success('Đã thêm mốc')
          onClose()
        },
      },
    )
  }

  return (
    <Dialog
      open
      onOpenChange={onClose}
      title="Thêm mốc"
      footer={
        <>
          <Button onClick={onClose}>Hủy</Button>
          <Button variant="primary" type="submit" form="create-milestone" loading={create.isPending}>
            Thêm mốc
          </Button>
        </>
      }
    >
      <form id="create-milestone" onSubmit={submit} className="flex flex-col gap-3">
        <Field label="Tên mốc" error={errors?.fields.ten_moc}>
          <Input value={name} onChange={(e) => setName(e.target.value)} required minLength={2} placeholder="Bàn giao bản beta" autoFocus />
        </Field>
        <Field label="Hạn hoàn thành" hint="Phải nằm trong thời gian của dự án." error={errors?.fields.han_hoan_thanh}>
          <Input type="date" value={due} min={project.ngay_bat_dau} max={project.ngay_ket_thuc_du_kien} onChange={(e) => setDue(e.target.value)} required />
        </Field>
        {errors?.form ? <p className="text-sm text-danger">{errors.form}</p> : null}
      </form>
    </Dialog>
  )
}
