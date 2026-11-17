import { useState } from 'react'
import { toast } from 'sonner'
import { errorMessage } from '@/api/client'
import type { Evaluation, KpiConfig, Period } from '@/api/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Sheet } from '@/components/ui/dialog'
import { Input, Textarea } from '@/components/ui/form'
import { Progress } from '@/components/ui/misc'
import { EVAL_STATUS } from '@/lib/labels'
import { useConfirmEvaluation, useDecideEvaluation, useSaveManual } from './queries'

const fmt = (n: number | null | undefined) => (n == null ? '—' : n.toLocaleString('vi-VN', { maximumFractionDigits: 2 }))

interface Props {
  projectId: number
  ev: Evaluation
  period: Period
  config: KpiConfig | undefined
  /** Người đang xem có quyền quản lý kỳ (nhập số liệu, tính điểm). */
  manage: boolean
  /** Người đang xem có quyền duyệt KPI và là quản lý. */
  canApprove: boolean
  /** Người đang xem chính là người được đánh giá. */
  isSelf: boolean
  onClose: () => void
}

export function EvaluationSheet({ projectId, ev, period, config, manage, canApprove, isSelf, onClose }: Props) {
  const confirm = useConfirmEvaluation(projectId)
  const decide = useDecideEvaluation(projectId)
  const saveManual = useSaveManual(projectId)
  const [note, setNote] = useState('')

  const sourceOf = (id: number) => config?.items.find((c) => c.ma_tieu_chi === id)?.nguon_du_lieu
  const manualRows = ev.chi_tiet.filter((d) => sourceOf(d.ma_tieu_chi) === 'MANUAL')
  // Số liệu thủ công chỉ sửa được khi kỳ đang mở và đánh giá chưa được duyệt.
  const editable = manage && period.trang_thai === 'OPEN' && ev.trang_thai !== 'APPROVED'
  const [drafts, setDrafts] = useState<Record<number, string>>(() =>
    Object.fromEntries(manualRows.map((d) => [d.ma_tieu_chi, d.gia_tri_thu_cong == null ? '' : String(d.gia_tri_thu_cong)])),
  )

  const saveDrafts = () => {
    const items = manualRows
      .filter((d) => drafts[d.ma_tieu_chi] !== '' && drafts[d.ma_tieu_chi] !== undefined)
      .map((d) => ({ ma_nd: ev.ma_nguoi_dung, ma_tieu_chi: d.ma_tieu_chi, gia_tri: Number(drafts[d.ma_tieu_chi]) }))
    if (items.length === 0) return
    saveManual.mutate(
      { periodId: period.ma_ky, items },
      { onSuccess: () => toast.success('Đã lưu số liệu. Bấm Tính điểm để cập nhật điểm.'), onError: (e) => toast.error(errorMessage(e)) },
    )
  }

  const onDone = (msg: string) => ({
    onSuccess: () => {
      toast.success(msg)
      onClose()
    },
    onError: (e: unknown) => toast.error(errorMessage(e)),
  })

  const showConfirm = isSelf && ev.trang_thai === 'PROVISIONAL'
  const showDecide = canApprove && !isSelf && ev.trang_thai === 'MEMBER_CONFIRMED'
  const footer = (
    <>
      {showConfirm ? (
        <Button variant="primary" loading={confirm.isPending} onClick={() => confirm.mutate({ periodId: period.ma_ky, ma_nd: ev.ma_nguoi_dung }, onDone('Đã xác nhận kết quả'))}>
          Xác nhận kết quả
        </Button>
      ) : null}
      {showDecide ? (
        <>
          <Button
            variant="danger"
            loading={decide.isPending}
            disabledReason={note.trim() ? null : 'Nhập nhận xét để từ chối.'}
            onClick={() => decide.mutate({ periodId: period.ma_ky, ma_nd: ev.ma_nguoi_dung, approve: false, nhan_xet: note.trim() }, onDone('Đã từ chối, đánh giá cần tính lại'))}
          >
            Từ chối
          </Button>
          <Button variant="primary" loading={decide.isPending} onClick={() => decide.mutate({ periodId: period.ma_ky, ma_nd: ev.ma_nguoi_dung, approve: true, nhan_xet: note.trim() || null }, onDone('Đã duyệt KPI'))}>
            Duyệt
          </Button>
        </>
      ) : null}
    </>
  )

  return (
    <Sheet
      open
      onOpenChange={(o) => !o && onClose()}
      title={ev.ho_ten}
      description={`${period.ten_ky} · ${period.tu_ngay} đến ${period.den_ngay}`}
      footer={showConfirm || showDecide ? footer : undefined}
    >
      <div className="flex flex-col gap-4 p-4">
        <div className="grid grid-cols-4 gap-2 text-center">
          <Stat label="Điểm trước" value={fmt(ev.diem_ky_truoc)} />
          <Stat label="Điểm gốc" value={fmt(ev.diem_goc)} />
          <Stat label="Điểm trừ" value={fmt(ev.diem_tru)} tone="danger" />
          <Stat label="Điểm tổng" value={fmt(ev.diem_tong)} strong />
        </div>
        <div className="flex items-center gap-2 text-sm">
          <Badge tone={EVAL_STATUS[ev.trang_thai].tone}>{EVAL_STATUS[ev.trang_thai].text}</Badge>
          {ev.ngay_duyet ? <span className="text-muted">Duyệt ngày {ev.ngay_duyet}</span> : null}
          {ev.ngay_xac_nhan ? <span className="text-muted">Xác nhận ngày {ev.ngay_xac_nhan}</span> : null}
        </div>

        <div className="overflow-hidden rounded-md border">
          <table className="w-full text-left text-sm">
            <thead className="bg-surface-2 text-xs text-muted">
              <tr>
                <th className="px-3 py-2 font-medium">Tiêu chí</th>
                <th className="px-3 py-2 text-right font-medium">Trọng số</th>
                <th className="px-3 py-2 text-right font-medium">Giá trị</th>
                <th className="w-32 px-3 py-2 font-medium">Đạt</th>
              </tr>
            </thead>
            <tbody>
              {ev.chi_tiet.map((d) => {
                const manual = sourceOf(d.ma_tieu_chi) === 'MANUAL'
                const value = d.gia_tri_thu_cong ?? d.gia_tri_tu_dong
                return (
                  <tr key={d.ma_tieu_chi} className="border-t">
                    <td className="px-3 py-2">
                      <span className="font-medium">{d.ten_tieu_chi}</span>
                      <span className="block text-xs text-muted">Chỉ tiêu {fmt(d.chi_tieu)}</span>
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">{fmt(d.trong_so)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {editable && manual ? (
                        <Input
                          type="number"
                          min={0}
                          step="any"
                          className="ml-auto w-24 text-right"
                          aria-label={`Giá trị ${d.ten_tieu_chi}`}
                          value={drafts[d.ma_tieu_chi] ?? ''}
                          onChange={(e) => setDrafts((s) => ({ ...s, [d.ma_tieu_chi]: e.target.value }))}
                        />
                      ) : (
                        fmt(value)
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <Progress className="flex-1" value={d.ty_le_dat ?? 0} />
                        <span className="w-10 text-right text-xs text-muted tabular-nums">{d.ty_le_dat == null ? '—' : `${fmt(d.ty_le_dat)}%`}</span>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {editable && manualRows.length > 0 ? (
          <div className="flex items-center justify-between gap-2 rounded-md bg-surface-2 p-3 text-sm">
            <span className="text-muted">Lưu số liệu thủ công, rồi bấm Tính điểm ở trang kỳ để cập nhật điểm.</span>
            <Button size="sm" loading={saveManual.isPending} onClick={saveDrafts}>
              Lưu số liệu
            </Button>
          </div>
        ) : null}

        {canApprove && !isSelf && ev.trang_thai === 'MEMBER_CONFIRMED' ? (
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-muted">Nhận xét (bắt buộc khi từ chối)</span>
            <Textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Ví dụ: cần kiểm tra lại số giờ làm tháng 10" />
          </label>
        ) : null}

        {ev.nhan_xet ? (
          <div className="rounded-md border p-3 text-sm">
            <p className="text-xs font-medium text-muted">Nhận xét trước đó</p>
            <p className="whitespace-pre-wrap">{ev.nhan_xet}</p>
          </div>
        ) : null}
      </div>
    </Sheet>
  )
}

function Stat({ label, value, tone, strong }: { label: string; value: string; tone?: 'danger'; strong?: boolean }) {
  return (
    <div className="rounded-md bg-surface-2 px-2 py-2">
      <p className="text-xs text-muted">{label}</p>
      <p className={`tabular-nums ${strong ? 'text-lg font-semibold' : 'font-medium'} ${tone === 'danger' ? 'text-danger' : ''}`}>{value}</p>
    </div>
  )
}
