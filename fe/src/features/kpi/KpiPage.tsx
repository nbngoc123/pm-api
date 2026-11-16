import { Calculator, Lock, Play, Plus, Settings, UserPlus } from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { errorMessage } from '@/api/client'
import type { Evaluation, EvalStatus } from '@/api/types'
import { useAuth } from '@/auth/useAuth'
import { Page } from '@/components/layout/Page'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/form'
import { Avatar, Card, EmptyState, ErrorState, PageLoader } from '@/components/ui/misc'
import { useProjectContext } from '@/features/projects/projectContext'
import { EVAL_STATUS, PERIOD_STATUS } from '@/lib/labels'
import { cn } from '@/lib/utils'
import { CreatePeriodDialog, ConfigDialog } from './KpiDialogs'
import { EvaluationSheet } from './EvaluationSheet'
import { useClosePeriod, useCalculate, useCriteria, useEvaluations, useOpenPeriod, usePeriodConfig, usePeriods, useSyncMembers } from './queries'

const TABS: { id: 'ALL' | EvalStatus; label: string }[] = [
  { id: 'ALL', label: 'Tất cả' },
  { id: 'PROVISIONAL', label: 'Tạm tính' },
  { id: 'MEMBER_CONFIRMED', label: 'Chờ duyệt' },
  { id: 'APPROVED', label: 'Đã duyệt' },
  { id: 'REJECTED', label: 'Bị từ chối' },
]

const fmt = (n: number | null | undefined) => (n == null ? '—' : n.toLocaleString('vi-VN', { maximumFractionDigits: 2 }))
const onError = (e: unknown) => toast.error(errorMessage(e))

