from enum import StrEnum


class TrangThaiNguoiDung(StrEnum):
    ACTIVE = "ACTIVE"; LOCKED = "LOCKED"; INACTIVE = "INACTIVE"

class LoaiNguoiDung(StrEnum):          # ISA: NGƯỜI DÙNG -> QUẢN LÝ | NHÂN VIÊN
    QUAN_LY = "QUAN_LY"; NHAN_VIEN = "NHAN_VIEN"

class PhamVi(StrEnum):
    SYSTEM = "SYSTEM"; PROJECT = "PROJECT"

class TrangThaiDuAn(StrEnum):
    PLANNING = "PLANNING"; ACTIVE = "ACTIVE"; ON_HOLD = "ON_HOLD"; COMPLETED = "COMPLETED"; CLOSED = "CLOSED"

class TrangThaiThanhVien(StrEnum):
    ACTIVE = "ACTIVE"; LEFT = "LEFT"

class TrangThaiMoc(StrEnum):
    PENDING = "PENDING"; ACHIEVED = "ACHIEVED"; MISSED = "MISSED"

class TrangThaiTask(StrEnum):
    TODO = "TODO"; IN_PROGRESS = "IN_PROGRESS"; IN_REVIEW = "IN_REVIEW"; DONE = "DONE"; CANCELLED = "CANCELLED"

class UuTien(StrEnum):
    LOW = "LOW"; MEDIUM = "MEDIUM"; HIGH = "HIGH"; CRITICAL = "CRITICAL"

class TrangThaiPhanCong(StrEnum):
    ASSIGNED = "ASSIGNED"; COMPLETED = "COMPLETED"; CANCELLED = "CANCELLED"

class KetQuaDuyet(StrEnum):
    APPROVED = "APPROVED"; REJECTED = "REJECTED"

class TrangThaiViPham(StrEnum):
    DRAFT = "DRAFT"; PENDING_EXPLANATION = "PENDING_EXPLANATION"; EXPLAINED = "EXPLAINED"
    CONFIRMED = "CONFIRMED"; DISMISSED = "DISMISSED"

class TrangThaiKy(StrEnum):
    DRAFT = "DRAFT"; OPEN = "OPEN"; CLOSED = "CLOSED"

class TrangThaiDanhGia(StrEnum):
    DRAFT = "DRAFT"; PROVISIONAL = "PROVISIONAL"; MEMBER_CONFIRMED = "MEMBER_CONFIRMED"
    APPROVED = "APPROVED"; REJECTED = "REJECTED"

class NguonDuLieuKPI(StrEnum):
    TASK_COMPLETION = "TASK_COMPLETION"; ON_TIME_RATE = "ON_TIME_RATE"
    HOURS_UTILIZATION = "HOURS_UTILIZATION"; MANUAL = "MANUAL"

# Mã vai trò hệ thống / dự án
class SysRole(StrEnum):
    ADMIN = "ADMIN"; DIRECTOR = "DIRECTOR"; MANAGER = "MANAGER"; EMPLOYEE = "EMPLOYEE"

class ProjRole(StrEnum):
    PM = "PM"; TEAM_LEAD = "TEAM_LEAD"; MEMBER = "MEMBER"
