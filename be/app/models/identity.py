"""NGƯỜI DÙNG, VAI TRÒ, QUYỀN, QUẢN LÝ / NHÂN VIÊN (ISA)."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.enums import LoaiNguoiDung, PhamVi, TrangThaiNguoiDung
from app.security import utcnow


def E(cls):
    return SAEnum(cls, native_enum=False, length=30, validate_strings=True, create_constraint=False)


class Quyen(Base):
    __tablename__ = "quyen"
    ma_quyen: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    ten_quyen: Mapped[str] = mapped_column(String(120))
    mo_ta: Mapped[str | None] = mapped_column(String(255))


class VaiTro(Base):
    __tablename__ = "vai_tro"
    ma_vai_tro: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    ten_vai_tro: Mapped[str] = mapped_column(String(100))
    pham_vi: Mapped[PhamVi] = mapped_column(E(PhamVi))


class VaiTroQuyen(Base):
    __tablename__ = "vai_tro_quyen"
    ma_vai_tro: Mapped[int] = mapped_column(ForeignKey("vai_tro.ma_vai_tro"), primary_key=True)
    ma_quyen: Mapped[int] = mapped_column(ForeignKey("quyen.ma_quyen"), primary_key=True)


class NguoiDung(Base):
    __tablename__ = "nguoi_dung"
    ma_nd: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    ho_ten: Mapped[str] = mapped_column(String(150))
    mat_khau_hash: Mapped[str] = mapped_column(String(255))
    ma_vai_tro_he_thong: Mapped[int] = mapped_column(ForeignKey("vai_tro.ma_vai_tro"), index=True)
    trang_thai: Mapped[TrangThaiNguoiDung] = mapped_column(E(TrangThaiNguoiDung), default=TrangThaiNguoiDung.ACTIVE)
    loai: Mapped[LoaiNguoiDung] = mapped_column(E(LoaiNguoiDung), default=LoaiNguoiDung.NHAN_VIEN)
    token_version: Mapped[int] = mapped_column(Integer, default=0)       # mở rộng: thu hồi token
    so_lan_dang_nhap_sai: Mapped[int] = mapped_column(Integer, default=0)  # mở rộng: khóa tạm
    khoa_den: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class QuanLy(Base):
    __tablename__ = "quan_ly"
    ma_nd: Mapped[int] = mapped_column(ForeignKey("nguoi_dung.ma_nd"), primary_key=True)


class NhanVien(Base):
    __tablename__ = "nhan_vien"
    ma_nd: Mapped[int] = mapped_column(ForeignKey("nguoi_dung.ma_nd"), primary_key=True)
    ma_quan_ly: Mapped[int | None] = mapped_column(ForeignKey("quan_ly.ma_nd"), index=True)
    don_gia_gio: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
