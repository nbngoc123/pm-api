from datetime import date, datetime

from pydantic import Field, model_validator

from app.schemas.common import ORM


class BaselineIn(ORM):
    ngay_bat_dau_goc: date
    ngay_ket_thuc_goc: date
    gio_du_kien_goc: float = Field(ge=0, le=10000)
    chi_phi_ke_hoach_goc: float = Field(ge=0)

    @model_validator(mode="after")
    def _d(self):
        if self.ngay_ket_thuc_goc < self.ngay_bat_dau_goc:
            raise ValueError("ngay_ket_thuc_goc phải >= ngay_bat_dau_goc")
        return self


class BaselineOut(ORM):
    ma_cv: int
    ngay_bat_dau_goc: date
    ngay_ket_thuc_goc: date
    gio_du_kien_goc: float
    chi_phi_ke_hoach_goc: float
    khoa_luc: datetime | None


class SnapshotOut(ORM):
    ma_cs: int
    ma_du_an: int
    ngay: date
    pv: float
    ev: float
    ac: float
    spi: float | None
    cpi: float | None


class NotificationOut(ORM):
    ma_tb: int
    loai: str
    tieu_de: str
    noi_dung: str | None
    ma_cv: int | None
    da_doc: bool
    created_at: datetime


class AuditOut(ORM):
    ma_log: int
    ma_nguoi_thuc_hien: int | None
    thoi_diem: datetime
    loai_su_kien: str
    noi_dung: str | None
    doi_tuong: str | None
    ma_doi_tuong: int | None
    ma_du_an: int | None = None
