from datetime import date

from pydantic import Field, model_validator

from app.enums import NguonDuLieuKPI, TrangThaiDanhGia, TrangThaiKy
from app.schemas.common import ORM


class CriterionIn(ORM):
    ten_tieu_chi: str = Field(min_length=2, max_length=150)
    mo_ta_cach_tinh: str | None = None
    don_vi: str | None = Field(None, max_length=30)
    nguon_du_lieu: NguonDuLieuKPI = NguonDuLieuKPI.MANUAL


class CriterionUpdate(ORM):
    ten_tieu_chi: str | None = Field(None, min_length=2, max_length=150)
    mo_ta_cach_tinh: str | None = None
    don_vi: str | None = Field(None, max_length=30)
    nguon_du_lieu: NguonDuLieuKPI | None = None


class CriterionOut(ORM):
    ma_tieu_chi: int
    ten_tieu_chi: str
    mo_ta_cach_tinh: str | None
    don_vi: str | None
    nguon_du_lieu: NguonDuLieuKPI


class PeriodIn(ORM):
    ten_ky: str = Field(min_length=2, max_length=120)
    tu_ngay: date
    den_ngay: date

    @model_validator(mode="after")
    def _d(self):
        if self.den_ngay < self.tu_ngay:
            raise ValueError("den_ngay phải >= tu_ngay")
        return self


class PeriodOut(ORM):
    ma_ky: int
    ma_du_an: int
    ten_ky: str
    tu_ngay: date
    den_ngay: date
    trang_thai: TrangThaiKy


class ConfigItem(ORM):
    ma_tieu_chi: int
    trong_so: float = Field(gt=0, le=100)
    chi_tieu: float = Field(gt=0, le=100000)


class ConfigIn(ORM):
    items: list[ConfigItem] = Field(min_length=1, max_length=20)


class ConfigOut(ORM):
    ma_ky: int
    items: list[dict]
    tong_trong_so: float


class ManualItem(ORM):
    ma_nd: int
    ma_tieu_chi: int
    gia_tri: float = Field(ge=0, le=100000)
    ghi_chu: str | None = None


class ManualIn(ORM):
    items: list[ManualItem] = Field(min_length=1, max_length=500)


class DecisionIn(ORM):
    nhan_xet: str | None = Field(None, max_length=5000)


class EvaluationOut(ORM):
    diem_ky_truoc: float | None = None
    ma_ky: int
    ma_nguoi_dung: int
    ho_ten: str
    trang_thai: TrangThaiDanhGia
    diem_goc: float | None
    diem_tru: float
    diem_tong: float | None
    ma_nguoi_duyet: int | None
    ngay_xac_nhan: date | None
    ngay_duyet: date | None
    nhan_xet: str | None
    chi_tiet: list[dict] = []
