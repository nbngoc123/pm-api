import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { subDays } from 'date-fns'
import { Pencil, Trash2 } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'
import { api, errorMessage } from '@/api/client'
import type { Page as Paged, Task, Timesheet, TimesheetSummary } from '@/api/types'
import { Page } from '@/components/layout/Page'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { Field, Input, Textarea } from '@/components/ui/form'
import { Card, EmptyState, ErrorState, PageLoader, Stat } from '@/components/ui/misc'
import { useOpenTask } from '@/features/tasks/useOpenTask'
import { formatDate, formatHours, formatTime, parseUtc, toDateInput, toDateTimeInput } from '@/lib/format'
import { toFormErrors } from '@/lib/formErrors'

/** Backend chỉ cho sửa hoặc xóa bản ghi trong 7 ngày (TIMESHEET_EDIT_DAYS). */
const EDIT_WINDOW_DAYS = 7

export function MyTimesheetsPage() {
  const qc = useQueryClient()
  const openTask = useOpenTask()
  const [today] = useState(() => new Date())
  const [from, setFrom] = useState(() => toDateInput(subDays(today, 29)))
  const [to, setTo] = useState(() => toDateInput(today))
  const [editing, setEditing] = useState<Timesheet | null>(null)
  const range = { tu_ngay: from, den_ngay: to }

  const list = useQuery({ queryKey: ['my-timesheets', 'list', range], queryFn: () => api.get<Paged<Timesheet>>('/me/timesheets', { ...range, size: 200 }) })
  const summary = useQuery({ queryKey: ['my-timesheets', 'summary', range], queryFn: () => api.get<TimesheetSummary>('/me/timesheets/summary', range) })
  const items = list.data?.items ?? []

  // Bản ghi giờ chỉ có mã công việc; lấy thêm tên để hiển thị.
  const taskIds = [...new Set(items.map((t) => t.ma_cv))]
  const tasks = useQueries({
    queries: taskIds.map((id) => ({ queryKey: ['task', id, 'info'], queryFn: () => api.get<Task>(`/tasks/${id}`), staleTime: 5 * 60_000 })),
  })
  const taskName = new Map(taskIds.map((id, i) => [id, tasks[i]?.data?.ten_cv]))

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['my-timesheets'] })
    qc.invalidateQueries({ queryKey: ['dashboard'] })
  }
  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/timesheets/${id}`),
    onSuccess: () => {
      toast.success('Đã xóa bản ghi giờ')
      refresh()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const lockBefore = subDays(today, EDIT_WINDOW_DAYS)
  return (
    <Page
      crumbs={[{ label: 'Giờ làm của tôi' }]}
      title="Giờ làm của tôi"
      actions={
        <>
          <Input type="date" className="w-36" value={from} max={to} onChange={(e) => setFrom(e.target.value)} aria-label="Từ ngày" />
          <span className="text-muted">đến</span>
          <Input type="date" className="w-36" value={to} min={from} onChange={(e) => setTo(e.target.value)} aria-label="Đến ngày" />
        </>
      }
    >
      <div className="mx-auto flex max-w-5xl flex-col gap-4">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
          <Stat label="Tổng giờ trong khoảng" value={summary.data ? summary.data.tong_gio : '—'} />
          <Stat label="Số bản ghi" value={list.data ? list.data.total : '—'} />
          <Stat label="Số dự án có ghi giờ" value={summary.data ? summary.data.theo_du_an.length : '—'} />
        </div>

        <Card className="overflow-x-auto">
          {list.isPending ? (
            <PageLoader />
          ) : list.isError ? (
            <ErrorState error={list.error} onRetry={list.refetch} />
          ) : items.length === 0 ? (
            <EmptyState title="Chưa có giờ làm trong khoảng này" description="Mở một công việc được giao cho bạn rồi chọn Ghi giờ." />
          ) : (
            <table className="w-full text-left">
              <thead className="border-b bg-surface-2 text-xs text-muted">
                <tr>
                  <th className="px-4 py-2 font-medium">Ngày</th>
                  <th className="px-4 py-2 font-medium">Thời gian</th>
                  <th className="px-4 py-2 font-medium">Công việc</th>
                  <th className="px-4 py-2 font-medium">Nội dung</th>
                  <th className="px-4 py-2 text-right font-medium">Số giờ</th>
                  <th className="w-20 px-4 py-2" />
                </tr>
              </thead>
              <tbody>
                {items.map((t) => {
                  const locked = parseUtc(t.bat_dau) < lockBefore ? `Chỉ sửa hoặc xóa được trong ${EDIT_WINDOW_DAYS} ngày.` : null
                  return (
                    <tr key={t.ma_nk} className="border-b last:border-0">
                      <td className="px-4 py-2 tabular-nums">{formatDate(toDateInput(parseUtc(t.bat_dau)))}</td>
                      <td className="px-4 py-2 text-muted tabular-nums">
                        {formatTime(t.bat_dau)} – {formatTime(t.ket_thuc)}
                      </td>
                      <td className="px-4 py-2">
                        <button type="button" className="text-left text-primary hover:underline" onClick={() => openTask(t.ma_cv)}>
                          {taskName.get(t.ma_cv) ?? `Công việc #${t.ma_cv}`}
                        </button>
                      </td>
                      <td className="max-w-xs truncate px-4 py-2 text-muted">{t.noi_dung ?? '—'}</td>
                      <td className="px-4 py-2 text-right font-medium tabular-nums">{formatHours(t.so_gio)}</td>
                      <td className="px-4 py-1">
                        <div className="flex justify-end">
                          <Button variant="ghost" size="icon" aria-label="Sửa bản ghi giờ" disabledReason={locked} onClick={() => setEditing(t)}>
                            <Pencil />
                          </Button>
                          <Button variant="ghost" size="icon" aria-label="Xóa bản ghi giờ" disabledReason={locked} onClick={() => confirm('Xóa bản ghi giờ này?') && remove.mutate(t.ma_nk)}>
                            <Trash2 />
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
      </div>
      {editing ? <EditTimesheetDialog entry={editing} onClose={() => setEditing(null)} onSaved={refresh} /> : null}
    </Page>
  )
}

