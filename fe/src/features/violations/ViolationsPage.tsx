import { Plus } from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { Violation } from '@/api/types'
import { useAuth } from '@/auth/useAuth'
import { Page } from '@/components/layout/Page'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/form'
import { Avatar, Card, EmptyState, ErrorState, PageLoader } from '@/components/ui/misc'
import { Pagination } from '@/components/ui/pagination'
import { useMembers } from '@/features/projects/queries'
import { useProjectContext } from '@/features/projects/projectContext'
import { useProjectTasks } from '@/features/tasks/queries'
import { formatDate, parseUtc } from '@/lib/format'
import { VIOLATION_STATUS } from '@/lib/labels'
import { cn } from '@/lib/utils'
import { ViolationSheet } from './ViolationSheet'
import { CreateViolationDialog } from './ViolationDialogs'
import { useRules, useViolations } from './queries'

type Tab = 'ALL' | 'DRAFT' | 'PENDING_EXPLANATION' | 'EXPLAINED' | 'CONCLUDED'

const TABS: { id: Tab; label: string }[] = [
  { id: 'ALL', label: 'Tất cả' },
  { id: 'DRAFT', label: 'Chờ gửi yêu cầu' },
  { id: 'PENDING_EXPLANATION', label: 'Chờ giải trình' },
  { id: 'EXPLAINED', label: 'Đã giải trình' },
  { id: 'CONCLUDED', label: 'Đã kết luận' },
]

const isOverdue = (v: Violation) => v.trang_thai === 'PENDING_EXPLANATION' && !!v.han_giai_trinh && parseUtc(v.han_giai_trinh) < new Date()
const matchesTab = (v: Violation, tab: Tab) =>
  tab === 'ALL' ? true : tab === 'CONCLUDED' ? v.trang_thai === 'CONFIRMED' || v.trang_thai === 'DISMISSED' : v.trang_thai === tab

