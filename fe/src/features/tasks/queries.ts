import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import type { AssignResult, Assignment, Attachment, Epic, Page, Priority, Review, SubTask, Task, TaskStatus, Timesheet } from '@/api/types'

/** Bảng Kanban cần toàn bộ task của dự án nên gom hết các trang (backend giới hạn 100 mỗi trang). */
async function fetchAllTasks(projectId: number) {
  const all: Task[] = []
  for (let page = 1; ; page++) {
    const res = await api.get<Page<Task>>(`/projects/${projectId}/tasks`, { page, size: 100 })
    all.push(...res.items)
    if (all.length >= res.total || res.items.length === 0) return all
  }
}

export function useProjectTasks(projectId: number) {
  return useQuery({ queryKey: ['project', projectId, 'tasks'], queryFn: () => fetchAllTasks(projectId) })
}

export function usePrioritizedTasks(projectId: number, enabled: boolean) {
  return useQuery({
    queryKey: ['project', projectId, 'tasks', 'prioritized'],
    queryFn: () => api.get<Task[]>(`/projects/${projectId}/tasks/prioritized`),
    enabled,
  })
}

export function usePendingReviews(projectId: number, enabled: boolean) {
  return useQuery({
    queryKey: ['project', projectId, 'tasks', 'pending-reviews'],
    queryFn: () => api.get<Task[]>(`/projects/${projectId}/reviews/pending`),
    enabled,
  })
}

export function useTask(id: number | null) {
  return useQuery({ queryKey: ['task', id, 'info'], queryFn: () => api.get<Task>(`/tasks/${id}`), enabled: id !== null })
}

const taskList = <T>(name: string) =>
  function useTaskList(id: number) {
    return useQuery({ queryKey: ['task', id, name], queryFn: () => api.get<T[]>(`/tasks/${id}/${name}`) })
  }

export const useAssignments = taskList<Assignment>('assignments')
export const useSubTasks = taskList<SubTask>('subtasks')
export const useAttachments = taskList<Attachment>('attachments')
export const useReviews = taskList<Review>('reviews')
export const useTaskTimesheets = taskList<Timesheet>('timesheets')

/** Mọi thay đổi trên task đều làm mới bảng công việc, số liệu dự án và dashboard. */
function useTaskMutation<V, R = unknown>(projectId: number, fn: (v: V) => Promise<R>) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['project', projectId] })
      qc.invalidateQueries({ queryKey: ['task'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
      qc.invalidateQueries({ queryKey: ['my-timesheets'] })
    },
  })
}

export interface TaskInput {
  ten_cv: string
  mo_ta: string | null
  uu_tien: Priority
  ma_moc: number | null
  ma_epic: number | null
  ngay_bat_dau_du_kien: string | null
  han_hoan_thanh: string | null
  gio_du_kien: number
}

export const useCreateTask = (projectId: number) =>
  useTaskMutation(projectId, (body: TaskInput) => api.post<Task>(`/projects/${projectId}/tasks`, body))

export const useUpdateTask = (projectId: number) =>
  useTaskMutation(projectId, (v: { task: Task; changes: Partial<TaskInput> }) =>
    api.patch<Task>(`/tasks/${v.task.ma_cv}`, { ...v.changes, version: v.task.version }),
  )

export const useDeleteTask = (projectId: number) => useTaskMutation(projectId, (id: number) => api.delete(`/tasks/${id}`))

export const useTransition = (projectId: number) =>
  useTaskMutation(projectId, (v: { id: number; to: TaskStatus }) => api.post<Task>(`/tasks/${v.id}/transition`, { trang_thai: v.to }))

export const useSetProgress = (projectId: number) =>
  useTaskMutation(projectId, (v: { id: number; pct: number }) => api.post<Task>(`/tasks/${v.id}/progress`, { ty_le_hoan_thanh: v.pct }))

export const useReviewTask = (projectId: number) =>
  useTaskMutation(projectId, (v: { id: number; ket_qua: 'APPROVED' | 'REJECTED'; nhan_xet: string | null }) =>
    api.post<Review>(`/tasks/${v.id}/review`, { ket_qua: v.ket_qua, nhan_xet: v.nhan_xet }),
  )

export const useAssign = (projectId: number) =>
  useTaskMutation(projectId, (v: { id: number; ma_nd: number }) => api.post<AssignResult>(`/tasks/${v.id}/assignments`, { ma_nd: v.ma_nd }))

export const useUnassign = (projectId: number) =>
  useTaskMutation(projectId, (v: { id: number; ma_nd: number }) => api.delete(`/tasks/${v.id}/assignments/${v.ma_nd}`))

export const useCreateSubTask = (projectId: number) =>
  useTaskMutation(projectId, (v: { id: number; ten_subtask: string }) => api.post(`/tasks/${v.id}/subtasks`, { ten_subtask: v.ten_subtask }))

export const useToggleSubTask = (projectId: number) =>
  useTaskMutation(projectId, (v: { id: number; sub: SubTask }) =>
    api.patch(`/tasks/${v.id}/subtasks/${v.sub.ma_subtask}`, { trang_thai: v.sub.trang_thai === 'DONE' ? 'TODO' : 'DONE' }),
  )

export const useDeleteSubTask = (projectId: number) =>
  useTaskMutation(projectId, (v: { id: number; ma_subtask: number }) => api.delete(`/tasks/${v.id}/subtasks/${v.ma_subtask}`))

export const useUploadAttachment = (projectId: number) =>
  useTaskMutation(projectId, (v: { id: number; file: File }) => {
    const form = new FormData()
    form.append('file', v.file)
    return api.upload<Attachment>(`/tasks/${v.id}/attachments`, form)
  })

export const useDeleteAttachment = (projectId: number) => useTaskMutation(projectId, (ma_tep: number) => api.delete(`/attachments/${ma_tep}`))

export interface TimesheetInput {
  bat_dau: string
  ket_thuc: string
  noi_dung: string | null
}

export const useLogTime = (projectId: number) =>
  useTaskMutation(projectId, (v: { id: number; body: TimesheetInput }) => api.post<Timesheet>(`/tasks/${v.id}/timesheets`, v.body))

export function useEpics(projectId: number) {
  return useQuery({ queryKey: ['project', projectId, 'epics'], queryFn: () => api.get<Epic[]>(`/projects/${projectId}/epics`) })
}
