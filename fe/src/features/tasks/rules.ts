import type { Task, TaskStatus } from '@/api/types'

/**
 * Luật chuyển trạng thái công việc, phản chiếu services/tasks.py của backend.
 * Giao diện dùng để chỉ hiện hành động hợp lệ; backend vẫn kiểm tra lại mọi thao tác.
 */

export interface Actor {
  userId: number
  can: (permission: string) => boolean
  /** Dự án đã hoàn thành hoặc đóng. */
  readOnly: boolean
}

export type ActionKey = 'start' | 'submit' | 'back' | 'approve' | 'reject' | 'reopen' | 'cancel' | 'restore'

export interface TaskAction {
  key: ActionKey
  label: string
  /** Trạng thái đích. Duyệt và từ chối đi qua hộp xét duyệt thay vì chuyển thẳng. */
  to: TaskStatus
  /** Lý do người dùng hiện tại chưa làm được, hoặc null nếu làm được. */
  reason: string | null
  primary?: boolean
  /** Hành động phụ: chỉ hiện trong khung chi tiết, không hiện trên thẻ. */
  secondary?: boolean
}

const READ_ONLY = 'Dự án đã hoàn thành hoặc đã đóng nên không thay đổi được.'
const NEED_LEAD = 'Cần quyền trưởng nhóm hoặc quản lý dự án.'
const NEED_ASSIGNEE = 'Chỉ người được giao mới làm được.'
const NOT_ASSIGNED = 'Công việc chưa được phân công cho ai.'

export function isAssignee(task: Task, actor: Actor) {
  return task.assignees.includes(actor.userId)
}

/** Người được giao hoặc người có quyền sửa công việc. */
export function canWorkOn(task: Task, actor: Actor) {
  return actor.can('task.update') || isAssignee(task, actor)
}

export function taskActions(task: Task, actor: Actor): TaskAction[] {
  const lead = actor.can('task.update')
  const worker = lead || isAssignee(task, actor)
  const guard = (...checks: (string | false | null)[]) => (actor.readOnly ? READ_ONLY : (checks.find(Boolean) as string | undefined) ?? null)
  const unassigned = task.assignees.length === 0 && NOT_ASSIGNED
  const needWorker = !worker && NEED_ASSIGNEE
  const needLead = !lead && NEED_LEAD
  const cancel: TaskAction = { key: 'cancel', label: 'Hủy công việc', to: 'CANCELLED', reason: guard(needLead), secondary: true }

  switch (task.trang_thai) {
    case 'TODO':
      return [{ key: 'start', label: 'Bắt đầu', to: 'IN_PROGRESS', reason: guard(unassigned, needWorker), primary: true }, cancel]
    case 'IN_PROGRESS':
      return [
        { key: 'submit', label: 'Gửi duyệt', to: 'IN_REVIEW', reason: guard(unassigned, needWorker), primary: true },
        { key: 'back', label: 'Trả về cần làm', to: 'TODO', reason: guard(needWorker), secondary: true },
        cancel,
      ]
    case 'IN_REVIEW': {
      const review = guard(
        !actor.can('task.review') && NEED_LEAD,
        isAssignee(task, actor) && task.assignees.length === 1 && 'Bạn không được tự duyệt công việc của chính mình.',
      )
      return [
        { key: 'approve', label: 'Duyệt', to: 'DONE', reason: review, primary: true },
        { key: 'reject', label: 'Từ chối', to: 'IN_PROGRESS', reason: review },
        cancel,
      ]
    }
    case 'DONE':
      return [{ key: 'reopen', label: 'Mở lại', to: 'IN_PROGRESS', reason: guard((!lead || !actor.can('task.review')) && NEED_LEAD) }]
    case 'CANCELLED':
      return [{ key: 'restore', label: 'Khôi phục', to: 'TODO', reason: guard(needLead) }]
  }
}

/**
 * Hành động tương ứng khi kéo thẻ sang một cột. Trả về null nếu không có bước chuyển đó
 * (ví dụ Cần làm sang Xong). Từ chối chỉ làm bằng nút vì bắt buộc nhập nhận xét.
 */
export function dropAction(task: Task, to: TaskStatus, actor: Actor): TaskAction | null {
  return taskActions(task, actor).find((a) => a.to === to && a.key !== 'reject') ?? null
}
