import { useQueries, useQuery } from '@tanstack/react-query'
import { ArrowDown, ArrowUp } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '@/api/client'
import type { Member, ProjectStatus } from '@/api/types'
import { Page } from '@/components/layout/Page'
import { Badge } from '@/components/ui/badge'
import { Input, Select } from '@/components/ui/form'
import { Card, EmptyState, ErrorState, PageLoader, Progress, Stat } from '@/components/ui/misc'
import { formatDate, formatHours } from '@/lib/format'
import { PROJECT_STATUS } from '@/lib/labels'
import { cn } from '@/lib/utils'

type Health = 'GREEN' | 'AMBER' | 'RED' | 'GREY'

interface PortfolioItem {
  ma_du_an: number
  ten_du_an: string
  trang_thai: ProjectStatus
  ma_quan_ly: number
  ty_le_hoan_thanh: number
  tong_task: number
  task_tre_han: number
  gio_thuc_te: number
  ngan_sach_gio: number
  vuot_ngan_sach_gio: boolean
  spi: number | null
  cpi: number | null
  suc_khoe: Health
  vi_pham_da_xu_ly: number
  ngay_ket_thuc_du_kien: string
}

interface PortfolioResponse {
  tong_du_an: number
  theo_trang_thai: Record<string, number>
  du_an: PortfolioItem[]
}

const HEALTH: Record<Health, { text: string; tone: 'success' | 'warning' | 'danger' | 'neutral'; rank: number }> = {
  RED: { text: 'Đỏ', tone: 'danger', rank: 0 },
  AMBER: { text: 'Vàng', tone: 'warning', rank: 1 },
  GREY: { text: 'Chưa đủ dữ liệu', tone: 'neutral', rank: 2 },
  GREEN: { text: 'Xanh', tone: 'success', rank: 3 },
}

type SortKey = 'spi' | 'pct' | 'gio' | null

