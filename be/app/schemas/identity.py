import re
from typing import Annotated

from pydantic import Field, StringConstraints, field_validator

from app.enums import LoaiNguoiDung, TrangThaiNguoiDung
from app.schemas.common import ORM

# Không dùng EmailStr: nó từ chối domain nội bộ như *.local
Email = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, max_length=255,
                                        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]
Pwd = Annotated[str, Field(min_length=8, max_length=128)]


def _check_pwd(v: str) -> str:
    if not (re.search(r"[A-Za-z]", v) and re.search(r"\d", v)):
        raise ValueError("Mật khẩu phải có cả chữ và số")
    return v


class LoginIn(ORM):
    email: Email
    password: str


class RefreshIn(ORM):
    refresh_token: str


class ChangePwdIn(ORM):
    old_password: str
    new_password: Pwd
    _v = field_validator("new_password")(_check_pwd)


class UserCreate(ORM):
    email: Email
    ho_ten: str = Field(min_length=2, max_length=150)
    password: Pwd
    vai_tro_he_thong: str = "EMPLOYEE"
    loai: LoaiNguoiDung | None = None
    ma_quan_ly: int | None = None
    don_gia_gio: float = Field(0, ge=0)
    _v = field_validator("password")(_check_pwd)


class UserUpdate(ORM):
    ho_ten: str | None = Field(None, min_length=2, max_length=150)
    vai_tro_he_thong: str | None = None
    trang_thai: TrangThaiNguoiDung | None = None
    ma_quan_ly: int | None = None
    don_gia_gio: float | None = Field(None, ge=0)


class ResetPwdIn(ORM):
    new_password: Pwd
    _v = field_validator("new_password")(_check_pwd)


class UserOut(ORM):
    ma_nd: int
    email: str
    ho_ten: str
    ma_vai_tro_he_thong: int
    vai_tro: str
    trang_thai: TrangThaiNguoiDung
    loai: LoaiNguoiDung
    ma_quan_ly: int | None = None
    don_gia_gio: float = 0


class UserLookup(ORM):
    ma_nd: int
    ho_ten: str
    email: str


class TokenOut(ORM):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class MeOut(UserOut):
    permissions: list[str]


class RoleOut(ORM):
    ma_vai_tro: int
    code: str
    ten_vai_tro: str
    pham_vi: str
    permissions: list[str]
