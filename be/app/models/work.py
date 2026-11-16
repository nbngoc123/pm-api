"""DỰ ÁN, THÀNH VIÊN DỰ ÁN, MỐC, EPIC, TASK, SUB TASK, KẾ HOẠCH GỐC, TỆP, PHÂN CÔNG, NHẬT KÝ GIỜ LÀM, XÉT DUYỆT."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.enums import (KetQuaDuyet, TrangThaiDuAn, TrangThaiMoc, TrangThaiPhanCong, TrangThaiTask,
                       TrangThaiThanhVien, UuTien)
from app.models.identity import E
from app.security import utcnow


class DuAn(Base):
    __tablename__ = "du_an"
    ma_du_an: Mapped[int] = mapped_column(primary_key=True)
    ten_du_an: Mapped[str] = mapped_column(String(200), unique=True)
    muc_tieu: Mapped[str | None] = mapped_column(Text)
    ngay_bat_dau: Mapped[date] = mapped_column(Date)
    ngay_ket_thuc_du_kien: Mapped[date] = mapped_column(Date)
    ngan_sach_gio: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    trang_thai: Mapped[TrangThaiDuAn] = mapped_column(E(TrangThaiDuAn), default=TrangThaiDuAn.PLANNING, index=True)
    ngay_dong: Mapped[date | None] = mapped_column(Date)
    ma_quan_ly: Mapped[int] = mapped_column(ForeignKey("quan_ly.ma_nd"), index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("nguoi_dung.ma_nd"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    version: Mapped[int] = mapped_column(Integer, default=1)


class ThanhVienDuAn(Base):
    __tablename__ = "thanh_vien_du_an"
    ma_du_an: Mapped[int] = mapped_column(ForeignKey("du_an.ma_du_an"), primary_key=True)
    ma_nguoi_dung: Mapped[int] = mapped_column(ForeignKey("nguoi_dung.ma_nd"), primary_key=True)
    ma_vai_tro: Mapped[int] = mapped_column(ForeignKey("vai_tro.ma_vai_tro"))
    ngay_tham_gia: Mapped[date] = mapped_column(Date)
    ngay_roi: Mapped[date | None] = mapped_column(Date)
    trang_thai: Mapped[TrangThaiThanhVien] = mapped_column(E(TrangThaiThanhVien), default=TrangThaiThanhVien.ACTIVE)


class MocDuAn(Base):
    __tablename__ = "moc_du_an"
    ma_moc: Mapped[int] = mapped_column(primary_key=True)
    ma_du_an: Mapped[int] = mapped_column(ForeignKey("du_an.ma_du_an"), index=True)
    ten_moc: Mapped[str] = mapped_column(String(200))
    han_hoan_thanh: Mapped[date] = mapped_column(Date)
    trang_thai: Mapped[TrangThaiMoc] = mapped_column(E(TrangThaiMoc), default=TrangThaiMoc.PENDING)


class Epic(Base):
    __tablename__ = "epic"
    ma_epic: Mapped[int] = mapped_column(primary_key=True)
    ma_du_an: Mapped[int] = mapped_column(ForeignKey("du_an.ma_du_an"), index=True)
    ten_epic: Mapped[str] = mapped_column(String(200))
    mo_ta: Mapped[str | None] = mapped_column(Text)
    trang_thai: Mapped[str] = mapped_column(String(30), default="OPEN")


class Task(Base):
    __tablename__ = "task"
    ma_cv: Mapped[int] = mapped_column(primary_key=True)
    ma_du_an: Mapped[int] = mapped_column(ForeignKey("du_an.ma_du_an"), index=True)
    ma_moc: Mapped[int | None] = mapped_column(ForeignKey("moc_du_an.ma_moc"), index=True)
    ma_epic: Mapped[int | None] = mapped_column(ForeignKey("epic.ma_epic"), index=True)
    ten_cv: Mapped[str] = mapped_column(String(200))
    mo_ta: Mapped[str | None] = mapped_column(Text)
    trang_thai: Mapped[TrangThaiTask] = mapped_column(E(TrangThaiTask), default=TrangThaiTask.TODO)
    uu_tien: Mapped[UuTien] = mapped_column(E(UuTien), default=UuTien.MEDIUM)
    ty_le_hoan_thanh: Mapped[int] = mapped_column(Integer, default=0)
    ngay_bat_dau_du_kien: Mapped[date | None] = mapped_column(Date)
    han_hoan_thanh: Mapped[date | None] = mapped_column(Date)
    gio_du_kien: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    ma_nguoi_tao: Mapped[int] = mapped_column(ForeignKey("nguoi_dung.ma_nd"))
    hoan_thanh_luc: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (Index("ix_task_project_status", "ma_du_an", "trang_thai"),)


class SubTask(Base):
    __tablename__ = "sub_task"
    ma_subtask: Mapped[int] = mapped_column(primary_key=True)
    ma_cv: Mapped[int] = mapped_column(ForeignKey("task.ma_cv"), index=True)
    ten_subtask: Mapped[str] = mapped_column(String(200))
    mo_ta: Mapped[str | None] = mapped_column(Text)
    trang_thai: Mapped[str] = mapped_column(String(30), default="TODO")


class KeHoachGoc(Base):
    __tablename__ = "ke_hoach_goc"
    ma_cv: Mapped[int] = mapped_column(ForeignKey("task.ma_cv"), primary_key=True)
    ngay_bat_dau_goc: Mapped[date] = mapped_column(Date)
    ngay_ket_thuc_goc: Mapped[date] = mapped_column(Date)
    gio_du_kien_goc: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    chi_phi_ke_hoach_goc: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    khoa_luc: Mapped[datetime | None] = mapped_column(DateTime)   # đã khóa baseline


class TepDinhKem(Base):
    __tablename__ = "tep_dinh_kem"
    ma_tep: Mapped[int] = mapped_column(primary_key=True)
    ma_cv: Mapped[int] = mapped_column(ForeignKey("task.ma_cv"), index=True)
    ten_tep: Mapped[str] = mapped_column(String(255))
    duong_dan: Mapped[str] = mapped_column(String(500))
    kich_thuoc: Mapped[int] = mapped_column(Integer, default=0)
    ma_nguoi_tai: Mapped[int] = mapped_column(ForeignKey("nguoi_dung.ma_nd"))
    thoi_diem_tai: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PhanCong(Base):
    """ERD: khóa ghép (MaCV, MaND). TASK 1–N PHÂN CÔNG; NHÂN VIÊN 1–N PHÂN CÔNG (Nhận việc)."""
    __tablename__ = "phan_cong"
    ma_cv: Mapped[int] = mapped_column(ForeignKey("task.ma_cv"), primary_key=True)
    ma_nd: Mapped[int] = mapped_column(ForeignKey("nhan_vien.ma_nd"), primary_key=True, index=True)
    trang_thai_phan_cong: Mapped[TrangThaiPhanCong] = mapped_column(E(TrangThaiPhanCong), default=TrangThaiPhanCong.ASSIGNED)
    ngay_giao: Mapped[date] = mapped_column(Date)
    gio_du_kien: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    ma_nguoi_giao: Mapped[int] = mapped_column(ForeignKey("nguoi_dung.ma_nd"))


class NhatKyGioLam(Base):
    __tablename__ = "nhat_ky_gio_lam"
    ma_nk: Mapped[int] = mapped_column(primary_key=True)
    ma_cv: Mapped[int] = mapped_column(ForeignKey("task.ma_cv"), index=True)
    ma_nd: Mapped[int] = mapped_column(ForeignKey("nhan_vien.ma_nd"), index=True)   # ERD: NHÂN VIÊN "Lập" NHẬT KÝ GIỜ LÀM
    bat_dau: Mapped[datetime] = mapped_column(DateTime)
    ket_thuc: Mapped[datetime] = mapped_column(DateTime)
    so_gio: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    noi_dung: Mapped[str | None] = mapped_column(Text)
    chi_phi_thuc_te: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    __table_args__ = (Index("ix_timesheet_user_time", "ma_nd", "bat_dau"),)


class XetDuyetCongViec(Base):
    __tablename__ = "xet_duyet_cong_viec"
    ma_duyet: Mapped[int] = mapped_column(primary_key=True)
    ma_cv: Mapped[int] = mapped_column(ForeignKey("task.ma_cv"), index=True)
    ma_nguoi_duyet: Mapped[int] = mapped_column(ForeignKey("nguoi_dung.ma_nd"))
    ket_qua: Mapped[KetQuaDuyet] = mapped_column(E(KetQuaDuyet))
    nhan_xet: Mapped[str | None] = mapped_column(Text)
    thoi_diem_duyet: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
