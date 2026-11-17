import { Lock, Save } from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { errorMessage } from '@/api/client'
import type { Task } from '@/api/types'
import { Page } from '@/components/layout/Page'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/form'
import { Card, CardHeader, EmptyState, ErrorState, PageLoader, Progress, Stat } from '@/components/ui/misc'
import { useProjectContext } from '@/features/projects/projectContext'
import { useProjectTasks } from '@/features/tasks/queries'
import { formatDate, formatHours, toDateInput } from '@/lib/format'
import { cn } from '@/lib/utils'
import { type CoSo, useBaselines, useBurndown, useEvm, useLockBaselines, useProjectTimesheets, useSaveSnapshot, useSnapshots } from './queries'

const HEALTH: Record<'GREEN' | 'AMBER' | 'RED' | 'GREY', { text: string; tone: 'success' | 'warning' | 'danger' | 'neutral' }> = {
  GREEN: { text: 'Xanh', tone: 'success' },
  AMBER: { text: 'Vàng', tone: 'warning' },
  RED: { text: 'Đỏ', tone: 'danger' },
  GREY: { text: 'Chưa đủ dữ liệu', tone: 'neutral' },
}

const num = (n: number | null | undefined, digits = 2) => (n == null ? '—' : n.toLocaleString('vi-VN', { maximumFractionDigits: digits }))
const money = (n: number) => `${Math.round(n).toLocaleString('vi-VN')} đ`

