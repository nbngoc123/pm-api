from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, require_sys
from app.errors import forbidden, not_found
from app.models import NguoiDung, Quyen, VaiTro
from app.schemas.common import Msg, Page
from app.schemas.identity import (ResetPwdIn, RoleOut, UserCreate, UserLookup, UserOut, UserUpdate)
from app.security import hash_password
from app.services import users as svc
from app.services.access import role_perms, system_perms
from app.services.common import audit, paginate

router = APIRouter(tags=["Users & Roles"])


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, admin=Depends(require_sys("user.manage")), db: Session = Depends(get_db)):
    return svc.user_out(db, svc.create_user(db, admin, body))


@router.get("/users", response_model=Page[UserOut])
def list_users(q: str | None = None, trang_thai: str | None = None, vai_tro: str | None = None,
               page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
               admin=Depends(require_sys("user.manage")), db: Session = Depends(get_db)):
    st = select(NguoiDung).order_by(NguoiDung.ma_nd)
    if q:
        st = st.where(or_(NguoiDung.email.ilike(f"%{q}%"), NguoiDung.ho_ten.ilike(f"%{q}%")))
    if trang_thai:
        st = st.where(NguoiDung.trang_thai == trang_thai)
    if vai_tro:
        st = st.join(VaiTro, VaiTro.ma_vai_tro == NguoiDung.ma_vai_tro_he_thong).where(VaiTro.code == vai_tro)
    r = paginate(db, st, page, size)
    r["items"] = [svc.user_out(db, u) for u in r["items"]]
    return r


@router.get("/users/lookup", response_model=list[UserLookup])
def lookup_users(q: str = Query(..., min_length=2), user=Depends(current_user), db: Session = Depends(get_db)):
    """Tìm người dùng ACTIVE để thêm vào dự án (mọi user đăng nhập đều dùng được, chỉ trả thông tin tối thiểu)."""
    st = select(NguoiDung).where(NguoiDung.trang_thai == "ACTIVE",
                                 or_(NguoiDung.email.ilike(f"%{q}%"), NguoiDung.ho_ten.ilike(f"%{q}%"))).limit(20)
    return db.scalars(st).all()


@router.get("/users/{ma_nd}", response_model=UserOut)
def get_user(ma_nd: int, user=Depends(current_user), db: Session = Depends(get_db)):
    if ma_nd != user.ma_nd and "user.manage" not in system_perms(db, user):
        raise forbidden()
    u = db.get(NguoiDung, ma_nd)
    if not u:
        raise not_found("USER_NOT_FOUND", "Người dùng không tồn tại")
    return svc.user_out(db, u)


@router.patch("/users/{ma_nd}", response_model=UserOut)
def update_user(ma_nd: int, body: UserUpdate, admin=Depends(require_sys("user.manage")), db: Session = Depends(get_db)):
    u = db.get(NguoiDung, ma_nd)
    if not u:
        raise not_found("USER_NOT_FOUND", "Người dùng không tồn tại")
    return svc.user_out(db, svc.update_user(db, admin, u, body))


@router.post("/users/{ma_nd}/reset-password", response_model=Msg)
def reset_password(ma_nd: int, body: ResetPwdIn, admin=Depends(require_sys("user.manage")), db: Session = Depends(get_db)):
    u = db.get(NguoiDung, ma_nd)
    if not u:
        raise not_found("USER_NOT_FOUND", "Người dùng không tồn tại")
    u.mat_khau_hash = hash_password(body.new_password)
    u.token_version += 1
    u.so_lan_dang_nhap_sai, u.khoa_den = 0, None
    audit(db, admin.ma_nd, "PASSWORD_RESET", "nguoi_dung", u.ma_nd)
    return Msg()


@router.get("/roles", response_model=list[RoleOut])
def list_roles(user=Depends(current_user), db: Session = Depends(get_db)):
    return [RoleOut(ma_vai_tro=r.ma_vai_tro, code=r.code, ten_vai_tro=r.ten_vai_tro, pham_vi=r.pham_vi.value,
                    permissions=sorted(role_perms(db, r.ma_vai_tro))) for r in db.scalars(select(VaiTro))]
