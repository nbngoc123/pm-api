import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import type { Page, Rule, Violation } from '@/api/types'

/** Gom đủ mọi trang của danh sách vi phạm (backend giới hạn 100 mỗi trang). */
async function fetchAllViolations(projectId: number) {
  const all: Violation[] = []
  for (let page = 1; ; page++) {
    const res = await api.get<Page<Violation>>('/violations', { ma_da: projectId, page, size: 100 })
    all.push(...res.items)
    if (all.length >= res.total || res.items.length === 0) return all
  }
}

export function useViolations(projectId: number) {
  return useQuery({ queryKey: ['project', projectId, 'violations'], queryFn: () => fetchAllViolations(projectId) })
}

export function useRules() {
  return useQuery({ queryKey: ['violation-rules'], queryFn: () => api.get<Rule[]>('/violation-rules'), staleTime: 5 * 60_000 })
}

function useViolationMutation<V, R = unknown>(projectId: number, fn: (v: V) => Promise<R>) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['project', projectId, 'violations'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export const useCreateViolation = (projectId: number) =>
  useViolationMutation(projectId, (body: { ma_cv: number; ma_nd: number; ma_qd: number; noi_dung: string }) =>
    api.post<Violation>('/violations', body),
  )

export const useNotifyViolator = (projectId: number) =>
  useViolationMutation(projectId, (id: number) => api.post<Violation>(`/violations/${id}/notify`))

export const useExplain = (projectId: number) =>
  useViolationMutation(projectId, (v: { id: number; noi_dung: string; duong_dan_bang_chung: string | null }) =>
    api.post(`/violations/${v.id}/explanations`, { noi_dung: v.noi_dung, duong_dan_bang_chung: v.duong_dan_bang_chung }),
  )

export const useConclude = (projectId: number) =>
  useViolationMutation(projectId, (v: { id: number; ket_luan: 'CONFIRMED' | 'DISMISSED'; ghi_chu: string }) =>
    api.post<Violation>(`/violations/${v.id}/conclude`, { ket_luan: v.ket_luan, ghi_chu: v.ghi_chu }),
  )
