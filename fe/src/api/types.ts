import type { components } from './schema'

type S = components['schemas']

export type User = S['UserOut']
export type Me = S['MeOut']
export type TokenOut = S['TokenOut']
export type UserLookup = S['UserLookup']
export type Project = S['ProjectOut']
export type Member = S['MemberOut']
export type Milestone = S['MilestoneOut']
export type Task = S['TaskOut']
export type Assignment = S['AssignOut']
export type AssignResult = S['AssignResult']
export type Review = S['ReviewOut']
export type SubTask = S['SubTaskOut']
export type Attachment = S['AttachmentOut']
export type Timesheet = S['TimesheetOut']
export type Notification = S['NotificationOut']
export type Period = S['PeriodOut']
export type KpiCriterion = S['CriterionOut']
export type EvalStatus = 'DRAFT' | 'PROVISIONAL' | 'MEMBER_CONFIRMED' | 'APPROVED' | 'REJECTED'

export interface KpiConfigItem {
  ma_tieu_chi: number
  ten_tieu_chi: string
  nguon_du_lieu: 'TASK_COMPLETION' | 'ON_TIME_RATE' | 'HOURS_UTILIZATION' | 'MANUAL'
  trong_so: number
  chi_tieu: number
}

export interface KpiConfig {
  ma_ky: number
  items: KpiConfigItem[]
  tong_trong_so: number
}

/** Một dòng tiêu chí trong bảng điểm của một người. */
export interface KpiDetail {
  ma_tieu_chi: number
  ten_tieu_chi: string
  trong_so: number
  chi_tieu: number
  gia_tri_tu_dong: number | null
  gia_tri_thu_cong: number | null
  gia_tri_xac_nhan: number | null
  ty_le_dat: number | null
  ghi_chu: string | null
}

export interface Evaluation extends Omit<S['EvaluationOut'], 'chi_tiet' | 'trang_thai'> {
  trang_thai: EvalStatus
  chi_tiet: KpiDetail[]
}
export type Epic = S['EpicOut']
export type Violation = S['ViolationOut']
export type Rule = S['RuleOut']
export type Explanation = S['ExplanationOut']

export type TaskStatus = Task['trang_thai']
export type Priority = Task['uu_tien']
export type ProjectStatus = Project['trang_thai']
export type MilestoneStatus = Milestone['trang_thai']
export type ProjectRole = 'PM' | 'TEAM_LEAD' | 'MEMBER'
export type Urgency = 'OVERDUE' | 'URGENT' | 'SOON' | 'NORMAL' | 'NO_DEADLINE'

export interface Page<T> {
  items: T[]
  total: number
  page: number
  size: number
}

/** Các endpoint dưới đây backend không khai báo response_model nên phải tự mô tả kiểu. */
export interface ProjectPermissions {
  vai_tro: ProjectRole | null
  permissions: string[]
}

export interface ProjectOverview {
  ma_du_an: number
  ten_du_an: string
  trang_thai: ProjectStatus
  task_theo_trang_thai: Partial<Record<TaskStatus, number>>
  tong_task: number
  task_hoan_thanh: number
  ty_le_hoan_thanh: number
  task_tre_han: number
  so_thanh_vien: number
  gio_thuc_te: number
  ngan_sach_gio: number
  ty_le_su_dung_ngan_sach_gio: number | null
  moc_theo_trang_thai: Partial<Record<MilestoneStatus, number>>
  so_ngay_con_lai: number
}

export interface Dashboard {
  task_theo_trang_thai: Partial<Record<TaskStatus, number>>
  task_tre_han: number
  deadline_sap_toi: { ma_cv: number; ten_cv: string; han_hoan_thanh: string; uu_tien: Priority }[]
  gio_tuan_nay: number
  gio_thang_nay: number
  gio_trong_khoang: number | null
  vi_pham_cho_giai_trinh: number
  kpi_gan_nhat: { ma_ky: number; trang_thai: string; diem_tong: number | null } | null
  thong_bao_chua_doc: number
  so_du_an: number
}

export interface TimesheetSummary {
  tong_gio: number
  tong_chi_phi: number
  theo_du_an: { ma_du_an: number; gio: number; chi_phi: number }[]
}

export interface AssignWarning {
  code: string
  message: string
}
