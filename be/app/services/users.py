from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import LoaiNguoiDung, PhamVi, SysRole, TrangThaiNguoiDung
from app.errors import AppError, conflict, forbidden, invalid, unauthorized
from app.models import NguoiDung, NhanVien, QuanLy, VaiTro
from app.schemas.common import D
from app.schemas.identity import UserOut
from app.security import create_token, hash_password, utcnow, verify_password
from app.services.access import role_perms, system_role_code
from app.services.common import audit

MANAGER_ROLES = {SysRole.ADMIN.value, SysRole.DIRECTOR.value, SysRole.MANAGER.value}


def user_out(db: Session, u: NguoiDung) -> UserOut:
    nv = db.get(NhanVien, u.ma_nd)
    return UserOut(ma_nd=u.ma_nd, email=u.email, ho_ten=u.ho_ten, ma_vai_tro_he_thong=u.ma_vai_tro_he_thong,
                   vai_tro=system_role_code(db, u), trang_thai=u.trang_thai, loai=u.loai,
                   ma_quan_ly=nv.ma_quan_ly if nv else None, don_gia_gio=float(nv.don_gia_gio) if nv else 0)


def _sys_role(db, code: str) -> VaiTro:
    r = db.scalar(select(VaiTro).where(VaiTro.code == code, VaiTro.pham_vi == PhamVi.SYSTEM))
    if not r:
        raise invalid("INVALID_ROLE", f"Vai trò hệ thống '{code}' không tồn tại")
    return r


def _check_manager(db, ma_quan_ly):
    if ma_quan_ly is not None and not db.get(QuanLy, ma_quan_ly):
        raise invalid("INVALID_MANAGER", "ma_quan_ly phải là người dùng thuộc loại QUAN_LY")


def create_user(db: Session, actor: NguoiDung, d) -> NguoiDung:
    email = d.email.lower()
    if db.scalar(select(NguoiDung.ma_nd).where(NguoiDung.email == email)):
        raise conflict("EMAIL_EXISTS", "Email đã được sử dụng")
    role = _sys_role(db, d.vai_tro_he_thong)
    loai = d.loai or (LoaiNguoiDung.QUAN_LY if role.code in MANAGER_ROLES else LoaiNguoiDung.NHAN_VIEN)
    _check_manager(db, d.ma_quan_ly)
    u = NguoiDung(email=email, ho_ten=d.ho_ten, mat_khau_hash=hash_password(d.password),
                  ma_vai_tro_he_thong=role.ma_vai_tro, loai=loai)
    db.add(u); db.flush()
    if loai == LoaiNguoiDung.QUAN_LY:
        db.add(QuanLy(ma_nd=u.ma_nd))
    else:
        db.add(NhanVien(ma_nd=u.ma_nd, ma_quan_ly=d.ma_quan_ly, don_gia_gio=D(d.don_gia_gio)))
    audit(db, actor.ma_nd, "USER_CREATED", "nguoi_dung", u.ma_nd, email)
    db.flush()
    return u


def update_user(db: Session, actor: NguoiDung, u: NguoiDung, d) -> NguoiDung:
    data = d.model_dump(exclude_unset=True)
    if "ho_ten" in data and data["ho_ten"]:
        u.ho_ten = data["ho_ten"]
    if data.get("vai_tro_he_thong"):
        u.ma_vai_tro_he_thong = _sys_role(db, data["vai_tro_he_thong"]).ma_vai_tro
    if data.get("trang_thai"):
        if u.ma_nd == actor.ma_nd and data["trang_thai"] != TrangThaiNguoiDung.ACTIVE:
            raise conflict("CANNOT_DISABLE_SELF", "Không thể tự khóa tài khoản của mình")
        u.trang_thai = data["trang_thai"]
        if u.trang_thai == TrangThaiNguoiDung.ACTIVE:
            u.so_lan_dang_nhap_sai, u.khoa_den = 0, None
        else:
            u.token_version += 1
    nv = db.get(NhanVien, u.ma_nd)
    if "ma_quan_ly" in data:
        _check_manager(db, data["ma_quan_ly"])
        if nv:
            nv.ma_quan_ly = data["ma_quan_ly"]
    if data.get("don_gia_gio") is not None and nv:
        nv.don_gia_gio = D(data["don_gia_gio"])
    audit(db, actor.ma_nd, "USER_UPDATED", "nguoi_dung", u.ma_nd, ",".join(data))
    return u


def login(db: Session, email: str, password: str):
    u = db.scalar(select(NguoiDung).where(NguoiDung.email == email.lower()))
    if not u:
        raise unauthorized("BAD_CREDENTIALS", "Sai email hoặc mật khẩu")
    if u.khoa_den and u.khoa_den > utcnow():
        raise forbidden("ACCOUNT_LOCKED", "Tài khoản bị khóa tạm do nhập sai nhiều lần")
    if not verify_password(password, u.mat_khau_hash):
        u.so_lan_dang_nhap_sai += 1
        if u.so_lan_dang_nhap_sai >= settings.max_failed_logins:
            u.khoa_den = utcnow() + timedelta(minutes=settings.lock_minutes)
            u.so_lan_dang_nhap_sai = 0
            audit(db, u.ma_nd, "ACCOUNT_LOCKED", "nguoi_dung", u.ma_nd)
        db.commit()   # giữ bộ đếm dù trả lỗi
        raise unauthorized("BAD_CREDENTIALS", "Sai email hoặc mật khẩu")
    if u.trang_thai != TrangThaiNguoiDung.ACTIVE:
        raise forbidden("ACCOUNT_DISABLED", "Tài khoản bị khóa hoặc ngừng hoạt động")
    u.so_lan_dang_nhap_sai, u.khoa_den = 0, None
    audit(db, u.ma_nd, "LOGIN", "nguoi_dung", u.ma_nd)
    return u


def tokens(db: Session, u: NguoiDung) -> dict:
    return {"access_token": create_token(u.ma_nd, "access", u.token_version),
            "refresh_token": create_token(u.ma_nd, "refresh", u.token_version), "user": user_out(db, u)}
