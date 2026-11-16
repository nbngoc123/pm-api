import { useOutletContext } from 'react-router-dom'
import type { Project } from '@/api/types'

export interface ProjectContext {
  project: Project
  /** Dự án đã hoàn thành hoặc đóng: backend từ chối mọi thay đổi. */
  readOnly: boolean
  can: (permission: string) => boolean
}

export function useProjectContext() {
  return useOutletContext<ProjectContext>()
}

/** Lý do một hành động ghi không dùng được trong dự án hiện tại, hoặc null nếu dùng được. */
export function blockedReason(ctx: ProjectContext, permission: string, roleHint: string): string | null {
  if (ctx.readOnly) return 'Dự án đã hoàn thành hoặc đã đóng nên không thay đổi được.'
  if (!ctx.can(permission)) return `Cần quyền ${roleHint}.`
  return null
}
