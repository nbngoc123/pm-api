import { ChevronsLeft, ChevronsRight, Clock, FolderKanban, LayoutDashboard, LayoutGrid, UserCog, type LucideIcon } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '@/auth/useAuth'
import { Tooltip } from '@/components/ui/tooltip'
import { useLocalState } from '@/lib/useLocalState'
import { cn } from '@/lib/utils'
import { NotificationBell } from './NotificationBell'
import { UserMenu } from './UserMenu'

interface RailItem {
  to: string
  label: string
  icon: LucideIcon
  end?: boolean
}

export function AppShell() {
  const { user, can } = useAuth()
  const [expanded, setExpanded] = useLocalState<boolean>('pmkpi.rail', false)

  const items: RailItem[] = [
    { to: '/', label: 'Bảng điều khiển', icon: LayoutDashboard, end: true },
    { to: '/projects', label: 'Dự án', icon: FolderKanban },
    // Chỉ nhân viên mới ghi giờ; người loại quản lý không có màn hình này.
    ...(user?.loai === 'NHAN_VIEN' ? [{ to: '/timesheets', label: 'Giờ làm của tôi', icon: Clock }] : []),
    ...(can('report.portfolio') ? [{ to: '/portfolio', label: 'Portfolio', icon: LayoutGrid }] : []),
    ...(can('user.manage') ? [{ to: '/admin/users', label: 'Tài khoản', icon: UserCog }] : []),
  ]

  return (
    <div className="flex h-full">
      <nav
        aria-label="Điều hướng chính"
        className={cn('flex shrink-0 flex-col gap-1 bg-rail p-2 text-rail-fg', expanded ? 'w-48' : 'w-12')}
      >
        <div className="mb-2 flex h-8 items-center gap-2 px-1.5 text-white">
          <span className="flex size-5 shrink-0 items-center justify-center rounded bg-primary text-[11px] font-bold">P</span>
          {expanded ? <span className="truncate text-sm font-semibold">PM-KPI</span> : null}
        </div>
        {items.map((item) => (
          <RailLink key={item.to} item={item} expanded={expanded} />
        ))}
        <div className="flex-1" />
        <NotificationBell expanded={expanded} />
        <UserMenu expanded={expanded} />
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex h-8 items-center gap-2 rounded-md px-2 hover:bg-rail-active hover:text-white"
          aria-label={expanded ? 'Thu gọn menu' : 'Mở rộng menu'}
        >
          {expanded ? <ChevronsLeft className="size-4 shrink-0" /> : <ChevronsRight className="size-4 shrink-0" />}
          {expanded ? <span className="text-sm">Thu gọn</span> : null}
        </button>
      </nav>
      <div className="flex min-w-0 flex-1">
        <Outlet />
      </div>
    </div>
  )
}

function RailLink({ item, expanded }: { item: RailItem; expanded: boolean }) {
  const link = (
    <NavLink
      to={item.to}
      end={item.end}
      className={({ isActive }) =>
        cn('flex h-8 items-center gap-2 rounded-md px-2 hover:bg-rail-active hover:text-white', isActive && 'bg-rail-active text-white')
      }
    >
      <item.icon className="size-4 shrink-0" />
      {expanded ? <span className="truncate text-sm">{item.label}</span> : null}
    </NavLink>
  )
  return expanded ? link : (
    <Tooltip content={item.label} side="right">
      {link}
    </Tooltip>
  )
}
