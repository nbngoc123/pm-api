export type Tone = 'primary' | 'success' | 'warning' | 'danger' | 'purple' | 'neutral' | 'muted'

export interface StatusMeta {
  text: string
  tone?: Tone
}

export const SYSTEM_ROLE: Record<string, string> = {
  ADMIN: 'Quản trị hệ thống',
  DIRECTOR: 'Ban giám đốc',
  MANAGER: 'Quản lý',
  EMPLOYEE: 'Nhân viên',
}

export const PROJECT_ROLE: Record<string, string> = {
  PM: 'Quản lý dự án',
  TEAM_LEAD: 'Trưởng nhóm',
  MEMBER: 'Thành viên',
}

export const PROJECT_STATUS: Record<string, StatusMeta> = {
  PLANNING: { text: 'Lập kế hoạch', tone: 'neutral' },
  ACTIVE: { text: 'Đang triển khai', tone: 'success' },
  ON_HOLD: { text: 'Tạm dừng', tone: 'warning' },
  COMPLETED: { text: 'Hoàn thành', tone: 'primary' },
  CLOSED: { text: 'Đã đóng', tone: 'muted' },
}

export const TASK_STATUS: Record<string, StatusMeta> = {
  TODO: { text: 'Cần làm', tone: 'neutral' },
  IN_PROGRESS: { text: 'Đang làm', tone: 'primary' },
  IN_REVIEW: { text: 'Chờ duyệt', tone: 'warning' },
  DONE: { text: 'Hoàn thành', tone: 'success' },
  CANCELLED: { text: 'Đã hủy', tone: 'muted' },
}

export const BOARD_COLUMNS: ('TODO' | 'IN_PROGRESS' | 'IN_REVIEW' | 'DONE')[] = [
  'TODO',
  'IN_PROGRESS',
  'IN_REVIEW',
  'DONE',
]

export const PRIORITY: Record<string, StatusMeta> = {
  LOW: { text: 'Thấp', tone: 'muted' },
  MEDIUM: { text: 'Vừa', tone: 'neutral' },
  HIGH: { text: 'Cao', tone: 'warning' },
  CRITICAL: { text: 'Khẩn cấp', tone: 'danger' },
}

export const URGENCY: Record<string, StatusMeta> = {
  OVERDUE: { text: 'Quá hạn', tone: 'danger' },
  URGENT: { text: 'Gấp', tone: 'warning' },
  SOON: { text: 'Sắp tới', tone: 'neutral' },
  NORMAL: { text: 'Bình thường', tone: 'muted' },
  NO_DEADLINE: { text: 'Không hạn', tone: 'muted' },
}

export const MILESTONE_STATUS: Record<string, StatusMeta> = {
  PENDING: { text: 'Chưa đạt', tone: 'neutral' },
  ACHIEVED: { text: 'Đạt được', tone: 'success' },
  MISSED: { text: 'Bỏ lỡ', tone: 'danger' },
}

export const PERIOD_STATUS: Record<string, StatusMeta> = {
  DRAFT: { text: 'Dự thảo', tone: 'neutral' },
  OPEN: { text: 'Đang mở', tone: 'success' },
  CLOSED: { text: 'Đã đóng', tone: 'muted' },
}

export const EVAL_STATUS: Record<string, StatusMeta> = {
  DRAFT: { text: 'Dự thảo', tone: 'neutral' },
  PROVISIONAL: { text: 'Tạm tính', tone: 'warning' },
  MEMBER_CONFIRMED: { text: 'Đã xác nhận', tone: 'primary' },
  APPROVED: { text: 'Đã duyệt', tone: 'success' },
  REJECTED: { text: 'Từ chối', tone: 'danger' },
}

export const VIOLATION_STATUS: Record<string, StatusMeta> = {
  DRAFT: { text: 'Dự thảo', tone: 'neutral' },
  PENDING_EXPLANATION: { text: 'Chờ giải trình', tone: 'warning' },
  EXPLAINED: { text: 'Đã giải trình', tone: 'primary' },
  CONFIRMED: { text: 'Đã xử phạt', tone: 'danger' },
  DISMISSED: { text: 'Bác bỏ', tone: 'success' },
}
