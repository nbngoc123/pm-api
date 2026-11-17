import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { KeyRound, Lock, LockOpen, Plus, Search } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { api, errorMessage } from '@/api/client'
import type { Page as Paged, User } from '@/api/types'
import { useAuth } from '@/auth/useAuth'
import { Page } from '@/components/layout/Page'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Pagination } from '@/components/ui/pagination'
import { Input, Select } from '@/components/ui/form'
import { Avatar, Card, EmptyState, ErrorState, PageLoader } from '@/components/ui/misc'
import { SYSTEM_ROLE } from '@/lib/labels'
import { CreateUserDialog, ResetPasswordDialog } from './UserDialogs'

const STATUS = {
  ACTIVE: { text: 'Hoạt động', tone: 'success' },
  LOCKED: { text: 'Đã khóa', tone: 'danger' },
  INACTIVE: { text: 'Ngừng dùng', tone: 'neutral' },
} as const

export function UsersPage() {
  const qc = useQueryClient()
  const { user: me } = useAuth()
  const [q, setQ] = useState('')
  const [role, setRole] = useState('')
  const [creating, setCreating] = useState(false)
  const [resetting, setResetting] = useState<User | null>(null)
  const [page, setPage] = useState(1)
  const [size, setSize] = useState(20)

  const users = useQuery({
    queryKey: ['users', { q, role, page, size }],
    queryFn: () => api.get<Paged<User>>('/users', { q, vai_tro: role, page, size }),
  })
  const setStatus = useMutation({
    mutationFn: (v: { user: User; trang_thai: User['trang_thai'] }) => api.patch(`/users/${v.user.ma_nd}`, { trang_thai: v.trang_thai }),
    onSuccess: (_, v) => {
      toast.success(v.trang_thai === 'ACTIVE' ? `Đã mở khóa ${v.user.ho_ten}` : `Đã khóa ${v.user.ho_ten}`)
      qc.invalidateQueries({ queryKey: ['users'] })
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  return (
    <Page
      crumbs={[{ label: 'Quản trị' }, { label: 'Tài khoản' }]}
      title="Tài khoản người dùng"
      actions={
        <Button variant="primary" onClick={() => setCreating(true)}>
          <Plus />
          Tạo tài khoản
        </Button>
      }
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-3">
        <div className="flex gap-2">
          <div className="relative w-72">
            <Search className="pointer-events-none absolute top-2 left-2.5 size-4 text-subtle" />
            <Input className="pl-8" placeholder="Tìm theo tên hoặc email" value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} aria-label="Tìm tài khoản" />
          </div>
          <Select className="w-48" value={role} onChange={(e) => { setRole(e.target.value); setPage(1) }} aria-label="Lọc theo vai trò">
            <option value="">Mọi vai trò</option>
            {Object.entries(SYSTEM_ROLE).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </Select>
        </div>

        <Card className="overflow-x-auto">
          {users.isPending ? (
            <PageLoader />
          ) : users.isError ? (
            <ErrorState error={users.error} onRetry={users.refetch} />
          ) : users.data.items.length === 0 ? (
            <EmptyState title="Không có tài khoản nào khớp bộ lọc" />
          ) : (
            <table className="w-full text-left">
              <thead className="border-b bg-surface-2 text-xs text-muted">
                <tr>
                  <th className="px-4 py-2 font-medium">Người dùng</th>
                  <th className="px-4 py-2 font-medium">Vai trò hệ thống</th>
                  <th className="px-4 py-2 font-medium">Trạng thái</th>
                  <th className="px-4 py-2 text-right font-medium">Đơn giá giờ</th>
                  <th className="w-24 px-4 py-2" />
                </tr>
              </thead>
              <tbody>
                {users.data.items.map((u) => {
                  const active = u.trang_thai === 'ACTIVE'
                  return (
                    <tr key={u.ma_nd} className="border-b last:border-0">
                      <td className="px-4 py-2">
                        <div className="flex items-center gap-2.5">
                          <Avatar name={u.ho_ten} className="size-8 text-xs" />
                          <div className="min-w-0">
                            <p className="truncate font-medium">{u.ho_ten}</p>
                            <p className="truncate text-xs text-muted">{u.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-2">{SYSTEM_ROLE[u.vai_tro] ?? u.vai_tro}</td>
                      <td className="px-4 py-2">
                        <Badge tone={STATUS[u.trang_thai].tone}>{STATUS[u.trang_thai].text}</Badge>
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">{u.loai === 'NHAN_VIEN' ? `${u.don_gia_gio.toLocaleString('vi-VN')} đ` : '—'}</td>
                      <td className="px-4 py-1">
                        <div className="flex justify-end">
                          <Button variant="ghost" size="icon" aria-label={`Đặt lại mật khẩu của ${u.ho_ten}`} onClick={() => setResetting(u)}>
                            <KeyRound />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label={active ? `Khóa tài khoản ${u.ho_ten}` : `Mở khóa tài khoản ${u.ho_ten}`}
                            disabledReason={u.ma_nd === me?.ma_nd ? 'Bạn không tự khóa tài khoản của mình được.' : null}
                            onClick={() => setStatus.mutate({ user: u, trang_thai: active ? 'LOCKED' : 'ACTIVE' })}
                          >
                            {active ? <Lock /> : <LockOpen />}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </Card>
        <Pagination
          page={page}
          size={size}
          total={users.data?.total ?? 0}
          onPageChange={setPage}
          onSizeChange={(s) => { setSize(s); setPage(1) }}
        />
      </div>
      {creating ? <CreateUserDialog onClose={() => setCreating(false)} /> : null}
      {resetting ? <ResetPasswordDialog user={resetting} onClose={() => setResetting(null)} /> : null}
    </Page>
  )
}