export function ProgressPage() {
  const ctx = useProjectContext()
  const { project, can, readOnly } = ctx
  const [params, setParams] = useSearchParams()
  const [today] = useState(() => toDateInput(new Date()))
  const coSo = (params.get('cs') === 'gio' ? 'gio' : 'chi_phi') as CoSo
  const asOf = params.get('den') ?? today
  const chart = params.get('bd') === 'burndown' ? 'burndown' : 'evm'

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

  const evm = useEvm(project.ma_du_an, coSo, asOf)
  const burndown = useBurndown(project.ma_du_an, asOf)
  const snapshots = useSnapshots(project.ma_du_an)
  const baselines = useBaselines(project.ma_du_an)
  const tasks = useProjectTasks(project.ma_du_an)
  const timesheets = useProjectTimesheets(project.ma_du_an)
  const lock = useLockBaselines(project.ma_du_an)
  const snapshot = useSaveSnapshot(project.ma_du_an)

  const manage = can('progress.manage') && !readOnly
  const crumbs = [{ label: 'Dự án', to: '/projects' }, { label: project.ten_du_an, to: `/projects/${project.ma_du_an}` }, { label: 'Tiến độ' }]

  if (evm.isPending || tasks.isPending) return <PageLoader />
  if (evm.isError) {
    return (
      <Page crumbs={crumbs} title="Tiến độ">
        <ErrorState error={evm.error} onRetry={evm.refetch} />
      </Page>
    )
  }

  const e = evm.data
  // Chưa có công việc nào có kế hoạch gốc thì chưa có gì để đánh giá, không hiện Đỏ.
  const health = e.so_task_co_baseline === 0 ? HEALTH.GREY : HEALTH[e.suc_khoe]
  const unit = (v: number) => (coSo === 'chi_phi' ? money(v) : formatHours(v))

  return (
    <Page
      flush
      crumbs={crumbs}
      title="Tiến độ"
      actions={
        <>
          <Button disabledReason={manage ? null : 'Cần quyền quản lý dự án.'} loading={snapshot.isPending} onClick={() => snapshot.mutate(asOf, { onSuccess: () => toast.success('Đã lưu chỉ số của ngày ' + formatDate(asOf)), onError: (err) => toast.error(errorMessage(err)) })}>
            <Save />
            Lưu chỉ số
          </Button>
          <Button
            variant="primary"
            disabledReason={manage ? null : 'Cần quyền quản lý dự án.'}
            loading={lock.isPending}
            onClick={() => lock.mutate(undefined, { onSuccess: (r) => toast.success(`Đã khóa kế hoạch gốc cho ${r.so_task_duoc_khoa} công việc`), onError: (err) => toast.error(errorMessage(err)) })}
          >
            <Lock />
            Khóa kế hoạch gốc
          </Button>
        </>
      }
      toolbar={
        <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-2">
          <div role="tablist" aria-label="Biểu đồ" className="flex gap-4">
            {(['evm', 'burndown'] as const).map((c) => (
              <button
                key={c}
                type="button"
                role="tab"
                aria-selected={chart === c}
                onClick={() => update({ bd: c === 'evm' ? null : c })}
                className={cn('-mb-px border-b-2 border-transparent px-0.5 py-2 text-sm text-muted hover:text-fg', chart === c && 'border-primary font-medium text-primary hover:text-primary')}
              >
                {c === 'evm' ? 'Biểu đồ EVM' : 'Burndown'}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-3 pb-2 text-sm">
            <div role="radiogroup" aria-label="Cơ sở tính" className="flex overflow-hidden rounded-md border border-border-strong">
              {(['chi_phi', 'gio'] as const).map((c) => (
                <button
                  key={c}
                  type="button"
                  role="radio"
                  aria-checked={coSo === c}
                  onClick={() => update({ cs: c === 'chi_phi' ? null : c })}
                  className={cn('px-3 py-1 text-sm', coSo === c ? 'bg-primary-soft text-primary-soft-fg font-medium' : 'text-muted hover:bg-surface-2')}
                >
                  {c === 'chi_phi' ? 'Theo chi phí' : 'Theo giờ'}
                </button>
              ))}
            </div>
            <label className="flex items-center gap-2 text-muted">
              Tính đến ngày
              <Input type="date" className="w-40" value={asOf} max={today} onChange={(ev) => update({ den: ev.target.value === today ? null : ev.target.value })} />
            </label>
          </div>
        </div>
      }
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-4">
        {e.so_task_chua_co_baseline > 0 ? (
          <p className="rounded-md bg-warning-soft px-3 py-2 text-sm text-warning-soft-fg">
            {e.so_task_chua_co_baseline} công việc chưa có kế hoạch gốc nên không được tính vào PV. Bấm Khóa kế hoạch gốc để tạo kế hoạch mặc định.
          </p>
        ) : null}

        {/* Phần 1: chỉ số lớn */}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Stat label="SPI (tiến độ)" value={num(e.spi)} tone={e.spi != null && e.spi < 0.95 ? 'warning' : 'success'} hint={e.spi == null ? 'Chưa có kế hoạch' : e.spi < 1 ? `Chậm ${Math.round((1 - e.spi) * 100)}% so với kế hoạch` : 'Đúng hoặc nhanh hơn kế hoạch'} />
          <Stat label="CPI (chi phí)" value={num(e.cpi)} tone={e.cpi != null && e.cpi < 0.95 ? 'danger' : 'success'} hint={e.cpi == null ? 'Chưa có chi phí thực tế' : e.cpi < 1 ? 'Vượt chi phí kế hoạch' : 'Tiết kiệm so với kế hoạch'} />
          <Stat label="EAC (dự báo hoàn thành)" value={e.eac == null ? '—' : unit(e.eac)} hint={e.vac == null ? undefined : `Lệch dự toán ${unit(e.vac)}`} />
          <Card className="flex flex-col justify-between border-l-[3px] border-l-border-strong px-4 py-3">
            <p className="text-xs text-muted">Sức khỏe dự án</p>
            <div className="mt-1">
              <Badge tone={health.tone}>{health.text}</Badge>
            </div>
            <p className="text-xs text-subtle">Theo chỉ số thấp nhất giữa SPI và CPI</p>
          </Card>
        </div>

        {/* Phần 2: biểu đồ toàn chiều ngang */}
        <Card>
          <CardHeader title={chart === 'evm' ? `PV, EV, AC theo ngày (${coSo === 'chi_phi' ? 'chi phí' : 'giờ'})` : `Burndown (${burndown.data?.don_vi ?? ''})`} />
          <div className="p-4">
            {chart === 'evm' ? (
              snapshots.isPending ? (
                <PageLoader />
              ) : (snapshots.data?.length ?? 0) < 2 ? (
                <EmptyState
                  title="Chưa đủ bản ghi chỉ số để vẽ biểu đồ"
                  description="Biểu đồ EVM vẽ từ các bản ghi đã lưu theo ngày. Bấm Lưu chỉ số mỗi ngày để theo dõi xu hướng."
                />
              ) : (
                <LineChart
                  series={[
                    { name: 'Kế hoạch (PV)', color: '#378ADD', dashed: true, points: snapshots.data!.map((s) => ({ x: s.ngay, y: s.pv })) },
                    { name: 'Hoàn thành (EV)', color: '#639922', points: snapshots.data!.map((s) => ({ x: s.ngay, y: s.ev })) },
                    { name: 'Thực chi (AC)', color: '#BA7517', points: snapshots.data!.map((s) => ({ x: s.ngay, y: s.ac })) },
                  ]}
                  format={(v) => (coSo === 'chi_phi' ? money(v) : formatHours(v))}
                />
              )
            ) : burndown.isPending ? (
              <PageLoader />
            ) : burndown.isError ? (
              <ErrorState error={burndown.error} onRetry={burndown.refetch} />
            ) : (
              <LineChart
                series={[
                  { name: 'Lý tưởng', color: '#378ADD', dashed: true, points: burndown.data.diem.map((d) => ({ x: d.ngay, y: d.ly_tuong })) },
                  { name: 'Thực tế còn lại', color: '#639922', points: burndown.data.diem.filter((d) => d.thuc_te != null).map((d) => ({ x: d.ngay, y: d.thuc_te as number })) },
                ]}
                format={(v) => `${num(v, 1)} ${burndown.data.don_vi}`}
              />
            )}
          </div>
        </Card>

        {/* Phần 3: bảng việc, kế hoạch gốc so với thực tế */}
        <TaskProgressTable tasks={tasks.data ?? []} baselines={baselines.data} timesheets={timesheets.data} today={today} isLoading={baselines.isPending || timesheets.isPending} />
      </div>
    </Page>
  )
}

function TaskProgressTable({ tasks, baselines, timesheets, today, isLoading }: { tasks: Task[]; baselines: { ma_cv: number; gio_du_kien_goc: number; ngay_bat_dau_goc: string; ngay_ket_thuc_goc: string }[] | undefined; timesheets: { ma_cv: number; so_gio: number }[] | undefined; today: string; isLoading: boolean }) {
  const base = new Map((baselines ?? []).map((b) => [b.ma_cv, b]))
  const actual = new Map<number, number>()
  for (const t of timesheets ?? []) actual.set(t.ma_cv, (actual.get(t.ma_cv) ?? 0) + t.so_gio)
  const rows = tasks.filter((t) => t.trang_thai !== 'CANCELLED')

  return (
    <Card className="overflow-x-auto">
      <CardHeader title="Công việc: kế hoạch gốc so với thực tế" />
      {isLoading ? (
        <PageLoader />
      ) : rows.length === 0 ? (
        <EmptyState title="Chưa có công việc nào" />
      ) : (
        <table className="w-full text-left text-sm">
          <thead className="border-b bg-surface-2 text-xs text-muted">
            <tr>
              <th className="px-4 py-2 font-medium">Công việc</th>
              <th className="px-4 py-2 text-right font-medium">Giờ gốc</th>
              <th className="px-4 py-2 text-right font-medium">Giờ thực</th>
              <th className="w-40 px-4 py-2 font-medium">% xong</th>
              <th className="px-4 py-2 font-medium">Tình trạng</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => {
              const b = base.get(t.ma_cv)
              const hours = actual.get(t.ma_cv) ?? 0
              const plan = b ? b.gio_du_kien_goc : null
              const done = t.trang_thai === 'DONE'
              // Tỷ lệ thời gian đã trôi qua theo kế hoạch gốc, để so với % xong.
              const expected = b ? expectedPct(b.ngay_bat_dau_goc, b.ngay_ket_thuc_goc, today) : null
              const late = !done && t.muc_do_khan === 'OVERDUE'
              const behind = !done && !late && expected != null && t.ty_le_hoan_thanh < expected - 20
              const overHours = plan != null && hours > plan
              const status = done ? { text: 'Hoàn thành', tone: 'success' as const } : late ? { text: 'Trễ hạn', tone: 'danger' as const } : behind ? { text: 'Chậm tiến độ', tone: 'danger' as const } : overHours ? { text: 'Vượt giờ', tone: 'warning' as const } : b ? { text: 'Đúng kế hoạch', tone: 'success' as const } : { text: 'Chưa có kế hoạch gốc', tone: 'neutral' as const }
              return (
                <tr key={t.ma_cv} className="border-b last:border-0">
                  <td className="px-4 py-2.5">
                    <p className="font-medium">{t.ten_cv}</p>
                    {b ? <p className="text-xs text-muted">{formatDate(b.ngay_bat_dau_goc)} – {formatDate(b.ngay_ket_thuc_goc)}</p> : null}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums">{plan == null ? '—' : formatHours(plan)}</td>
                  <td className={cn('px-4 py-2.5 text-right tabular-nums', overHours && 'font-medium text-warning-soft-fg')}>{formatHours(hours)}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <Progress className="flex-1" value={done ? 100 : t.ty_le_hoan_thanh} />
                      <span className="w-10 text-right text-xs tabular-nums text-muted">{done ? 100 : t.ty_le_hoan_thanh}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge tone={status.tone}>{status.text}</Badge>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </Card>
  )
}

function expectedPct(start: string, end: string, today: string) {
  const s = new Date(start).getTime()
  const e = new Date(end).getTime()
  const t = new Date(today).getTime()
  if (e <= s) return t >= s ? 100 : 0
  return Math.max(0, Math.min(100, ((t - s) / (e - s)) * 100))
}

interface Series {
  name: string
  color: string
  dashed?: boolean
  points: { x: string; y: number }[]
}

/** Biểu đồ đường tự vẽ bằng SVG, không cần thư viện. Trục X là ngày, trục Y bắt đầu từ 0. */
function LineChart({ series, format }: { series: Series[]; format: (v: number) => string }) {
  const W = 960
  const H = 280
  const pad = { l: 64, r: 16, t: 16, b: 32 }
  const dates = [...new Set(series.flatMap((s) => s.points.map((p) => p.x)))].sort()
  const maxY = Math.max(1, ...series.flatMap((s) => s.points.map((p) => p.y)))
  const xOf = (d: string) => pad.l + (dates.length <= 1 ? 0 : (dates.indexOf(d) / (dates.length - 1)) * (W - pad.l - pad.r))
  const yOf = (v: number) => pad.t + (1 - v / maxY) * (H - pad.t - pad.b)
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => maxY * f)

  return (
    <div className="flex flex-col gap-3">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-72 w-full" role="img" aria-label={series.map((s) => s.name).join(', ')}>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={pad.l} x2={W - pad.r} y1={yOf(v)} y2={yOf(v)} stroke="var(--border)" strokeWidth={0.5} />
            <text x={pad.l - 8} y={yOf(v) + 4} textAnchor="end" className="fill-muted text-[11px]">
              {format(v)}
            </text>
          </g>
        ))}
        {dates
          .filter((_, i) => i % Math.ceil(dates.length / 8) === 0)
          .map((d) => (
            <text key={d} x={xOf(d)} y={H - 8} textAnchor="middle" className="fill-muted text-[11px]">
              {formatDate(d)}
            </text>
          ))}
        {series.map((s) => (
          <g key={s.name}>
            <polyline
              fill="none"
              stroke={s.color}
              strokeWidth={2}
              strokeDasharray={s.dashed ? '6 4' : undefined}
              points={s.points.map((p) => `${xOf(p.x)},${yOf(p.y)}`).join(' ')}
            />
            {s.points.map((p) => (
              <circle key={p.x} cx={xOf(p.x)} cy={yOf(p.y)} r={3} fill={s.color}>
                <title>{`${s.name} · ${formatDate(p.x)}: ${format(p.y)}`}</title>
              </circle>
            ))}
          </g>
        ))}
      </svg>
      <div className="flex flex-wrap gap-4 text-xs text-muted">
        {series.map((s) => (
          <span key={s.name} className="flex items-center gap-1.5">
            <span className="inline-block h-0.5 w-5" style={{ background: s.color, borderTop: s.dashed ? `2px dashed ${s.color}` : undefined }} />
            {s.name}
          </span>
        ))}
      </div>
    </div>
  )
}
