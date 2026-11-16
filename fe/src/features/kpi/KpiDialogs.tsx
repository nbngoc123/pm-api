import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { Field, Input } from '@/components/ui/form'
import { toFormErrors } from '@/lib/formErrors'
import { useCreatePeriod, useSetConfig } from './queries'
import type { KpiConfig, KpiCriterion } from '@/api/types'

export function CreatePeriodDialog({ projectId, onClose, onCreated }: { projectId: number; onClose: () => void; onCreated: (id: number) => void }) {
  const create = useCreatePeriod(projectId)
  const [name, setName] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const errors = create.error ? toFormErrors(create.error) : null

  function submit(e: FormEvent) {
    e.preventDefault()
    create.mutate(
      { ten_ky: name, tu_ngay: from, den_ngay: to },
      {
        onSuccess: (p) => {
          toast.success('Đã tạo kỳ KPI')
          onCreated(p.ma_ky)
          onClose()
        },
      },
    )
  }

  return (
    <Dialog
      open
      onOpenChange={onClose}
      title="Tạo kỳ KPI"
      description="Kỳ không được trùng thời gian với kỳ khác trong cùng dự án."
      footer={
        <>
          <Button onClick={onClose}>Hủy</Button>
          <Button variant="primary" type="submit" form="create-period" loading={create.isPending}>
            Tạo kỳ
          </Button>
        </>
      }
    >
      <form id="create-period" onSubmit={submit} className="flex flex-col gap-3">
        <Field label="Tên kỳ" error={errors?.fields.ten_ky}>
          <Input value={name} onChange={(e) => setName(e.target.value)} required minLength={2} placeholder="Quý 4/2026" autoFocus />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Từ ngày" error={errors?.fields.tu_ngay}>
            <Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} required />
          </Field>
          <Field label="Đến ngày" error={errors?.fields.den_ngay}>
            <Input type="date" value={to} min={from || undefined} onChange={(e) => setTo(e.target.value)} required />
          </Field>
        </div>
        {errors?.form ? <p className="text-sm text-danger">{errors.form}</p> : null}
      </form>
    </Dialog>
  )
}

interface DraftRow {
  on: boolean
  trong_so: string
  chi_tieu: string
}

/** Chọn tiêu chí cho kỳ và phân bổ trọng số. Tổng trọng số phải bằng 100. */
export function ConfigDialog({
  projectId,
  periodId,
  criteria,
  config,
  onClose,
}: {
  projectId: number
  periodId: number
  criteria: KpiCriterion[]
  config: KpiConfig
  onClose: () => void
}) {
  const save = useSetConfig(projectId)
  const [rows, setRows] = useState<Record<number, DraftRow>>(() => {
    const init: Record<number, DraftRow> = {}
    for (const c of config.items) init[c.ma_tieu_chi] = { on: true, trong_so: String(c.trong_so), chi_tieu: String(c.chi_tieu) }
    return init
  })
  const set = (id: number, patch: Partial<DraftRow>) => setRows((r) => ({ ...r, [id]: { ...(r[id] ?? { on: false, trong_so: '', chi_tieu: '' }), ...patch } }))
  const chosen = criteria.filter((c) => rows[c.ma_tieu_chi]?.on)
  const total = chosen.reduce((n, c) => n + (Number(rows[c.ma_tieu_chi].trong_so) || 0), 0)
  const weightOk = Math.abs(total - 100) < 0.01
  const valid = chosen.length > 0 && weightOk && chosen.every((c) => Number(rows[c.ma_tieu_chi].chi_tieu) > 0)
  const blocked = !valid ? (chosen.length === 0 ? 'Chọn ít nhất một tiêu chí.' : !weightOk ? `Tổng trọng số hiện là ${total}, phải bằng 100.` : 'Nhập chỉ tiêu lớn hơn 0.') : null
  const errors = save.error ? toFormErrors(save.error) : null

  function submit(e: FormEvent) {
    e.preventDefault()
    save.mutate(
      {
        periodId,
        items: chosen.map((c) => ({ ma_tieu_chi: c.ma_tieu_chi, trong_so: Number(rows[c.ma_tieu_chi].trong_so), chi_tieu: Number(rows[c.ma_tieu_chi].chi_tieu) })),
      },
      {
        onSuccess: () => {
          toast.success('Đã lưu cấu hình kỳ')
          onClose()
        },
      },
    )
  }

  return (
    <Dialog
      open
      onOpenChange={onClose}
      title="Cấu hình tiêu chí kỳ KPI"
      description="Chọn tiêu chí, đặt trọng số và chỉ tiêu. Tổng trọng số bằng 100."
      className="max-w-2xl"
      footer={
        <>
          <span className={weightOk ? 'mr-auto text-sm text-success-soft-fg tabular-nums' : 'mr-auto text-sm text-muted tabular-nums'}>Tổng trọng số: {total} / 100</span>
          <Button onClick={onClose}>Hủy</Button>
          <Button variant="primary" type="submit" form="config-period" loading={save.isPending} disabledReason={blocked}>
            Lưu cấu hình
          </Button>
        </>
      }
    >
      <form id="config-period" onSubmit={submit}>
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-muted">
            <tr>
              <th className="w-8 pb-2" />
              <th className="pb-2 font-medium">Tiêu chí</th>
              <th className="w-24 pb-2 font-medium">Trọng số</th>
              <th className="w-28 pb-2 font-medium">Chỉ tiêu</th>
            </tr>
          </thead>
          <tbody>
            {criteria.map((c) => {
              const r = rows[c.ma_tieu_chi]
              const on = !!r?.on
              return (
                <tr key={c.ma_tieu_chi} className="border-t">
                  <td className="py-2">
                    <input
                      type="checkbox"
                      checked={on}
                      aria-label={`Chọn ${c.ten_tieu_chi}`}
                      onChange={(e) => set(c.ma_tieu_chi, { on: e.target.checked, trong_so: r?.trong_so || '25', chi_tieu: r?.chi_tieu || '100' })}
                    />
                  </td>
                  <td className="py-2">
                    <span className="font-medium">{c.ten_tieu_chi}</span>
                    <span className="block text-xs text-muted">{c.mo_ta_cach_tinh ?? c.nguon_du_lieu}</span>
                  </td>
                  <td className="py-2">
                    <Input type="number" min={0} max={100} step="any" disabled={!on} value={r?.trong_so ?? ''} onChange={(e) => set(c.ma_tieu_chi, { trong_so: e.target.value })} aria-label={`Trọng số ${c.ten_tieu_chi}`} />
                  </td>
                  <td className="py-2">
                    <Input type="number" min={0} step="any" disabled={!on} value={r?.chi_tieu ?? ''} onChange={(e) => set(c.ma_tieu_chi, { chi_tieu: e.target.value })} aria-label={`Chỉ tiêu ${c.ten_tieu_chi}`} />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {errors?.form ? <p className="mt-3 text-sm text-danger">{errors.form}</p> : null}
      </form>
    </Dialog>
  )
}
