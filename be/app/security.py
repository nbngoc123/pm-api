import base64, hashlib, hmac, os
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings


def utcnow() -> datetime:
    """Toàn hệ thống lưu thời gian UTC naive."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _b(x: bytes) -> str: return base64.b64encode(x).decode()


def hash_password(p: str) -> str:
    salt = os.urandom(16)
    it = settings.password_iterations
    dk = hashlib.pbkdf2_hmac("sha256", p.encode(), salt, it)
    return f"pbkdf2_sha256${it}${_b(salt)}${_b(dk)}"


def verify_password(p: str, stored: str) -> bool:
    try:
        _, it, salt, dk = stored.split("$")
        new = hashlib.pbkdf2_hmac("sha256", p.encode(), base64.b64decode(salt), int(it))
        return hmac.compare_digest(new, base64.b64decode(dk))
    except Exception:
        return False


def create_token(sub: int, kind: str, ver: int) -> str:
    ttl = timedelta(minutes=settings.access_ttl_min) if kind == "access" else timedelta(days=settings.refresh_ttl_days)
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(sub), "typ": kind, "ver": ver, "iat": now, "exp": now + ttl},
                      settings.jwt_secret, algorithm=settings.jwt_alg)


def decode_token(token: str, kind: str) -> dict | None:
    try:
        d = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
    except jwt.PyJWTError:
        return None
    return d if d.get("typ") == kind else None
