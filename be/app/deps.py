from datetime import timedelta

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import TrangThaiNguoiDung
from app.errors import forbidden, unauthorized
from app.models import NguoiDung
from app.security import decode_token, utcnow
from app.services.access import system_perms

bearer = HTTPBearer(auto_error=False)


def current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> NguoiDung:
    if not cred:
        raise unauthorized()
    d = decode_token(cred.credentials, "access")
    if not d:
        raise unauthorized("TOKEN_INVALID", "Token không hợp lệ hoặc đã hết hạn")
    u = db.get(NguoiDung, int(d["sub"]))
    if not u or u.token_version != d.get("ver"):
        raise unauthorized("TOKEN_REVOKED", "Token đã bị thu hồi")
    if u.trang_thai != TrangThaiNguoiDung.ACTIVE:
        raise forbidden("ACCOUNT_DISABLED", "Tài khoản bị khóa hoặc ngừng hoạt động")
    return u


def require_sys(perm: str):
    def dep(user: NguoiDung = Depends(current_user), db: Session = Depends(get_db)) -> NguoiDung:
        if perm not in system_perms(db, user):
            raise forbidden()
        return user
    return dep
