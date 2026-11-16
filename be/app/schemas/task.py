from datetime import date, datetime, timezone

from pydantic import Field, field_validator, model_validator

from app.enums import KetQuaDuyet, TrangThaiPhanCong, TrangThaiTask, UuTien
from app.schemas.common import ORM


class TaskCreate(ORM):
    ten_cv: str = Field(min_length=1, max_length=200)
    mo_ta: str | None = Field(None, max_length=10000)
    ma_moc: int | None = None
    ma_epic: int | None = None
    uu_tien: UuTien = UuTien.MEDIUM
    ngay_bat_dau_du_kien: date | None = None
    han_hoan_thanh: date | None = None
    gio_du_kien: float = Field(0, ge=0, le=10000)

    @model_validator(mode="after")
    def _d(self):
        if self.ngay_bat_dau_du_kien and self.han_hoan_thanh and self.han_hoan_thanh < self.ngay_bat_dau_du_kien:
            raise ValueError("han_hoan_thanh phải >= ngay_bat_dau_du_kien")
        return self


class TaskUpdate(ORM):
    version: int
    ten_cv: str | None = Field(None, min_length=1, max_length=200)
    mo_ta: str | None = Field(None, max_length=10000)
    ma_moc: int | None = None
    ma_epic: int | None = None
    uu_tien: UuTien | None = None
    ngay_bat_dau_du_kien: date | None = None
    han_hoan_thanh: date | None = None
    gio_du_kien: float | None = Field(None, ge=0, le=10000)


class TransitionIn(ORM):
    trang_thai: TrangThaiTask


class ProgressIn(ORM):
    ty_le_hoan_thanh: int = Field(ge=0, le=100)


class TaskOut(ORM):
    ma_cv: int
    ma_du_an: int
    ma_moc: int | None
    ma_epic: int | None
    ten_cv: str
    mo_ta: str | None
    trang_thai: TrangThaiTask
    uu_tien: UuTien
    ty_le_hoan_thanh: int
    ngay_bat_dau_du_kien: date | None
    han_hoan_thanh: date | None
    gio_du_kien: float
    ma_nguoi_tao: int
    hoan_thanh_luc: datetime | None
    version: int
    assignees: list[int] = []
    muc_do_khan: str | None = None
    tre_han: bool = False


class EpicIn(ORM):
    ten_epic: str = Field(min_length=1, max_length=200)
    mo_ta: str | None = None


class EpicOut(ORM):
    ma_epic: int
    ma_du_an: int
    ten_epic: str
    mo_ta: str | None
    trang_thai: str


class SubTaskIn(ORM):
    ten_subtask: str = Field(min_length=1, max_length=200)
    mo_ta: str | None = None


class SubTaskUpdate(ORM):
    ten_subtask: str | None = Field(None, min_length=1, max_length=200)
    mo_ta: str | None = None
    trang_thai: str | None = Field(None, pattern="^(TODO|DONE)$")


class SubTaskOut(ORM):
    ma_subtask: int
    ma_cv: int
    ten_subtask: str
    mo_ta: str | None
    trang_thai: str


class AssignIn(ORM):
    ma_nd: int
    gio_du_kien: float | None = Field(None, ge=0, le=10000)


class AssignOut(ORM):
    ma_cv: int
    ma_nd: int
    trang_thai_phan_cong: TrangThaiPhanCong
    ngay_giao: date
    gio_du_kien: float
    ma_nguoi_giao: int


class AssignResult(ORM):
    phan_cong: AssignOut
    warnings: list[dict] = []


class ReviewIn(ORM):
    ket_qua: KetQuaDuyet
    nhan_xet: str | None = Field(None, max_length=5000)


class ReviewOut(ORM):
    ma_duyet: int
    ma_cv: int
    ma_nguoi_duyet: int
    ket_qua: KetQuaDuyet
    nhan_xet: str | None
    thoi_diem_duyet: datetime


class AttachmentOut(ORM):
    ma_tep: int
    ma_cv: int
    ten_tep: str
    kich_thuoc: int
    ma_nguoi_tai: int
    thoi_diem_tai: datetime


def _utc_naive(v):
    """Client có thể gửi '+07:00' hoặc 'Z' -> quy về UTC naive (quy ước lưu trữ toàn hệ thống)."""
    if v is not None and v.tzinfo is not None:
        return v.astimezone(timezone.utc).replace(tzinfo=None)
    return v


class TimesheetIn(ORM):
    bat_dau: datetime
    ket_thuc: datetime
    noi_dung: str | None = Field(None, max_length=2000)
    _tz = field_validator("bat_dau", "ket_thuc")(_utc_naive)


class TimesheetUpdate(ORM):
    bat_dau: datetime | None = None
    ket_thuc: datetime | None = None
    noi_dung: str | None = Field(None, max_length=2000)
    _tz = field_validator("bat_dau", "ket_thuc")(_utc_naive)


class TimesheetOut(ORM):
    ma_nk: int
    ma_cv: int
    ma_nd: int
    bat_dau: datetime
    ket_thuc: datetime
    so_gio: float
    noi_dung: str | None
    chi_phi_thuc_te: float
    tong_gio_tich_luy_task: float | None = None
    tong_gio_tich_luy_du_an: float | None = None
