import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from '@/auth/useAuth'
import { AppShell } from '@/components/layout/AppShell'
import { Page } from '@/components/layout/Page'
import { EmptyState, PageLoader } from '@/components/ui/misc'
import { UsersPage } from '@/features/admin/UsersPage'
import { LoginPage } from '@/features/auth/LoginPage'
import { DashboardPage } from '@/features/dashboard/DashboardPage'
import { KpiPage } from '@/features/kpi/KpiPage'
import { PortfolioPage } from '@/features/portfolio/PortfolioPage'
import { ProgressPage } from '@/features/progress/ProgressPage'
import { ViolationsPage } from '@/features/violations/ViolationsPage'
import { MembersPage } from '@/features/projects/MembersPage'
import { MilestonesPage } from '@/features/projects/MilestonesPage'
import { OverviewPage } from '@/features/projects/OverviewPage'
import { ProjectLayout } from '@/features/projects/ProjectLayout'
import { ProjectListPage } from '@/features/projects/ProjectListPage'
import { TaskBoardPage } from '@/features/tasks/TaskBoardPage'
import { MyTimesheetsPage } from '@/features/timesheets/MyTimesheetsPage'

function RequireAuth() {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <PageLoader />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  return <Outlet />
}

function NotFoundPage() {
  return (
    <Page crumbs={[{ label: 'PM-KPI' }]} title="Không tìm thấy trang này">
      <EmptyState title="Không tìm thấy trang này" description="Đường dẫn không tồn tại hoặc bạn không có quyền xem." />
    </Page>
  )
}

/** Màn hình cần quyền hệ thống: không có quyền thì coi như không tồn tại. */
function RequirePermission({ permission }: { permission: string }) {
  const { can } = useAuth()
  return can(permission) ? <Outlet /> : <NotFoundPage />
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route index element={<DashboardPage />} />
          <Route path="projects" element={<ProjectListPage />} />
          <Route path="projects/:projectId" element={<ProjectLayout />}>
            <Route index element={<OverviewPage />} />
            <Route path="tasks" element={<TaskBoardPage />} />
            <Route path="milestones" element={<MilestonesPage />} />
            <Route path="members" element={<MembersPage />} />
            <Route path="kpi" element={<KpiPage />} />
            <Route path="violations" element={<ViolationsPage />} />
            <Route path="progress" element={<ProgressPage />} />
          </Route>
          <Route path="timesheets" element={<MyTimesheetsPage />} />
          <Route element={<RequirePermission permission="report.portfolio" />}>
            <Route path="portfolio" element={<PortfolioPage />} />
          </Route>
          <Route element={<RequirePermission permission="user.manage" />}>
            <Route path="admin/users" element={<UsersPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  )
}
