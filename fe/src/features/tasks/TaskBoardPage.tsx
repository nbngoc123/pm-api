import { useQueryClient } from '@tanstack/react-query'
import { Plus, Search } from 'lucide-react'
import { useCallback, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { errorMessage } from '@/api/client'
import type { Priority, Task } from '@/api/types'
import { useAuth } from '@/auth/useAuth'
import { Page } from '@/components/layout/Page'
import { Button } from '@/components/ui/button'
import { Input, Select } from '@/components/ui/form'
import { EmptyState, ErrorState, PageLoader } from '@/components/ui/misc'
import { blockedReason, useProjectContext } from '@/features/projects/projectContext'
import { useMembers } from '@/features/projects/queries'
import { PRIORITY } from '@/lib/labels'
import { cn } from '@/lib/utils'
import { KanbanBoard } from './KanbanBoard'
import { usePendingReviews, usePrioritizedTasks, useProjectTasks, useTransition } from './queries'
import type { Actor, TaskAction } from './rules'
import { TaskBoardContext } from './TaskBoardContext'
import { ReviewDialog, TaskFormDialog } from './TaskDialogs'
import { TaskSheet } from './TaskSheet'
import { TaskTable } from './TaskTable'

type View = 'kanban' | 'table' | 'priority' | 'reviews'

export function TaskBoardPage() {
  const ctx = useProjectContext()
  const { project } = ctx
  const projectId = project.ma_du_an
  const { user } = useAuth()
  const qc = useQueryClient()
  const [params, setParams] = useSearchParams()
  const canReview = ctx.can('task.review')

  const requested = params.get('view') as View | null
  // Tab "Chờ duyệt" là màn hình cần quyền: không có quyền thì ẩn hẳn.
  const view: View = requested && (requested !== 'reviews' || canReview) ? requested : 'kanban'
  const openTaskId = Number(params.get('task')) || null

  const setParam = useCallback(
    (key: string, value: string | null) =>
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          if (value === null) next.delete(key)
          else next.set(key, value)
          return next
        },
        { replace: key === 'view' },
      ),
    [setParams],
  )

  const [search, setSearch] = useState('')
  const [priority, setPriority] = useState<Priority | ''>('')
  const [mineOnly, setMineOnly] = useState(false)
  const [assignee, setAssignee] = useState('')
  const [creating, setCreating] = useState(false)
  const [reviewing, setReviewing] = useState<{ task: Task; initial: 'APPROVED' | 'REJECTED' } | null>(null)

  const all = useProjectTasks(projectId)
  const prioritized = usePrioritizedTasks(projectId, view === 'priority')
  const pending = usePendingReviews(projectId, canReview)
  const members = useMembers(projectId)
  const transition = useTransition(projectId)

  const actor = useMemo<Actor>(() => ({ userId: user!.ma_nd, can: ctx.can, readOnly: ctx.readOnly }), [user, ctx.can, ctx.readOnly])
  const memberMap = useMemo(() => new Map(members.data?.map((m) => [m.ma_nguoi_dung, m])), [members.data])

  const run = useCallback(
    (task: Task, action: TaskAction) => {
      if (action.reason) return
      if (action.key === 'approve' || action.key === 'reject') {
        setReviewing({ task, initial: action.key === 'approve' ? 'APPROVED' : 'REJECTED' })
        return
      }
      if (action.key === 'cancel' && !confirm(`Hủy công việc "${task.ten_cv}"?`)) return
      // Cập nhật lạc quan để thẻ sang cột mới ngay; nếu backend từ chối, dữ liệu được tải lại và thẻ quay về.
      qc.setQueryData<Task[]>(['project', projectId, 'tasks'], (list) => list?.map((t) => (t.ma_cv === task.ma_cv ? { ...t, trang_thai: action.to } : t)))
      transition.mutate({ id: task.ma_cv, to: action.to }, { onError: (e) => toast.error(errorMessage(e)) })
    },
    [qc, projectId, transition],
  )

  const board = useMemo(
    () => ({ projectId, actor, members: memberMap, run, openTask: (id: number) => setParam('task', String(id)) }),
    [projectId, actor, memberMap, run, setParam],
  )

  const source = view === 'priority' ? prioritized : view === 'reviews' ? pending : all
  const tasks = useMemo(() => {
    const q = search.trim().toLowerCase()
    return (source.data ?? []).filter(
      (t) =>
        (!q || t.ten_cv.toLowerCase().includes(q)) &&
        (!priority || t.uu_tien === priority) &&
        (!mineOnly || t.assignees.includes(actor.userId)) &&
        (!assignee || t.assignees.includes(Number(assignee))),
    )
  }, [source.data, search, priority, mineOnly, assignee, actor.userId])

  const tabs: { id: View; label: string; count?: number }[] = [
    { id: 'kanban', label: 'Kanban' },
    { id: 'table', label: 'Bảng' },
    { id: 'priority', label: 'Ưu tiên' },
    ...(canReview ? [{ id: 'reviews' as const, label: 'Chờ duyệt', count: pending.data?.length }] : []),
  ]

  return (
    <TaskBoardContext.Provider value={board}>
      <Page
        flush
        crumbs={[{ label: 'Dự án', to: '/projects' }, { label: project.ten_du_an, to: `/projects/${projectId}` }, { label: 'Công việc' }]}
        title="Công việc"
        actions={
          <Button variant="primary" disabledReason={blockedReason(ctx, 'task.create', 'trưởng nhóm hoặc quản lý dự án')} onClick={() => setCreating(true)}>
            <Plus />
            Tạo công việc
          </Button>
        }
        toolbar={
          <div className="flex flex-wrap items-end justify-between gap-x-4">
            <div role="tablist" aria-label="Kiểu xem" className="flex gap-4">
              {tabs.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  role="tab"
                  aria-selected={view === t.id}
                  onClick={() => setParam('view', t.id === 'kanban' ? null : t.id)}
                  className={cn(
                    '-mb-px flex items-center gap-1.5 border-b-2 border-transparent px-0.5 py-2 text-sm text-muted hover:text-fg',
                    view === t.id && 'border-primary font-medium text-primary hover:text-primary',
                  )}
                >
                  {t.label}
                  {t.count ? <span className="rounded-full bg-purple-soft px-1.5 text-xs text-purple-soft-fg tabular-nums">{t.count}</span> : null}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 pb-2">
              <div className="relative w-52">
                <Search className="pointer-events-none absolute top-2 left-2.5 size-4 text-subtle" />
                <Input className="pl-8" placeholder="Tìm công việc" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Tìm công việc" />
              </div>
              <Select className="w-36" value={priority} onChange={(e) => setPriority(e.target.value as Priority | '')} aria-label="Lọc theo ưu tiên">
                <option value="">Mọi ưu tiên</option>
                {Object.entries(PRIORITY).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v.text}
                  </option>
                ))}
              </Select>
              <Select className="w-40" value={assignee} onChange={(e) => setAssignee(e.target.value)} aria-label="Lọc theo người thực hiện">
                <option value="">Mọi người làm</option>
                {members.data?.map((m) => (
                  <option key={m.ma_nguoi_dung} value={m.ma_nguoi_dung}>
                    {m.ho_ten}
                  </option>
                ))}
              </Select>
              <label className="flex items-center gap-1.5 text-sm whitespace-nowrap text-muted">
                <input type="checkbox" checked={mineOnly} onChange={(e) => setMineOnly(e.target.checked)} />
                Việc của tôi
              </label>
            </div>
          </div>
        }
      >
        {source.isPending ? (
          <PageLoader />
        ) : source.isError ? (
          <ErrorState error={source.error} onRetry={source.refetch} />
        ) : view === 'kanban' ? (
          <KanbanBoard tasks={tasks} />
        ) : tasks.length === 0 ? (
          <EmptyState
            title={view === 'reviews' ? 'Không có công việc nào chờ duyệt' : 'Không có công việc nào khớp'}
            description={view === 'reviews' ? 'Công việc được gửi duyệt sẽ hiện ở đây.' : 'Thử bỏ bớt bộ lọc, hoặc tạo công việc mới.'}
          />
        ) : (
          <div className="overflow-y-auto p-4">
            <TaskTable tasks={tasks} fixedOrder={view === 'priority'} />
          </div>
        )}
      </Page>

      {openTaskId ? <TaskSheet key={openTaskId} taskId={openTaskId} onClose={() => setParam('task', null)} /> : null}
      {creating ? <TaskFormDialog projectId={projectId} onClose={() => setCreating(false)} /> : null}
      {reviewing ? <ReviewDialog projectId={projectId} task={reviewing.task} initial={reviewing.initial} onClose={() => setReviewing(null)} /> : null}
    </TaskBoardContext.Provider>
  )
}
