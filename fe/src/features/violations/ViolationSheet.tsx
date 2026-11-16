import { useState } from 'react'
import { toast } from 'sonner'
import { errorMessage } from '@/api/client'
import type { Violation } from '@/api/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Sheet } from '@/components/ui/dialog'
import { formatDateTime } from '@/lib/format'
import { VIOLATION_STATUS } from '@/lib/labels'
import { ConcludeDialog, ExplainDialog } from './ViolationDialogs'
import { useNotifyViolator } from './queries'

interface Props {
  projectId: number
  violation: Violation
  violatorName: string
  taskName: string
  ruleName: string
  /** Số vi phạm trước đó của cùng người (không tính hồ sơ đang mở và hồ sơ đã bác bỏ). */
  priorCount: number
  priorConfirmed: number
  /** Người đang xem có quyền ghi nhận vi phạm (trưởng nhóm, quản lý dự án). */
  canCreate: boolean
  /** Người đang xem có quyền kết luận: quản lý dự án, hoặc quản lý trực tiếp của người vi phạm. */
  canConclude: boolean
  isViolator: boolean
  /** Chỉ quản lý thấy lịch sử vi phạm của người khác. */
  showHistory: boolean
  /** Đã quá hạn giải trình, do trang cha tính để tránh đọc giờ hệ thống trong lúc render. */
  overdue: boolean
  onFilterPerson: () => void
  onClose: () => void
}

export function ViolationSheet({ projectId, violation: v, violatorName, taskName, ruleName, priorCount, priorConfirmed, canCreate, canConclude, isViolator, showHistory, overdue, onFilterPerson, onClose }: Props) {
  const notify = useNotifyViolator(projectId)
  const [dialog, setDialog] = useState<'explain' | 'conclude' | null>(null)
  const canExplain = isViolator && (v.trang_thai === 'PENDING_EXPLANATION' || v.trang_thai === 'EXPLAINED')
  // Backend chỉ cho kết luận khi đã giải trình hoặc đã quá hạn giải trình.
  const canDecide = canConclude && (v.trang_thai === 'EXPLAINED' || overdue)
  const status = VIOLATION_STATUS[v.trang_thai]

  const footer = (
    <>
      {canCreate && v.trang_thai === 'DRAFT' ? (
        <Button
          variant="primary"
          loading={notify.isPending}
          onClick={() => notify.mutate(v.ma_vp, { onSuccess: () => toast.success('Đã gửi yêu cầu giải trình cho nhân viên'), onError: (e) => toast.error(errorMessage(e)) })}
        >
          Gửi yêu cầu giải trình
        </Button>
      ) : null}
      {canExplain ? <Button variant="primary" onClick={() => setDialog('explain')}>Gửi giải trình</Button> : null}
      {canDecide ? (
        <Button variant="primary" onClick={() => setDialog('conclude')}>
          Kết luận
        </Button>
      ) : null}
    </>
  )
  const hasActions = (canCreate && v.trang_thai === 'DRAFT') || canExplain || canDecide

  return (
    <Sheet
      open
      onOpenChange={(o) => !o && onClose()}
      title={violatorName}
      description={`${ruleName} · ${taskName}`}
      footer={hasActions ? footer : undefined}
    >
      <div className="flex flex-col gap-4 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={status.tone}>{status.text}</Badge>
          {overdue ? <Badge tone="danger">Quá hạn giải trình</Badge> : null}
          {v.diem_tru != null ? <span className="text-sm text-muted">Điểm trừ: <span className="font-medium text-danger">−{v.diem_tru}</span></span> : null}
        </div>

        {/* Lịch sử: giúp quản lý biết người này tái phạm lần thứ mấy trước khi quyết định. */}
        {showHistory ? (
        <button
          type="button"
          onClick={onFilterPerson}
          className="rounded-md bg-surface-2 px-3 py-2 text-left text-sm hover:bg-neutral-soft"
        >
          {priorCount > 0 ? (
            <>
              Nhân viên này đã có <span className="font-semibold">{priorCount}</span> vi phạm trong dự án
              {priorConfirmed > 0 ? ` (${priorConfirmed} đã xử phạt)` : ''}. Bấm để xem các vi phạm đó.
            </>
          ) : (
            'Đây là vi phạm đầu tiên của nhân viên này trong dự án.'
          )}
        </button>
        ) : null}

        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-xs text-muted">Ghi nhận lúc</dt>
            <dd>{formatDateTime(v.thoi_diem)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Hạn giải trình</dt>
            <dd className={overdue ? 'text-danger' : undefined}>{v.han_giai_trinh ? formatDateTime(v.han_giai_trinh) : '—'}</dd>
          </div>
        </dl>

        <section>
          <h3 className="mb-1 text-xs font-medium text-muted">Mô tả vi phạm</h3>
          <p className="text-sm whitespace-pre-wrap">{v.noi_dung}</p>
        </section>

        <section>
          <h3 className="mb-2 text-xs font-medium text-muted">Giải trình ({v.giai_trinh.length})</h3>
          {v.giai_trinh.length === 0 ? (
            <p className="text-sm text-subtle">Chưa có giải trình nào.</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {v.giai_trinh.map((g) => (
                <li key={g.ma_gt} className="rounded-md border p-3 text-sm">
                  <p className="text-xs text-muted">{formatDateTime(g.thoi_diem_gui)}</p>
                  <p className="mt-1 whitespace-pre-wrap">{g.noi_dung}</p>
                  {g.duong_dan_bang_chung ? (
                    <a href={g.duong_dan_bang_chung} target="_blank" rel="noreferrer" className="mt-1 inline-block text-primary hover:underline">
                      Xem bằng chứng
                    </a>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </section>

        {v.ket_luan ? (
          <section className="rounded-md border p-3 text-sm">
            <h3 className="mb-1 text-xs font-medium text-muted">Kết luận {v.ngay_xu_ly ? `ngày ${v.ngay_xu_ly}` : ''}</h3>
            <p className="whitespace-pre-wrap">{v.ket_luan}</p>
          </section>
        ) : null}
      </div>

      {dialog === 'explain' ? <ExplainDialog projectId={projectId} violation={v} onClose={() => setDialog(null)} /> : null}
      {dialog === 'conclude' ? <ConcludeDialog projectId={projectId} violation={v} onClose={() => setDialog(null)} /> : null}
    </Sheet>
  )
}
