import { createContext, useContext } from 'react'
import type { Member, Task } from '@/api/types'
import type { Actor, TaskAction } from './rules'

interface TaskBoardContextValue {
  projectId: number
  actor: Actor
  /** Thành viên dự án theo mã người dùng, để hiện tên từ mảng assignees. */
  members: Map<number, Member>
  /** Thực hiện một hành động trên task: chuyển trạng thái, hoặc mở hộp xét duyệt. */
  run: (task: Task, action: TaskAction) => void
  openTask: (taskId: number) => void
}

export const TaskBoardContext = createContext<TaskBoardContextValue | null>(null)

export function useTaskBoard() {
  const ctx = useContext(TaskBoardContext)
  if (!ctx) throw new Error('useTaskBoard phải được gọi bên trong TaskBoardPage')
  return ctx
}
