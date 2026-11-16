from datetime import date

from pydantic import Field, model_validator

from app.enums import (ProjRole, TrangThaiDuAn, TrangThaiMoc, TrangThaiThanhVien)
from app.schemas.common import ORM


class ProjectCreate(ORM):
    ten_du_an: str = Field(min_length=3, max_length=200)
    muc_tieu: str | None = Field(None, max_length=5000)
    ngay_bat_dau: date
    ngay_ket_thuc_du_kien: date
    ngan_sach_gio: float = Field(0, ge=0, le=10_000_000)
    ma_quan_ly: int

    @model_validator(mode="after")
    def _dates(self):
        if self.ngay_ket_thuc_du_kien < self.ngay_bat_dau:
            raise ValueError("ngay_ket_thuc_du_kien phải >= ngay_bat_dau")
        return self


class ProjectInfoUpdate(ORM):          # 1.2 Cập nhật dự án
    version: int
    ten_du_an: str | None = Field(None, min_length=3, max_length=200)
    muc_tieu: str | None = Field(None, max_length=5000)


class ProjectGoalsUpdate(ORM):         # 1.3 Thiết lập mục tiêu & thời gian
    version: int
    muc_tieu: str | None = Field(None, max_length=5000)
    ngay_bat_dau: date | None = None
    ngay_ket_thuc_du_kien: date | None = None
    ngan_sach_gio: float | None = Field(None, ge=0, le=10_000_000)


class StatusIn(ORM):                   # 1.5 cập nhật trạng thái
    trang_thai: TrangThaiDuAn


class CloseIn(ORM):                    # 1.6 Đóng dự án
    force: bool = False
    ghi_chu: str | None = None


class ProjectOut(ORM):
    ma_du_an: int
    ten_du_an: str
    muc_tieu: str | None
    ngay_bat_dau: date
    ngay_ket_thuc_du_kien: date
    ngan_sach_gio: float
    trang_thai: TrangThaiDuAn
    ngay_dong: date | None
    ma_quan_ly: int
    version: int


class MemberAdd(ORM):                  # 1.4
    ma_nguoi_dung: int
    vai_tro: ProjRole = ProjRole.MEMBER


class MemberRoleUpdate(ORM):
    vai_tro: ProjRole


class MemberOut(ORM):
    ma_du_an: int
    ma_nguoi_dung: int
    ho_ten: str
    email: str
    vai_tro: str
    ngay_tham_gia: date
    ngay_roi: date | None
    trang_thai: TrangThaiThanhVien


class MilestoneIn(ORM):
    ten_moc: str = Field(min_length=2, max_length=200)
    han_hoan_thanh: date


class MilestoneUpdate(ORM):
    ten_moc: str | None = Field(None, min_length=2, max_length=200)
    han_hoan_thanh: date | None = None
    trang_thai: TrangThaiMoc | None = None


class MilestoneOut(ORM):
    ma_moc: int
    ma_du_an: int
    ten_moc: str
    han_hoan_thanh: date
    trang_thai: TrangThaiMoc