export function ViolationsPage() {
  const ctx = useProjectContext()
  const { project, can, readOnly } = ctx
  const { user } = useAuth()
  const [params, setParams] = useSearchParams()
  const violations = useViolations(project.ma_du_an)
  const members = useMembers(project.ma_du_an)
  const tasks = useProjectTasks(project.ma_du_an)
  const rules = useRules()
  const [creating, setCreating] = useState(false)
  const [page, setPage] = useState(1)
  const [size, setSize] = useState(20)

  const tab = (params.get('tt') ?? 'ALL') as Tab
  const person = params.get('nv') ? Number(params.get('nv')) : null
  const vpKey = params.get('vp') ? Number(params.get('vp')) : null
  const update = (changes: Record<string, string | null>) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        for (const [k, v] of Object.entries(changes)) {
          if (v === null) next.delete(k)
          else next.set(k, v)
        }
        return next
      },
      { replace: true },
    )

  if (violations.isPending) return <PageLoader />
  if (violations.isError) {
    return (
      <Page crumbs={[{ label: 'Dự án', to: '/projects' }, { label: project.ten_du_an, to: `/projects/${project.ma_du_an}` }, { label: 'Vi phạm' }]} title="Vi phạm">
        <ErrorState error={violations.error} onRetry={violations.refetch} />
      </Page>
    )
  }

  const all = violations.data
  const names = new Map(members.data?.map((m) => [m.ma_nguoi_dung, m.ho_ten]))
  const taskNames = new Map(tasks.data?.map((t) => [t.ma_cv, t.ten_cv]))
  const ruleNames = new Map(rules.data?.map((r) => [r.ma_qd, r.ten_quy_dinh]))

  const manage = can('violation.create') && !readOnly
  const canConcludeAny = can('violation.conclude') && user?.loai === 'QUAN_LY' && !readOnly
  const filtered = all.filter((v) => matchesTab(v, tab) && (person === null || v.ma_nd === person))
  const rows = filtered.slice((page - 1) * size, page * size)
  const current = all.find((v) => v.ma_vp === vpKey) ?? null
  const overdueCount = all.filter(isOverdue).length

  /** Số vi phạm trước đó của cùng người, không tính hồ sơ bác bỏ và hồ sơ đang mở. */
  const historyFor = (v: Violation) => {
    const others = all.filter((o) => o.ma_nd === v.ma_nd && o.ma_vp !== v.ma_vp)
    return {
      priorCount: others.filter((o) => o.trang_thai !== 'DISMISSED').length,
      priorConfirmed: others.filter((o) => o.trang_thai === 'CONFIRMED').length,
    }
  }

  return (
    <Page
      flush
      crumbs={[{ label: 'Dự án', to: '/projects' }, { label: project.ten_du_an, to: `/projects/${project.ma_du_an}` }, { label: 'Vi phạm' }]}
      title="Vi phạm"
      actions={
        <Button variant="primary" disabledReason={manage ? null : readOnly ? 'Dự án đã hoàn thành hoặc đã đóng nên không ghi nhận thêm.' : 'Cần quyền trưởng nhóm hoặc quản lý dự án.'} onClick={() => setCreating(true)}>
          <Plus />
          Ghi nhận vi phạm
        </Button>
      }
      toolbar={
        <div className="flex flex-wrap items-end justify-between gap-x-4">
          <div role="tablist" aria-label="Lọc theo trạng thái xử lý" className="flex flex-wrap gap-4">
            {TABS.map((t) => {
              const n = all.filter((v) => matchesTab(v, t.id)).length
              const warn = t.id === 'PENDING_EXPLANATION' && overdueCount > 0
              return (
                <button
                  key={t.id}
                  type="button"
                  role="tab"
                  aria-selected={tab === t.id}
                  onClick={() => {
                    setPage(1)
                    update({ tt: t.id === 'ALL' ? null : t.id })
                  }}
                  className={cn('-mb-px flex items-center gap-1.5 border-b-2 border-transparent px-0.5 py-2 text-sm text-muted hover:text-fg', tab === t.id && 'border-primary font-medium text-primary hover:text-primary')}
                >
                  {t.label}
                  <span
                    title={warn ? `${overdueCount} hồ sơ đã quá hạn giải trình` : undefined}
                    className={cn('rounded-full px-1.5 text-xs tabular-nums', warn ? 'bg-danger-soft text-danger-soft-fg font-medium' : 'bg-neutral-soft text-neutral-soft-fg')}
                  >
                    {n}
                  </span>
                </button>
              )
            })}
          </div>
          <div className="flex items-center gap-2 pb-2">
            <Select
              className="w-48"
              aria-label="Lọc theo nhân viên"
              value={person ?? ''}
              onChange={(e) => {
                setPage(1)
                update({ nv: e.target.value || null, vp: null })
              }}
            >
              <option value="">Mọi nhân viên</option>
              {members.data?.map((m) => (
                <option key={m.ma_nguoi_dung} value={m.ma_nguoi_dung}>
                  {m.ho_ten}
                </option>
              ))}
            </Select>
          </div>
        </div>
      }
    >
      {all.length === 0 ? (
        <EmptyState
          title="Chưa có vi phạm nào được ghi nhận"
          description="Vi phạm được ghi ở dạng nháp, sau đó gửi yêu cầu giải trình cho nhân viên."
          action={manage ? <Button variant="primary" onClick={() => setCreating(true)}><Plus />Ghi nhận vi phạm</Button> : null}
        />
      ) : filtered.length === 0 ? (
        <EmptyState title="Không có hồ sơ nào khớp bộ lọc" />
      ) : (
        <div className="flex flex-col gap-3 overflow-y-auto p-4">
          <Card className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="border-b bg-surface-2 text-xs text-muted">
                <tr>
                  <th className="px-4 py-2 font-medium">Nhân viên</th>
                  <th className="px-4 py-2 font-medium">Quy định</th>
                  <th className="px-4 py-2 font-medium">Công việc</th>
                  <th className="px-4 py-2 font-medium">Ghi nhận</th>
                  <th className="px-4 py-2 text-right font-medium">Điểm trừ</th>
                  <th className="px-4 py-2 font-medium">Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((v) => {
                  const st = VIOLATION_STATUS[v.trang_thai]
                  const late = isOverdue(v)
                  return (
                    <tr
                      key={v.ma_vp}
                      tabIndex={0}
                      onClick={() => update({ vp: String(v.ma_vp) })}
                      onKeyDown={(k) => k.key === 'Enter' && update({ vp: String(v.ma_vp) })}
                      className={cn('cursor-pointer border-b last:border-0 hover:bg-surface-2', current?.ma_vp === v.ma_vp && 'bg-primary-soft hover:bg-primary-soft')}
                    >
                      <td className="px-4 py-2.5">
                        <div className="flex items-center gap-2">
                          <Avatar name={names.get(v.ma_nd) ?? '?'} />
                          <span className="font-medium">{names.get(v.ma_nd) ?? `#${v.ma_nd}`}</span>
                        </div>
                      </td>
                      <td className="px-4 py-2.5 text-muted">{ruleNames.get(v.ma_qd) ?? `#${v.ma_qd}`}</td>
                      <td className="max-w-48 truncate px-4 py-2.5 text-muted">{taskNames.get(v.ma_cv) ?? `#${v.ma_cv}`}</td>
                      <td className="px-4 py-2.5 text-muted tabular-nums">{formatDate(v.thoi_diem.slice(0, 10))}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-danger">{v.diem_tru != null ? `−${v.diem_tru}` : '—'}</td>
                      <td className="px-4 py-2.5">
                        <div className="flex items-center gap-1.5">
                          <Badge tone={st.tone}>{st.text}</Badge>
                          {late ? <Badge tone="danger">Quá hạn</Badge> : null}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </Card>
          <Pagination
            page={page}
            size={size}
            total={filtered.length}
            onPageChange={setPage}
            onSizeChange={(s) => {
              setSize(s)
              setPage(1)
            }}
          />
        </div>
      )}

      {current ? (
        <ViolationSheet
          key={current.ma_vp}
          projectId={project.ma_du_an}
          violation={current}
          violatorName={names.get(current.ma_nd) ?? `#${current.ma_nd}`}
          taskName={taskNames.get(current.ma_cv) ?? `#${current.ma_cv}`}
          ruleName={ruleNames.get(current.ma_qd) ?? `#${current.ma_qd}`}
          priorCount={historyFor(current).priorCount}
          priorConfirmed={historyFor(current).priorConfirmed}
          canCreate={manage}
          canConclude={canConcludeAny && current.ma_nd !== user?.ma_nd && (can('violation.conclude'))}
          isViolator={current.ma_nd === user?.ma_nd}
          showHistory={canConcludeAny || manage}
          overdue={isOverdue(current)}
          onFilterPerson={() => {
            setPage(1)
            update({ nv: String(current.ma_nd), vp: null })
          }}
          onClose={() => update({ vp: null })}
        />
      ) : null}
      {creating ? <CreateViolationDialog projectId={project.ma_du_an} onClose={() => setCreating(false)} /> : null}
    </Page>
  )
}