function EditTimesheetDialog({ entry, onClose, onSaved }: { entry: Timesheet; onClose: () => void; onSaved: () => void }) {
  const [start, setStart] = useState(toDateTimeInput(parseUtc(entry.bat_dau)))
  const [end, setEnd] = useState(toDateTimeInput(parseUtc(entry.ket_thuc)))
  const [note, setNote] = useState(entry.noi_dung ?? '')
  const save = useMutation({
    mutationFn: () =>
      api.patch(`/timesheets/${entry.ma_nk}`, { bat_dau: new Date(start).toISOString(), ket_thuc: new Date(end).toISOString(), noi_dung: note || null }),
    onSuccess: () => {
      toast.success('Đã lưu bản ghi giờ')
      onSaved()
      onClose()
    },
  })
  const errors = save.error ? toFormErrors(save.error) : null

  function submit(e: FormEvent) {
    e.preventDefault()
    save.mutate()
  }

  return (
    <Dialog
      open
      onOpenChange={onClose}
      title="Sửa bản ghi giờ"
      footer={
        <>
          <Button onClick={onClose}>Hủy</Button>
          <Button variant="primary" type="submit" form="edit-timesheet" loading={save.isPending}>
            Lưu thay đổi
          </Button>
        </>
      }
    >
      <form id="edit-timesheet" onSubmit={submit} className="flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Bắt đầu" error={errors?.fields.bat_dau}>
            <Input type="datetime-local" value={start} max={end} onChange={(e) => setStart(e.target.value)} required />
          </Field>
          <Field label="Kết thúc" error={errors?.fields.ket_thuc}>
            <Input type="datetime-local" value={end} min={start} onChange={(e) => setEnd(e.target.value)} required />
          </Field>
        </div>
        <Field label="Nội dung đã làm">
          <Textarea value={note} onChange={(e) => setNote(e.target.value)} />
        </Field>
        {errors?.form ? <p className="text-sm text-danger">{errors.form}</p> : null}
      </form>
    </Dialog>
  )
}
