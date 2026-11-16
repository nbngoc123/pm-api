import { Flag, Home, ListChecks, ShieldAlert, Target, TrendingUp, Users, type LucideIcon } from 'lucide-react'
import { NavLink, Outlet, useParams } from 'react-router-dom'
import { Page } from '@/components/layout/Page'
import { Badge } from '@/components/ui/badge'
import { useAuth } from '@/auth/useAuth'
import { ErrorState, PageLoader } from '@/components/ui/misc'
import { PROJECT_ROLE, PROJECT_STATUS, SYSTEM_ROLE } from '@/lib/labels'
import { cn } from '@/lib/utils'
import type { ProjectContext } from './projectContext'
import { useProject, useProjectAccess } from './queries'

const NAV: { to: string; label: string; icon: LucideIcon; end?: boolean; perm?: string }[] = [
  { to: '', label: 'Tổng quan', icon: Home, end: true },
  { to: 'tasks', label: 'Công việc', icon: ListChecks },
  { to: 'milestones', label: 'Mốc', icon: Flag },
  { to: 'members', label: 'Thành viên', icon: Users },
  { to: 'kpi', label: 'KPI', icon: Target },
  { to: 'violations', label: 'Vi phạm', icon: ShieldAlert },
  { to: 'progress', label: 'Tiến độ', icon: TrendingUp, perm: 'report.project' },
]

export function ProjectLayout() {
  const projectId = Number(useParams().projectId)
  const project = useProject(projectId)
  const access = useProjectAccess(projectId)
  const { user } = useAuth()

  if (project.isPending || access.loading) return <PageLoader />
  if (project.isError) {
    return (
      <Page crumbs={[{ label: 'Dự án', to: '/projects' }]} title="Dự án">
        <ErrorState error={project.error} onRetry={project.refetch} />
      </Page>
    )
  }

  const p = project.data
  const readOnly = p.trang_thai === 'COMPLETED' || p.trang_thai === 'CLOSED'
  return (
    <>
      <aside className="flex w-52 shrink-0 flex-col gap-0.5 border-r bg-surface p-2">
        <div className="mb-2 px-2 pt-1">
          <p className="truncate font-semibold" title={p.ten_du_an}>
            {p.ten_du_an}
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-1">
            <Badge tone={PROJECT_STATUS[p.trang_thai].tone}>{PROJECT_STATUS[p.trang_thai].text}</Badge>
            <span className="text-xs text-muted">{access.role ? PROJECT_ROLE[access.role] : (SYSTEM_ROLE[user?.vai_tro ?? ''] ?? 'Chỉ xem')}</span>
          </div>
        </div>
        {NAV.filter((item) => !item.perm || access.can(item.perm)).map((item) => (
          <NavLink
            key={item.label}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              cn('flex h-8 items-center gap-2 rounded-md px-2 text-sm text-muted hover:bg-surface-2 hover:text-fg', isActive && 'bg-primary-soft text-primary-soft-fg hover:bg-primary-soft hover:text-primary-soft-fg')
            }
          >
            <item.icon className="size-4" />
            {item.label}
          </NavLink>
        ))}
      </aside>
      <Outlet context={{ project: p, readOnly, can: access.can } satisfies ProjectContext} />
    </>
  )
}
