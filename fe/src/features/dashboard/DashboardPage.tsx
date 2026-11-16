import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '@/api/client'
import type { Dashboard } from '@/api/types'
import { useAuth } from '@/auth/useAuth'
import { Page } from '@/components/layout/Page'
import { Badge } from '@/components/ui/badge'
import { Card, CardHeader, EmptyState, ErrorState, PageLoader, Stat } from '@/components/ui/misc'
import { useProjects } from '@/features/projects/queries'
import { useOpenTask } from '@/features/tasks/useOpenTask'
import { formatDate, formatHours } from '@/lib/format'
import { BOARD_COLUMNS, PRIORITY, PROJECT_STATUS, TASK_STATUS } from '@/lib/labels'

export function DashboardPage() {
  const { user } = useAuth()
  const openTask = useOpenTask()
  const q = useQuery({ queryKey: ['dashboard'], queryFn: () => api.get<Dashboard>('/dashboard/me') })

  return (
    <Page crumbs={[{ label: 'Bảng điều khiển' }]} title={`Xin chào, ${user?.ho_ten ?? ''}`}>
      {q.isPending ? (
        <PageLoader />
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={q.refetch} />
      ) : (
        <div className="mx-auto flex max-w-6xl flex-col gap-4">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Việc đang mở" value={BOARD_COLUMNS.slice(0, 3).reduce((n, s) => n + (q.data.task_theo_trang_thai[s] ?? 0), 0)} hint="Được giao cho bạn" />
            <Stat label="Việc trễ hạn" value={q.data.task_tre_han} tone={q.data.task_tre_han ? 'danger' : undefined} />
            <Stat label="Giờ làm tuần này" value={q.data.gio_tuan_nay} hint={`Tháng này: ${q.data.gio_thang_nay} giờ`} />
            <Stat label="Dự án tham gia" value={q.data.so_du_an} />
          </div>

          {user?.loai === 'QUAN_LY' ? <ManagedProjects managerId={user.ma_nd} /> : null}

          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader title="Hạn trong 7 ngày tới" />
              {q.data.deadline_sap_toi.length === 0 ? (
                <EmptyState title="Không có việc nào sắp đến hạn" description="Các việc được giao cho bạn có hạn trong 7 ngày tới sẽ hiện ở đây." />
              ) : (
                <ul>
                  {q.data.deadline_sap_toi.map((t) => (
                    <li key={t.ma_cv} className="border-b last:border-0">
                      <button type="button" onClick={() => openTask(t.ma_cv)} className="flex w-full items-center gap-3 px-4 py-2 text-left hover:bg-surface-2">
                        <span className="min-w-0 flex-1 truncate">{t.ten_cv}</span>
                        <Badge tone={PRIORITY[t.uu_tien].tone}>{PRIORITY[t.uu_tien].text}</Badge>
                        <span className="w-20 text-right text-xs text-muted tabular-nums">{formatDate(t.han_hoan_thanh)}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card>
              <CardHeader title="Việc của bạn theo trạng thái" />
              <ul className="flex flex-col gap-2 p-4">
                {BOARD_COLUMNS.map((s) => (
                  <li key={s} className="flex items-center justify-between">
                    <Badge tone={TASK_STATUS[s].tone}>{TASK_STATUS[s].text}</Badge>
                    <span className="font-medium tabular-nums">{q.data.task_theo_trang_thai[s] ?? 0}</span>
                  </li>
                ))}
              </ul>
              <div className="border-t px-4 py-3">
                <Link to="/projects" className="text-sm text-primary hover:underline">
                  Xem các dự án
                </Link>
              </div>
            </Card>
          </div>
        </div>
      )}
    </Page>
  )
}

/** Quản lý thường không được giao việc nên bảng điều khiển cá nhân trống; hiện các dự án họ quản lý thay thế. */
function ManagedProjects({ managerId }: { managerId: number }) {
  const navigate = useNavigate()
  const projects = useProjects({})
  const managed = projects.data?.items.filter((p) => p.ma_quan_ly === managerId) ?? []
  return (
    <Card>
      <CardHeader title="Dự án bạn quản lý" action={<span className="text-xs text-muted tabular-nums">{managed.length} dự án</span>} />
      {projects.isPending ? (
        <PageLoader />
      ) : managed.length === 0 ? (
        <EmptyState title="Bạn chưa quản lý dự án nào" description="Ban giám đốc sẽ tạo dự án và chỉ định bạn làm quản lý." />
      ) : (
        <ul className="grid gap-px bg-border sm:grid-cols-2 lg:grid-cols-3">
          {managed.map((p) => (
            <li key={p.ma_du_an} className="bg-surface">
              <button type="button" onClick={() => navigate(`/projects/${p.ma_du_an}`)} className="flex w-full flex-col gap-1.5 px-4 py-3 text-left hover:bg-surface-2">
                <span className="flex items-center justify-between gap-2">
                  <span className="truncate font-medium">{p.ten_du_an}</span>
                  <Badge tone={PROJECT_STATUS[p.trang_thai].tone}>{PROJECT_STATUS[p.trang_thai].text}</Badge>
                </span>
                <span className="text-xs text-muted tabular-nums">
                  {formatDate(p.ngay_bat_dau)} – {formatDate(p.ngay_ket_thuc_du_kien)} · Ngân sách {p.ngan_sach_gio ? formatHours(p.ngan_sach_gio) : 'không giới hạn'}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
