from datetime import date, datetime
from typing import Literal

from pydantic import Field, model_validator

from app.enums import TrangThaiViPham
from app.schemas.common import ORM


class RuleIn(ORM):
    ten_quy_dinh: str = Field(min_length=2, max_length=200)
    diem_tru: float = Field(gt=0, le=100)
    tu_ngay: date
    den_ngay: date | None = None

    @model_validator(mode="after")
    def _d(self):
        if self.den_ngay and self.den_ngay < self.tu_ngay:
            raise ValueError("den_ngay phải >= tu_ngay")
        return self


class RuleUpdate(ORM):
    ten_quy_dinh: str | None = Field(None, min_length=2, max_length=200)
    diem_tru: float | None = Field(None, gt=0, le=100)
    tu_ngay: date | None = None
    den_ngay: date | None = None


class RuleOut(ORM):
    ma_qd: int
    ten_quy_dinh: str
    diem_tru: float
    tu_ngay: date
    den_ngay: date | None


class ViolationIn(ORM):                # 5.1 Ghi nhận & phân loại vi phạm
    ma_cv: int
    ma_nd: int
    ma_qd: int
    noi_dung: str = Field(min_length=5, max_length=5000)


class ExplainIn(ORM):                  # đơn giải trình, bằng chứng
    noi_dung: str = Field(min_length=5, max_length=5000)
    duong_dan_bang_chung: str | None = Field(None, max_length=500)


class ConcludeIn(ORM):                 # 5.2 kết luận
    ket_luan: Literal["CONFIRMED", "DISMISSED"]
    ghi_chu: str = Field(min_length=3, max_length=5000)
    ma_ky_ap_dung: int | None = None


class ExplanationOut(ORM):
    ma_gt: int
    ma_vp: int
    noi_dung: str
    thoi_diem_gui: datetime
    duong_dan_bang_chung: str | None


class ViolationOut(ORM):
    ma_vp: int
    ma_cv: int
    ma_nd: int
    ma_nguoi_lap: int
    ma_qd: int
    noi_dung: str
    trang_thai: TrangThaiViPham
    thoi_diem: datetime
    han_giai_trinh: datetime | None
    ngay_xu_ly: date | None
    ket_luan: str | None
    ma_nguoi_xu_ly: int | None
    ma_ky_ap_dung: int | None
    diem_tru: float | None = None
    giai_trinh: list[ExplanationOut] = []
