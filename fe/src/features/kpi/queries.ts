import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import type { Evaluation, KpiConfig, KpiCriterion, Period } from '@/api/types'

export function usePeriods(projectId: number) {
  return useQuery({
    queryKey: ['project', projectId, 'kpi-periods'],
    queryFn: () => api.get<Period[]>(`/projects/${projectId}/kpi/periods`),
  })
}

export function usePeriodConfig(periodId: number | null) {
  return useQuery({
    queryKey: ['kpi', periodId, 'config'],
    queryFn: () => api.get<KpiConfig>(`/kpi/periods/${periodId}/config`),
    enabled: periodId !== null,
  })
}

export function useEvaluations(periodId: number | null) {
  return useQuery({
    queryKey: ['kpi', periodId, 'evaluations'],
    queryFn: () => api.get<Evaluation[]>(`/kpi/periods/${periodId}/evaluations`),
    enabled: periodId !== null,
  })
}

export function useCriteria() {
  return useQuery({ queryKey: ['kpi', 'criteria'], queryFn: () => api.get<KpiCriterion[]>('/kpi/criteria') })
}

/** Mọi thao tác KPI làm mới danh sách kỳ và số liệu của kỳ đang xem. */
function useKpiMutation<V, R>(projectId: number, fn: (v: V) => Promise<R>) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['project', projectId, 'kpi-periods'] })
      qc.invalidateQueries({ queryKey: ['kpi'] })
    },
  })
}

export const useCreatePeriod = (projectId: number) =>
  useKpiMutation(projectId, (body: { ten_ky: string; tu_ngay: string; den_ngay: string }) =>
    api.post<Period>(`/projects/${projectId}/kpi/periods`, body),
  )

export const useSetConfig = (projectId: number) =>
  useKpiMutation(projectId, (v: { periodId: number; items: { ma_tieu_chi: number; trong_so: number; chi_tieu: number }[] }) =>
    api.put<KpiConfig>(`/kpi/periods/${v.periodId}/config`, { items: v.items }),
  )

export const useOpenPeriod = (projectId: number) =>
  useKpiMutation(projectId, (periodId: number) => api.post<{ so_danh_gia_tao_moi: number }>(`/kpi/periods/${periodId}/open`))

export const useCalculate = (projectId: number) =>
  useKpiMutation(projectId, (periodId: number) => api.post<{ da_tinh: number; bo_qua: number }>(`/kpi/periods/${periodId}/calculate`))

/** Thêm bảng đánh giá cho thành viên mới được thêm vào dự án sau khi kỳ đã mở. */
export const useSyncMembers = (projectId: number) =>
  useKpiMutation(projectId, (periodId: number) => api.post<{ so_danh_gia_tao_moi: number }>(`/kpi/periods/${periodId}/sync-members`))

export const useClosePeriod = (projectId: number) =>
  useKpiMutation(projectId, (periodId: number) => api.post<Period>(`/kpi/periods/${periodId}/close`))

export const useSaveManual = (projectId: number) =>
  useKpiMutation(
    projectId,
    (v: { periodId: number; items: { ma_nd: number; ma_tieu_chi: number; gia_tri: number }[] }) =>
      api.put<{ so_gia_tri_cap_nhat: number }>(`/kpi/periods/${v.periodId}/manual-inputs`, { items: v.items }),
  )

export const useConfirmEvaluation = (projectId: number) =>
  useKpiMutation(projectId, (v: { periodId: number; ma_nd: number }) =>
    api.post<Evaluation>(`/kpi/periods/${v.periodId}/evaluations/${v.ma_nd}/confirm`),
  )

/** Duyệt hoặc từ chối một đánh giá. Từ chối bắt buộc có nhận xét. */
export const useDecideEvaluation = (projectId: number) =>
  useKpiMutation(projectId, (v: { periodId: number; ma_nd: number; approve: boolean; nhan_xet: string | null }) =>
    api.post<Evaluation>(`/kpi/periods/${v.periodId}/evaluations/${v.ma_nd}/${v.approve ? 'approve' : 'reject'}`, { nhan_xet: v.nhan_xet }),
  )
