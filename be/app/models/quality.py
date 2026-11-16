"""VI PHẠM, QUY ĐỊNH, GIẢI TRÌNH, KPI, NHẬT KÝ HỆ THỐNG và các bảng mở rộng (thông báo, snapshot chỉ số)."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, ForeignKeyConstraint, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.enums import NguonDuLieuKPI, TrangThaiDanhGia, TrangThaiKy, TrangThaiViPham
from app.models.identity import E
from app.security import utcnow


class QuyDinhViPham(Base):
    __tablename__ = "quy_dinh_vi_pham"
    ma_qd: Mapped[int] = mapped_column(primary_key=True)
    ten_quy_dinh: Mapped[str] = mapped_column(String(200))
    diem_tru: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    tu_ngay: Mapped[date] = mapped_column(Date)
    den_ngay: Mapped[date | None] = mapped_column(Date)


class KyKPI(Base):
    __tablename__ = "ky_kpi"
    ma_ky: Mapped[int] = mapped_column(primary_key=True)
    ma_du_an: Mapped[int] = mapped_column(ForeignKey("du_an.ma_du_an"), index=True)
    ten_ky: Mapped[str] = mapped_column(String(120))
    tu_ngay: Mapped[date] = mapped_column(Date)
    den_ngay: Mapped[date] = mapped_column(Date)
    trang_thai: Mapped[TrangThaiKy] = mapped_column(E(TrangThaiKy), default=TrangThaiKy.DRAFT)


class ViPham(Base):
    __tablename__ = "vi_pham"
    ma_vp: Mapped[int] = mapped_column(primary_key=True)
    ma_cv: Mapped[int] = mapped_column(ForeignKey("task.ma_cv"), index=True)
    ma_nd: Mapped[int] = mapped_column(ForeignKey("nhan_vien.ma_nd"), index=True)    # ERD: NHÂN VIÊN "Bị ghi nhận"
    ma_nguoi_lap: Mapped[int] = mapped_column(ForeignKey("nguoi_dung.ma_nd"))
    ma_qd: Mapped[int] = mapped_column(ForeignKey("quy_dinh_vi_pham.ma_qd"))
    noi_dung: Mapped[str] = mapped_column(Text)
    trang_thai: Mapped[TrangThaiViPham] = mapped_column(E(TrangThaiViPham), default=TrangThaiViPham.DRAFT, index=True)
    thoi_diem: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    han_giai_trinh: Mapped[datetime | None] = mapped_column(DateTime)       # mở rộng
    ngay_xu_ly: Mapped[date | None] = mapped_column(Date)
    ket_luan: Mapped[str | None] = mapped_column(Text)
    ma_nguoi_xu_ly: Mapped[int | None] = mapped_column(ForeignKey("quan_ly.ma_nd"))   # ERD: QUẢN LÝ "Kết luận"
    ma_ky_ap_dung: Mapped[int | None] = mapped_column(ForeignKey("ky_kpi.ma_ky"), index=True)


class GiaiTrinh(Base):
    __tablename__ = "giai_trinh"
    ma_gt: Mapped[int] = mapped_column(primary_key=True)
    ma_vp: Mapped[int] = mapped_column(ForeignKey("vi_pham.ma_vp"), index=True)   # ERD: GIẢI TRÌNH N–1 VI PHẠM
    noi_dung: Mapped[str] = mapped_column(Text)
    thoi_diem_gui: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    duong_dan_bang_chung: Mapped[str | None] = mapped_column(String(500))


class TieuChiKPI(Base):
    __tablename__ = "tieu_chi_kpi"
    ma_tieu_chi: Mapped[int] = mapped_column(primary_key=True)
    ten_tieu_chi: Mapped[str] = mapped_column(String(150), unique=True)
    mo_ta_cach_tinh: Mapped[str | None] = mapped_column(Text)
    don_vi: Mapped[str | None] = mapped_column(String(30))
    nguon_du_lieu: Mapped[NguonDuLieuKPI] = mapped_column(E(NguonDuLieuKPI), default=NguonDuLieuKPI.MANUAL)


class CauHinhKPI(Base):
    __tablename__ = "cau_hinh_kpi"
    ma_ky: Mapped[int] = mapped_column(ForeignKey("ky_kpi.ma_ky"), primary_key=True)
    ma_tieu_chi: Mapped[int] = mapped_column(ForeignKey("tieu_chi_kpi.ma_tieu_chi"), primary_key=True)
    trong_so: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    chi_tieu: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class DanhGiaKPI(Base):
    """ERD: khóa ghép (Mã kỳ, Mã người dùng)."""
    __tablename__ = "danh_gia_kpi"
    ma_ky: Mapped[int] = mapped_column(ForeignKey("ky_kpi.ma_ky"), primary_key=True)
    ma_nguoi_dung: Mapped[int] = mapped_column(ForeignKey("nguoi_dung.ma_nd"), primary_key=True, index=True)
    ma_nguoi_duyet: Mapped[int | None] = mapped_column(ForeignKey("quan_ly.ma_nd"))   # ERD: QUẢN LÝ "Phê duyệt"
    trang_thai: Mapped[TrangThaiDanhGia] = mapped_column(E(TrangThaiDanhGia), default=TrangThaiDanhGia.DRAFT)
    ngay_xac_nhan: Mapped[date | None] = mapped_column(Date)
    ngay_duyet: Mapped[date | None] = mapped_column(Date)
    diem_goc: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    diem_tru: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    diem_tong: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    nhan_xet: Mapped[str | None] = mapped_column(Text)


class ChiTietKPI(Base):
    __tablename__ = "chi_tiet_kpi"
    ma_nguoi_dung: Mapped[int] = mapped_column(ForeignKey("nguoi_dung.ma_nd"), primary_key=True)
    ma_ky: Mapped[int] = mapped_column(ForeignKey("ky_kpi.ma_ky"), primary_key=True)
    ma_tieu_chi: Mapped[int] = mapped_column(ForeignKey("tieu_chi_kpi.ma_tieu_chi"), primary_key=True)
    gia_tri_tu_dong: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    gia_tri_thu_cong: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    gia_tri_xac_nhan: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    ghi_chu: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        ForeignKeyConstraint(["ma_ky", "ma_tieu_chi"], ["cau_hinh_kpi.ma_ky", "cau_hinh_kpi.ma_tieu_chi"]),      # CẤU HÌNH KPI 1–N CHI TIẾT KPI
        ForeignKeyConstraint(["ma_ky", "ma_nguoi_dung"], ["danh_gia_kpi.ma_ky", "danh_gia_kpi.ma_nguoi_dung"]),  # ĐÁNH GIÁ KPI 1–N CHI TIẾT KPI ("Gồm")
    )


class NhatKyHeThong(Base):
    __tablename__ = "nhat_ky_he_thong"
    ma_log: Mapped[int] = mapped_column(primary_key=True)
    ma_nguoi_thuc_hien: Mapped[int | None] = mapped_column(ForeignKey("nguoi_dung.ma_nd"), index=True)
    ma_du_an: Mapped[int | None] = mapped_column(ForeignKey("du_an.ma_du_an"), index=True)   # ERD: DỰ ÁN 1–N NHẬT KÝ HỆ THỐNG ("Phát sinh")
    thoi_diem: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    loai_su_kien: Mapped[str] = mapped_column(String(60), index=True)
    noi_dung: Mapped[str | None] = mapped_column(Text)
    doi_tuong: Mapped[str | None] = mapped_column(String(40))
    ma_doi_tuong: Mapped[int | None] = mapped_column(Integer)


# ---- bảng mở rộng (không có trong ERD, cần cho DFD 3.2 / 3.3 / 1.5) ----
class ThongBao(Base):
    __tablename__ = "thong_bao"
    ma_tb: Mapped[int] = mapped_column(primary_key=True)
    ma_nd: Mapped[int] = mapped_column(ForeignKey("nguoi_dung.ma_nd"), index=True)
    loai: Mapped[str] = mapped_column(String(40))
    tieu_de: Mapped[str] = mapped_column(String(255))
    noi_dung: Mapped[str | None] = mapped_column(Text)
    ma_cv: Mapped[int | None] = mapped_column(ForeignKey("task.ma_cv"))
    da_doc: Mapped[bool] = mapped_column(Boolean, default=False)
    dedupe_key: Mapped[str | None] = mapped_column(String(120), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ChiSoDuAn(Base):
    __tablename__ = "chi_so_du_an"
    ma_cs: Mapped[int] = mapped_column(primary_key=True)
    ma_du_an: Mapped[int] = mapped_column(ForeignKey("du_an.ma_du_an"), index=True)
    ngay: Mapped[date] = mapped_column(Date)
    pv: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    ev: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    ac: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    spi: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    cpi: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    __table_args__ = (UniqueConstraint("ma_du_an", "ngay", name="uq_chi_so_ngay"),)
