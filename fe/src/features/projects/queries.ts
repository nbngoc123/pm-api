import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import type { Member, Milestone, MilestoneStatus, Page, Project, ProjectOverview, ProjectPermissions, ProjectRole, ProjectStatus, UserLookup } from '@/api/types'

export function useProjects(params: { q?: string; trang_thai?: ProjectStatus | '' }) {
  return useQuery({
    queryKey: ['projects', params],
    queryFn: () => api.get<Page<Project>>('/projects', { ...params, size: 100 }),
  })
}

export function useProject(id: number) {
  return useQuery({ queryKey: ['project', id, 'info'], queryFn: () => api.get<Project>(`/projects/${id}`), retry: false })
}

export function useProjectOverview(id: number) {
  return useQuery({ queryKey: ['project', id, 'overview'], queryFn: () => api.get<ProjectOverview>(`/projects/${id}/overview`) })
}

export function useMembers(id: number) {
  return useQuery({
    queryKey: ['project', id, 'members'],
    queryFn: () => api.get<Member[]>(`/projects/${id}/members`),
    staleTime: 60_000,
  })
}

export function useMilestones(id: number) {
  return useQuery({ queryKey: ['project', id, 'milestones'], queryFn: () => api.get<Milestone[]>(`/projects/${id}/milestones`) })
}

/** Vai trò và quyền của người dùng trong một dự án, dùng để ẩn menu và làm mờ nút. */
export function useProjectAccess(id: number) {
  const q = useQuery({
    queryKey: ['project', id, 'permissions'],
    queryFn: () => api.get<ProjectPermissions>(`/projects/${id}/my-permissions`),
    staleTime: 60_000,
    retry: false,
  })
  return {
    role: q.data?.vai_tro ?? null,
    can: (permission: string) => !!q.data?.permissions.includes(permission),
    loading: q.isPending,
  }
}

export function useUserLookup(q: string) {
  return useQuery({
    queryKey: ['user-lookup', q],
    queryFn: () => api.get<UserLookup[]>('/users/lookup', { q }),
    enabled: q.trim().length >= 2,
  })
}

function useProjectMutation<V>(id: number, fn: (v: V) => Promise<unknown>) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['project', id] })
      qc.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

export interface ProjectInput {
  ten_du_an: string
  muc_tieu: string | null
  ngay_bat_dau: string
  ngay_ket_thuc_du_kien: string
  ngan_sach_gio: number
  ma_quan_ly: number
}

export function useCreateProject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ProjectInput) => api.post<Project>('/projects', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })
}

export const useChangeProjectStatus = (id: number) =>
  useProjectMutation(id, (trang_thai: ProjectStatus) => api.patch(`/projects/${id}/status`, { trang_thai }))

export const useAddMember = (id: number) =>
  useProjectMutation(id, (body: { ma_nguoi_dung: number; vai_tro: ProjectRole }) => api.post(`/projects/${id}/members`, body))

export const useChangeMemberRole = (id: number) =>
  useProjectMutation(id, (v: { ma_nd: number; vai_tro: ProjectRole }) => api.patch(`/projects/${id}/members/${v.ma_nd}`, { vai_tro: v.vai_tro }))

export const useRemoveMember = (id: number) => useProjectMutation(id, (ma_nd: number) => api.delete(`/projects/${id}/members/${ma_nd}`))

export const useCreateMilestone = (id: number) =>
  useProjectMutation(id, (body: { ten_moc: string; han_hoan_thanh: string }) => api.post(`/projects/${id}/milestones`, body))

export const useUpdateMilestone = (id: number) =>
  useProjectMutation(id, (v: { ma_moc: number; trang_thai: MilestoneStatus }) =>
    api.patch(`/projects/${id}/milestones/${v.ma_moc}`, { trang_thai: v.trang_thai }),
  )

export const useDeleteMilestone = (id: number) => useProjectMutation(id, (ma_moc: number) => api.delete(`/projects/${id}/milestones/${ma_moc}`))
