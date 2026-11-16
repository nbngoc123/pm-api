import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import type { Page, Timesheet } from '@/api/types'

export type CoSo = 'chi_phi' | 'gio'

/** Kết quả của GET /progress/evm (tên trường giữ nguyên theo backend). */
export interface Evm {
  as_of: string
  bac: number
  pv: number
  ev: number
  ac: number
  sv: number
  cv: number
  spi: number | null
  cpi: number | null
  eac: number | null
  etc: number | null
  vac: number | null
  co_so: CoSo
  gio_ke_hoach: number
  gio_thuc_te: number
  so_task_co_baseline: number
  so_task_chua_co_baseline: number
  suc_khoe: 'GREEN' | 'AMBER' | 'RED' | 'GREY'
}

export interface Burndown {
  don_vi: string
  tong_khoi_luong: number
  diem: { ngay: string; ly_tuong: number; thuc_te: number | null }[]
}

export interface Snapshot {
  ma_cs: number
  ngay: string
  pv: number
  ev: number
  ac: number
  spi: number | null
  cpi: number | null
}

export interface Baseline {
  ma_cv: number
  ngay_bat_dau_goc: string
  ngay_ket_thuc_goc: string
  gio_du_kien_goc: number
  chi_phi_ke_hoach_goc: number
  khoa_luc: string | null
}

export function useEvm(projectId: number, coSo: CoSo, asOf: string) {
  return useQuery({
    queryKey: ['project', projectId, 'evm', coSo, asOf],
    queryFn: () => api.get<Evm>(`/projects/${projectId}/progress/evm`, { co_so: coSo, as_of: asOf }),
  })
}

export function useBurndown(projectId: number, asOf: string) {
  return useQuery({
    queryKey: ['project', projectId, 'burndown', asOf],
    queryFn: () => api.get<Burndown>(`/projects/${projectId}/progress/burndown`, { as_of: asOf }),
  })
}

export function useSnapshots(projectId: number) {
  return useQuery({
    queryKey: ['project', projectId, 'snapshots'],
    queryFn: () => api.get<Snapshot[]>(`/projects/${projectId}/progress/snapshots`),
  })
}

export function useBaselines(projectId: number) {
  return useQuery({
    queryKey: ['project', projectId, 'baselines'],
    queryFn: () => api.get<Baseline[]>(`/projects/${projectId}/baseline`),
  })
}

/** Giờ làm của cả dự án, gom đủ mọi trang, để tính giờ thực cho từng công việc. */
export function useProjectTimesheets(projectId: number) {
  return useQuery({
    queryKey: ['project', projectId, 'timesheets-all'],
    queryFn: async () => {
      const all: Timesheet[] = []
      for (let page = 1; ; page++) {
        const res = await api.get<Page<Timesheet>>(`/projects/${projectId}/timesheets`, { page, size: 200 })
        all.push(...res.items)
        if (all.length >= res.total || res.items.length === 0) return all
      }
    },
  })
}

function useProgressMutation<V, R>(projectId: number, fn: (v: V) => Promise<R>) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['project', projectId] })
    },
  })
}

export const useLockBaselines = (projectId: number) =>
  useProgressMutation(projectId, () => api.post<{ so_task_duoc_khoa: number }>(`/projects/${projectId}/baseline/lock`))

export const useSaveSnapshot = (projectId: number) =>
  useProgressMutation(projectId, (asOf: string) => api.post(`/projects/${projectId}/progress/snapshots?as_of=${asOf}`))
