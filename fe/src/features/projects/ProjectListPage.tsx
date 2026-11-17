import { Plus, Search } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { ProjectStatus } from '@/api/types'
import { useAuth } from '@/auth/useAuth'
import { Page } from '@/components/layout/Page'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input, Select } from '@/components/ui/form'
import { Card, EmptyState, ErrorState, PageLoader } from '@/components/ui/misc'
import { formatDate, formatHours } from '@/lib/format'
import { PROJECT_STATUS } from '@/lib/labels'
import { CreateProjectDialog } from './CreateProjectDialog'
import { useProjects } from './queries'

export function ProjectListPage() {
  const { can } = useAuth()
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [status, setStatus] = useState<ProjectStatus | ''>('')
  const [creating, setCreating] = useState(false)
  const projects = useProjects({ q, trang_thai: status })

  return (
    <Page
      crumbs={[{ label: 'Dự án' }]}
      title="Dự án"
      actions={
        <Button variant="primary" onClick={() => setCreating(true)} disabledReason={can('project.create') ? null : 'Chỉ Ban giám đốc mới tạo được dự án.'}>
          <Plus />
          Tạo dự án
        </Button>
      }
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-3">
        <div className="flex gap-2">
          <div className="relative w-72">
            <Search className="pointer-events-none absolute top-2 left-2.5 size-4 text-subtle" />
            <Input className="pl-8" placeholder="Tìm theo tên dự án" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Tìm dự án" />
          </div>
          <Select className="w-44" value={status} onChange={(e) => setStatus(e.target.value as ProjectStatus | '')} aria-label="Lọc theo trạng thái">
            <option value="">Mọi trạng thái</option>
            {Object.entries(PROJECT_STATUS).map(([k, v]) => (
              <option key={k} value={k}>
                {v.text}
              </option>
            ))}
          </Select>
        </div>

        <Card className="overflow-hidden">
          {projects.isPending ? (
            <PageLoader />
          ) : projects.isError ? (
            <ErrorState error={projects.error} onRetry={projects.refetch} />
          ) : projects.data.items.length === 0 ? (
            <EmptyState
              title={q || status ? 'Không có dự án nào khớp bộ lọc' : 'Bạn chưa tham gia dự án nào'}
              description={q || status ? undefined : 'Dự án sẽ hiện ở đây khi bạn được thêm làm thành viên.'}
            />
          ) : (
            <table className="w-full text-left">
              <thead className="border-b bg-surface-2 text-xs text-muted">
                <tr>
                  <th className="px-4 py-2 font-medium">Tên dự án</th>
                  <th className="px-4 py-2 font-medium">Trạng thái</th>
                  <th className="px-4 py-2 font-medium">Thời gian</th>
                  <th className="px-4 py-2 text-right font-medium">Ngân sách giờ</th>
                </tr>
              </thead>
              <tbody>
                {projects.data.items.map((p) => (
                  <tr
                    key={p.ma_du_an}
                    tabIndex={0}
                    onClick={() => navigate(`/projects/${p.ma_du_an}`)}
                    onKeyDown={(e) => e.key === 'Enter' && navigate(`/projects/${p.ma_du_an}`)}
                    className="cursor-pointer border-b last:border-0 hover:bg-surface-2"
                  >
                    <td className="px-4 py-2.5">
                      <p className="font-medium">{p.ten_du_an}</p>
                      {p.muc_tieu ? <p className="max-w-md truncate text-xs text-muted">{p.muc_tieu}</p> : null}
                    </td>
                    <td className="px-4 py-2.5">
                      <Badge tone={PROJECT_STATUS[p.trang_thai].tone}>{PROJECT_STATUS[p.trang_thai].text}</Badge>
                    </td>
                    <td className="px-4 py-2.5 text-muted tabular-nums">
                      {formatDate(p.ngay_bat_dau)} – {formatDate(p.ngay_ket_thuc_du_kien)}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{p.ngan_sach_gio ? formatHours(p.ngan_sach_gio) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
      <CreateProjectDialog open={creating} onOpenChange={setCreating} />
    </Page>
  )
}