export function PortfolioPage() {
  const [params, setParams] = useSearchParams()
  const status = (params.get('tt') ?? '') as ProjectStatus | ''
  const health = (params.get('sk') ?? '') as Health | ''
  const manager = params.get('ql') ?? ''
  const from = params.get('tu') ?? ''
  const to = params.get('den') ?? ''
  const [sort, setSort] = useState<{ key: SortKey; asc: boolean }>({ key: null, asc: true })

  const update = (changes: Record<string, string | null>) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        for (const [k, v] of Object.entries(changes)) {
          if (v === null || v === '') next.delete(k)
          else next.set(k, v)
        }
        return next
      },
      { replace: true },
    )

  const report = useQuery({
    queryKey: ['portfolio', { status, health, manager, from, to }],
    queryFn: () =>
      api.get<PortfolioResponse>('/reports/portfolio', {
        trang_thai: status || null,
        suc_khoe: health || null,
        ma_quan_ly: manager ? Number(manager) : null,
        tu_ngay: from || null,
        den_ngay: to || null,
      }),
  })
  const items = useMemo(() => report.data?.du_an ?? [], [report.data])

  // Tên quản lý lấy từ danh sách thành viên của từng dự án (Ban giám đốc có quyền xem mọi dự án).
  const memberLists = useQueries({
    queries: items.map((p) => ({
      queryKey: ['project', p.ma_du_an, 'members'],
      queryFn: () => api.get<Member[]>(`/projects/${p.ma_du_an}/members`),
      staleTime: 60_000,
    })),
  })
  const managerNames = useMemo(() => {
    const m = new Map<number, string>()
    items.forEach((p, i) => {
      const found = memberLists[i]?.data?.find((x) => x.ma_nguoi_dung === p.ma_quan_ly)
      if (found) m.set(p.ma_quan_ly, found.ho_ten)
    })
    return m
  }, [items, memberLists])

  const sorted = useMemo(() => {
    const list = [...items]
    if (sort.key === null) {
      // Mặc định: Đỏ, Vàng lên đầu; trong cùng mức thì SPI thấp hơn đứng trước.
      return list.sort((a, b) => HEALTH[a.suc_khoe].rank - HEALTH[b.suc_khoe].rank || (a.spi ?? 99) - (b.spi ?? 99))
    }
    const value = (p: PortfolioItem) => (sort.key === 'spi' ? p.spi : sort.key === 'pct' ? p.ty_le_hoan_thanh : p.ngan_sach_gio ? p.gio_thuc_te / p.ngan_sach_gio : null)
    return list.sort((a, b) => {
      const x = value(a) ?? Number.POSITIVE_INFINITY
      const y = value(b) ?? Number.POSITIVE_INFINITY
      return sort.asc ? x - y : y - x
    })
  }, [items, sort])

  const toggleSort = (key: Exclude<SortKey, null>) =>
    setSort((s) => (s.key === key ? { key, asc: !s.asc } : { key, asc: key === 'spi' }))

  const red = items.filter((p) => p.suc_khoe === 'RED').length
  const over = items.filter((p) => p.vuot_ngan_sach_gio).length
  const late = items.reduce((n, p) => n + p.task_tre_han, 0)
  const managers = [...managerNames.entries()].sort((a, b) => a[1].localeCompare(b[1], 'vi'))

  return (
    <Page
      flush
      crumbs={[{ label: 'Ban giám đốc' }, { label: 'Portfolio' }]}
      title="Báo cáo portfolio dự án"
      toolbar={
        <div className="flex flex-wrap items-end gap-2 pb-2">
          <Select className="w-44" aria-label="Lọc theo trạng thái" value={status} onChange={(e) => update({ tt: e.target.value || null })}>
            <option value="">Mọi trạng thái</option>
            {Object.entries(PROJECT_STATUS).map(([k, v]) => (
              <option key={k} value={k}>
                {v.text}
              </option>
            ))}
          </Select>
          <Select className="w-44" aria-label="Lọc theo quản lý" value={manager} onChange={(e) => update({ ql: e.target.value || null })}>
            <option value="">Mọi quản lý</option>
            {managers.map(([id, name]) => (
              <option key={id} value={id}>
                {name}
              </option>
            ))}
          </Select>
          <Select className="w-40" aria-label="Lọc theo sức khỏe" value={health} onChange={(e) => update({ sk: e.target.value || null })}>
            <option value="">Mọi sức khỏe</option>
            {(Object.keys(HEALTH) as Health[]).map((h) => (
              <option key={h} value={h}>
                {HEALTH[h].text}
              </option>
            ))}
          </Select>
          <label className="flex items-center gap-1.5 text-sm text-muted">
            Kết thúc từ
            <Input type="date" className="w-40" value={from} onChange={(e) => update({ tu: e.target.value || null })} />
          </label>
          <label className="flex items-center gap-1.5 text-sm text-muted">
            Bắt đầu đến
            <Input type="date" className="w-40" value={to} onChange={(e) => update({ den: e.target.value || null })} />
          </label>
        </div>
      }
    >
      {report.isPending ? (
        <PageLoader />
      ) : report.isError ? (
        <ErrorState error={report.error} onRetry={report.refetch} />
      ) : (
        <div className="mx-auto flex max-w-6xl flex-col gap-4">
          {/* Phần 1: tổng quan và báo động. Bấm thẻ Đỏ để lọc nhanh. */}
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Tổng dự án" value={items.length} hint={`Trạng thái: ${Object.entries(report.data.theo_trang_thai).map(([k, v]) => `${PROJECT_STATUS[k as ProjectStatus]?.text ?? k} ${v}`).join(', ') || '—'}`} />
            <button type="button" onClick={() => update({ sk: health === 'RED' ? null : 'RED' })} className="text-left" aria-pressed={health === 'RED'}>
              <Stat label="Báo động đỏ" value={`${red}`} tone="danger" hint={items.length ? `${Math.round((red / items.length) * 100)}% danh mục · bấm để lọc` : undefined} />
            </button>
            <Stat label="Vượt ngân sách giờ" value={over} tone={over ? 'warning' : undefined} />
            <Stat label="Việc trễ hạn" value={late} tone={late ? 'danger' : undefined} />
          </div>

          {/* Phần 2: bảng so sánh danh mục, dự án Đỏ và Vàng đứng đầu. */}
          {items.length === 0 ? (
            <EmptyState title="Không có dự án nào khớp bộ lọc" />
          ) : (
            <Card className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b bg-surface-2 text-xs text-muted">
                  <tr>
                    <th className="px-4 py-2 font-medium">Dự án</th>
                    <th className="px-4 py-2 font-medium">Quản lý</th>
                    <th className="px-4 py-2 font-medium">Sức khỏe</th>
                    <SortHead label="SPI" active={sort.key === 'spi'} asc={sort.asc} onClick={() => toggleSort('spi')} />
                    <th className="px-4 py-2 text-right font-medium">CPI</th>
                    <SortHead label="% xong" active={sort.key === 'pct'} asc={sort.asc} onClick={() => toggleSort('pct')} className="w-40" />
                    <SortHead label="Giờ thực / ngân sách" active={sort.key === 'gio'} asc={sort.asc} onClick={() => toggleSort('gio')} />
                    <th className="px-4 py-2 font-medium">Kết thúc dự kiến</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((p) => {
                    const h = HEALTH[p.suc_khoe]
                    return (
                      <tr key={p.ma_du_an} className={cn('border-b last:border-0', p.suc_khoe === 'RED' && 'bg-danger-soft/40')}>
                        <td className="px-4 py-2.5">
                          <p className="font-medium">{p.ten_du_an}</p>
                          <p className="text-xs text-muted">
                            {PROJECT_STATUS[p.trang_thai].text} · {p.tong_task} việc{p.task_tre_han ? ` · ${p.task_tre_han} trễ hạn` : ''}
                          </p>
                        </td>
                        <td className="px-4 py-2.5 text-muted">{managerNames.get(p.ma_quan_ly) ?? '…'}</td>
                        <td className="px-4 py-2.5">
                          <Badge tone={h.tone}>{h.text}</Badge>
                        </td>
                        <td className="px-4 py-2.5 tabular-nums">{p.spi == null ? '—' : p.spi.toLocaleString('vi-VN', { maximumFractionDigits: 2 })}</td>
                        <td className="px-4 py-2.5 text-right tabular-nums">{p.cpi == null ? '—' : p.cpi.toLocaleString('vi-VN', { maximumFractionDigits: 2 })}</td>
                        <td className="px-4 py-2.5">
                          <div className="flex items-center gap-2">
                            <Progress className="flex-1" value={p.ty_le_hoan_thanh} />
                            <span className="w-10 text-right text-xs tabular-nums text-muted">{p.ty_le_hoan_thanh}%</span>
                          </div>
                        </td>
                        <td className="px-4 py-2.5 tabular-nums">
                          <span className={cn(p.vuot_ngan_sach_gio && 'font-medium text-danger')}>{formatHours(p.gio_thuc_te)}</span>
                          <span className="text-muted"> / {p.ngan_sach_gio ? formatHours(p.ngan_sach_gio) : 'không giới hạn'}</span>
                        </td>
                        <td className="px-4 py-2.5 text-muted tabular-nums">{formatDate(p.ngay_ket_thuc_du_kien)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </Card>
          )}
        </div>
      )}
    </Page>
  )
}

function SortHead({ label, active, asc, onClick, className }: { label: string; active: boolean; asc: boolean; onClick: () => void; className?: string }) {
  return (
    <th className={cn('px-4 py-2 font-medium', className)} aria-sort={active ? (asc ? 'ascending' : 'descending') : undefined}>
      <button type="button" onClick={onClick} className="inline-flex items-center gap-1 hover:text-fg">
        {label}
        {active ? (asc ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" />) : null}
      </button>
    </th>
  )
}