export function KpiPage() {
  const ctx = useProjectContext()
  const { project, can, readOnly } = ctx
  const { user } = useAuth()
  const [params, setParams] = useSearchParams()
  const periods = usePeriods(project.ma_du_an)
  const picked = periods.data?.find((p) => String(p.ma_ky) === params.get('ky'))
  const period = picked ?? periods.data?.find((p) => p.trang_thai === 'OPEN') ?? periods.data?.at(-1) ?? null
  const periodId = period?.ma_ky ?? null
  const config = usePeriodConfig(periodId)
  const evals = useEvaluations(periodId)
  const criteria = useCriteria()
  const open = useOpenPeriod(project.ma_du_an)
  const calculate = useCalculate(project.ma_du_an)
  const close = useClosePeriod(project.ma_du_an)
  const sync = useSyncMembers(project.ma_du_an)
  const [creating, setCreating] = useState(false)
  const [configuring, setConfiguring] = useState(false)

  const tab = (params.get('tt') ?? 'ALL') as 'ALL' | EvalStatus
  const evKey = params.get('ev') ? Number(params.get('ev')) : null
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

  if (periods.isPending) {
    return <PageLoader />
  }
  if (periods.isError) {
    return (
      <Page crumbs={[{ label: 'Dự án', to: '/projects' }, { label: project.ten_du_an, to: `/projects/${project.ma_du_an}` }, { label: 'KPI' }]} title="KPI">
        <ErrorState error={periods.error} onRetry={periods.refetch} />
      </Page>
    )
  }

  const manage = can('kpi.period.manage') && !readOnly
  const canApprove = can('kpi.approve') && user?.loai === 'QUAN_LY' && !readOnly
  const all: Evaluation[] = evals.data ?? []
  const rows = all.filter((e) => tab === 'ALL' || e.trang_thai === tab)
  const current = all.find((e) => e.ma_nguoi_dung === evKey) ?? null
  const pendingCount = all.filter((e) => e.trang_thai !== 'APPROVED').length
  const crumbs = [{ label: 'Dự án', to: '/projects' }, { label: project.ten_du_an, to: `/projects/${project.ma_du_an}` }, { label: 'KPI' }]

  if (!period) {
    return (
      <Page crumbs={crumbs} title="KPI" actions={<CreateButton manage={manage} onClick={() => setCreating(true)} />}>
        <EmptyState
          title="Dự án chưa có kỳ KPI"
          description="Tạo kỳ, cấu hình tiêu chí và trọng số, mở kỳ để hệ thống tạo bảng đánh giá cho từng thành viên."
          action={manage ? <Button variant="primary" onClick={() => setCreating(true)}><Plus />Tạo kỳ đầu tiên</Button> : null}
        />
        {creating ? <CreatePeriodDialog projectId={project.ma_du_an} onClose={() => setCreating(false)} onCreated={(id) => update({ ky: String(id) })} /> : null}
      </Page>
    )
  }

  const reason = (ok: boolean, text: string) => (ok ? null : text)
  const needManage = reason(manage, readOnly ? 'Dự án đã hoàn thành hoặc đã đóng nên không thay đổi được.' : 'Cần quyền quản lý dự án.')

  return (
    <Page
      flush
      crumbs={crumbs}
      title="KPI"
      actions={
        <>
          <CreateButton manage={manage} onClick={() => setCreating(true)} />
          {period.trang_thai === 'DRAFT' ? (
            <>
              <Button disabledReason={needManage} onClick={() => setConfiguring(true)}>
                <Settings />
                Cấu hình
              </Button>
              <Button
                variant="primary"
                disabledReason={needManage}
                loading={open.isPending}
                onClick={() => open.mutate(period.ma_ky, { onSuccess: (r) => toast.success(`Đã mở kỳ, tạo ${r.so_danh_gia_tao_moi} bảng đánh giá`), onError })}
              >
                <Play />
                Mở kỳ
              </Button>
            </>
          ) : null}
          {period.trang_thai === 'OPEN' ? (
            <>
              <Button
                disabledReason={needManage}
                loading={calculate.isPending}
                onClick={() => calculate.mutate(period.ma_ky, { onSuccess: (r) => toast.success(`Đã tính ${r.da_tinh} người, bỏ qua ${r.bo_qua}`), onError })}
              >
                <Calculator />
                Tính điểm
              </Button>
              <Button
                disabledReason={needManage}
                loading={sync.isPending}
                onClick={() => sync.mutate(period.ma_ky, { onSuccess: (r) => toast.success(r.so_danh_gia_tao_moi ? `Đã thêm ${r.so_danh_gia_tao_moi} người vào kỳ` : 'Kỳ đã có đủ mọi thành viên'), onError })}
              >
                <UserPlus />
                Đồng bộ thành viên
              </Button>
              <Button
                disabledReason={needManage ?? (pendingCount ? `Còn ${pendingCount} đánh giá chưa được duyệt. Duyệt hết rồi mới đóng kỳ.` : null)}
                loading={close.isPending}
                onClick={() => confirm(`Đóng kỳ "${period.ten_ky}"? Kỳ đã đóng không sửa được.`) && close.mutate(period.ma_ky, { onSuccess: () => toast.success('Đã đóng kỳ KPI'), onError })}
              >
                <Lock />
                Đóng kỳ
              </Button>
            </>
          ) : null}
        </>
      }
      toolbar={
        <div className="flex flex-wrap items-end justify-between gap-x-4">
          <div role="tablist" aria-label="Lọc theo trạng thái đánh giá" className="flex gap-4">
            {TABS.map((t) => {
              const n = t.id === 'ALL' ? all.length : all.filter((e) => e.trang_thai === t.id).length
              return (
                <button
                  key={t.id}
                  type="button"
                  role="tab"
                  aria-selected={tab === t.id}
                  onClick={() => update({ tt: t.id === 'ALL' ? null : t.id })}
                  className={cn('-mb-px flex items-center gap-1.5 border-b-2 border-transparent px-0.5 py-2 text-sm text-muted hover:text-fg', tab === t.id && 'border-primary font-medium text-primary hover:text-primary')}
                >
                  {t.label}
                  <span
                    className={cn(
                      'rounded-full px-1.5 text-xs tabular-nums',
                      t.id === 'REJECTED' && n > 0 ? 'bg-danger-soft text-danger-soft-fg font-medium' : 'bg-neutral-soft text-neutral-soft-fg',
                    )}
                  >
                    {n}
                  </span>
                </button>
              )
            })}
          </div>
          <div className="flex items-center gap-2 pb-2">
            <Select className="w-44" aria-label="Chọn kỳ KPI" value={period.ma_ky} onChange={(e) => update({ ky: e.target.value, ev: null, tt: null })}>
              {periods.data?.map((p) => (
                <option key={p.ma_ky} value={p.ma_ky}>
                  {p.ten_ky} · {PERIOD_STATUS[p.trang_thai].text}
                </option>
              ))}
            </Select>
          </div>
        </div>
      }
    >
      {evals.isPending ? (
        <PageLoader />
      ) : evals.isError ? (
        <ErrorState error={evals.error} onRetry={evals.refetch} />
      ) : all.length === 0 ? (
        <EmptyState
          title={period.trang_thai === 'DRAFT' ? 'Mở kỳ để tạo bảng đánh giá' : 'Chưa có bảng đánh giá nào'}
          description={period.trang_thai === 'DRAFT' ? 'Cấu hình tiêu chí trước, rồi bấm Mở kỳ.' : 'Bảng đánh giá sẽ hiện ở đây khi kỳ đã mở.'}
        />
      ) : rows.length === 0 ? (
        <EmptyState title="Không có người nào ở trạng thái này" />
      ) : (
        <div className="overflow-y-auto p-4">
          <Card className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="border-b bg-surface-2 text-xs text-muted">
                <tr>
                  <th className="px-4 py-2 font-medium">Người</th>
                  <th className="px-4 py-2 text-right font-medium">Điểm trước</th>
                  <th className="px-4 py-2 text-right font-medium">Điểm gốc</th>
                  <th className="px-4 py-2 text-right font-medium">Điểm trừ</th>
                  <th className="px-4 py-2 text-right font-medium">Điểm tổng</th>
                  <th className="px-4 py-2 font-medium">Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((e) => (
                  <tr
                    key={e.ma_nguoi_dung}
                    tabIndex={0}
                    onClick={() => update({ ev: String(e.ma_nguoi_dung) })}
                    onKeyDown={(k) => k.key === 'Enter' && update({ ev: String(e.ma_nguoi_dung) })}
                    className={cn('cursor-pointer border-b last:border-0 hover:bg-surface-2', current?.ma_nguoi_dung === e.ma_nguoi_dung && 'bg-primary-soft hover:bg-primary-soft')}
                  >
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2">
                        <Avatar name={e.ho_ten} />
                        <span className="font-medium">{e.ho_ten}</span>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-muted">{fmt(e.diem_ky_truoc)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{fmt(e.diem_goc)}</td>
                    <td className={cn('px-4 py-2.5 text-right tabular-nums', e.diem_tru > 0 && 'text-danger')}>{fmt(e.diem_tru)}</td>
                    <td className="px-4 py-2.5 text-right text-base font-semibold tabular-nums">{fmt(e.diem_tong)}</td>
                    <td className="px-4 py-2.5">
                      <Badge tone={EVAL_STATUS[e.trang_thai].tone}>{EVAL_STATUS[e.trang_thai].text}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      )}

      {current ? (
        <EvaluationSheet
          key={current.ma_nguoi_dung}
          projectId={project.ma_du_an}
          ev={current}
          period={period}
          config={config.data}
          manage={manage}
          canApprove={canApprove}
          isSelf={current.ma_nguoi_dung === user?.ma_nd}
          onClose={() => update({ ev: null })}
        />
      ) : null}
      {creating ? <CreatePeriodDialog projectId={project.ma_du_an} onClose={() => setCreating(false)} onCreated={(id) => update({ ky: String(id), ev: null, tt: null })} /> : null}
      {configuring && config.data && criteria.data ? (
        <ConfigDialog projectId={project.ma_du_an} periodId={period.ma_ky} criteria={criteria.data} config={config.data} onClose={() => setConfiguring(false)} />
      ) : null}
    </Page>
  )
}

function CreateButton({ manage, onClick }: { manage: boolean; onClick: () => void }) {
  return (
    <Button variant="secondary" disabledReason={manage ? null : 'Cần quyền quản lý dự án.'} onClick={onClick}>
      <Plus />
      Tạo kỳ
    </Button>
  )
}
