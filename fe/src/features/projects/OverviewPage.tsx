import { toast } from 'sonner'
import { errorMessage } from '@/api/client'
import type { ProjectStatus } from '@/api/types'
import { Page } from '@/components/layout/Page'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, ErrorState, PageLoader, Progress, Stat } from '@/components/ui/misc'
import { formatDate, formatHours } from '@/lib/format'
import { BOARD_COLUMNS, MILESTONE_STATUS, TASK_STATUS } from '@/lib/labels'
import { useProjectContext } from './projectContext'
import { useChangeProjectStatus, useProjectOverview } from './queries'

/** Các bước chuyển trạng thái dự án mà backend cho phép (đóng dự án là thao tác riêng của Ban giám đốc). */
const NEXT_STATUS: Record<ProjectStatus, { to: ProjectStatus; label: string }[]> = {
  PLANNING: [{ to: 'ACTIVE', label: 'Bắt đầu dự án' }],
  ACTIVE: [
    { to: 'ON_HOLD', label: 'Tạm dừng' },
    { to: 'COMPLETED', label: 'Đánh dấu hoàn thành' },
  ],
  ON_HOLD: [{ to: 'ACTIVE', label: 'Tiếp tục dự án' }],
  COMPLETED: [{ to: 'ACTIVE', label: 'Mở lại dự án' }],
  CLOSED: [],
}

export function OverviewPage() {
  const { project, can } = useProjectContext()
  const overview = useProjectOverview(project.ma_du_an)
  const changeStatus = useChangeProjectStatus(project.ma_du_an)
  const o = overview.data

  return (
    <Page
      crumbs={[{ label: 'Dự án', to: '/projects' }, { label: project.ten_du_an }]}
      title="Tổng quan"
      actions={NEXT_STATUS[project.trang_thai].map((s) => (
        <Button
          key={s.to}
          loading={changeStatus.isPending}
          disabledReason={can('project.update') ? null : 'Cần quyền quản lý dự án.'}
          onClick={() => changeStatus.mutate(s.to, { onSuccess: () => toast.success('Đã cập nhật trạng thái dự án'), onError: (e) => toast.error(errorMessage(e)) })}
        >
          {s.label}
        </Button>
      ))}
    >
      {overview.isPending ? (
        <PageLoader />
      ) : overview.isError || !o ? (
        <ErrorState error={overview.error} onRetry={overview.refetch} />
      ) : (
        <div className="mx-auto flex max-w-6xl flex-col gap-4">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Tỷ lệ hoàn thành" value={`${o.ty_le_hoan_thanh}%`} hint={`${o.task_hoan_thanh} trên ${o.tong_task} công việc`} />
            <Stat label="Công việc trễ hạn" value={o.task_tre_han} tone={o.task_tre_han ? 'danger' : undefined} />
            <Stat
              label="Ngày còn lại"
              value={o.so_ngay_con_lai}
              tone={o.so_ngay_con_lai < 0 ? 'danger' : undefined}
              hint={`Kết thúc dự kiến ${formatDate(project.ngay_ket_thuc_du_kien)}`}
            />
            <Stat label="Thành viên" value={o.so_thanh_vien} />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader title="Công việc theo trạng thái" />
              <ul className="flex flex-col gap-3 p-4">
                {BOARD_COLUMNS.map((s) => {
                  const n = o.task_theo_trang_thai[s] ?? 0
                  return (
                    <li key={s} className="flex items-center gap-3">
                      <span className="w-24">
                        <Badge tone={TASK_STATUS[s].tone}>{TASK_STATUS[s].text}</Badge>
                      </span>
                      <Progress className="flex-1" value={o.tong_task ? (n / o.tong_task) * 100 : 0} />
                      <span className="w-8 text-right font-medium tabular-nums">{n}</span>
                    </li>
                  )
                })}
              </ul>
            </Card>

            <Card>
              <CardHeader title="Giờ làm và mốc" />
              <div className="flex flex-col gap-4 p-4">
                <div>
                  <div className="mb-1 flex justify-between text-sm">
                    <span className="text-muted">Giờ thực tế so với ngân sách</span>
                    <span className="font-medium tabular-nums">
                      {formatHours(o.gio_thuc_te)}
                      {o.ngan_sach_gio ? ` / ${formatHours(o.ngan_sach_gio)}` : ''}
                    </span>
                  </div>
                  {o.ty_le_su_dung_ngan_sach_gio === null ? (
                    <p className="text-xs text-subtle">Dự án không đặt ngân sách giờ.</p>
                  ) : (
                    <Progress value={o.ty_le_su_dung_ngan_sach_gio} />
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {(Object.keys(MILESTONE_STATUS) as (keyof typeof MILESTONE_STATUS)[]).map((s) => (
                    <Badge key={s} tone={MILESTONE_STATUS[s].tone}>
                      {MILESTONE_STATUS[s].text}: {o.moc_theo_trang_thai[s] ?? 0}
                    </Badge>
                  ))}
                </div>
                {project.muc_tieu ? (
                  <div>
                    <p className="text-xs font-medium text-muted">Mục tiêu</p>
                    <p className="text-sm whitespace-pre-wrap">{project.muc_tieu}</p>
                  </div>
                ) : null}
              </div>
            </Card>
          </div>
        </div>
      )}
    </Page>
  )
}
