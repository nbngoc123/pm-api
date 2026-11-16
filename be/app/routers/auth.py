from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user
from app.errors import conflict, unauthorized
from app.models import NguoiDung
from app.schemas.common import Msg
from app.schemas.identity import ChangePwdIn, LoginIn, MeOut, RefreshIn, TokenOut
from app.security import decode_token, hash_password, verify_password
from app.services import users as svc
from app.services.access import system_perms
from app.services.common import audit

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    return svc.tokens(db, svc.login(db, body.email, body.password))


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    d = decode_token(body.refresh_token, "refresh")
    u = db.get(NguoiDung, int(d["sub"])) if d else None
    if not u or u.token_version != d.get("ver") or u.trang_thai.value != "ACTIVE":
        raise unauthorized("TOKEN_INVALID", "Refresh token không hợp lệ")
    return svc.tokens(db, u)


@router.get("/me", response_model=MeOut)
def me(user: NguoiDung = Depends(current_user), db: Session = Depends(get_db)):
    from app.models import ThanhVienDuAn  # noqa
    o = svc.user_out(db, user)
    return MeOut(**o.model_dump(), permissions=sorted(system_perms(db, user)))


@router.post("/change-password", response_model=Msg)
def change_password(body: ChangePwdIn, user: NguoiDung = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(body.old_password, user.mat_khau_hash):
        raise unauthorized("BAD_CREDENTIALS", "Mật khẩu cũ không đúng")
    if body.old_password == body.new_password:
        raise conflict("PASSWORD_UNCHANGED", "Mật khẩu mới phải khác mật khẩu cũ")
    user.mat_khau_hash = hash_password(body.new_password)
    user.token_version += 1
    audit(db, user.ma_nd, "PASSWORD_CHANGED", "nguoi_dung", user.ma_nd)
    return Msg()
