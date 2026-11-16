import pytest
from sqlalchemy import select

from app.models import NguoiDung
from tests.conftest import PW

KEYS = ["director", "pm", "m1"]


@pytest.mark.parametrize("key", KEYS)
def test_login_success(ctx, key):
    r = ctx.post("/auth/login", json={"email": f"{key}@t.vn", "password": PW})
    assert r.status_code == 200
    b = r.json()
    assert b["access_token"] and b["refresh_token"] and b["user"]["ma_nd"] == ctx.u[key]


def test_login_admin_bootstrap(ctx):
    r = ctx.post("/auth/login", json={"email": "admin@company.local", "password": "Admin@12345"})
    assert r.status_code == 200 and r.json()["user"]["vai_tro"] == "ADMIN"


def test_login_email_case_insensitive(ctx):
    assert ctx.post("/auth/login", json={"email": "PM@T.VN", "password": PW}).status_code == 200


@pytest.mark.parametrize("body,code", [
    ({"email": "pm@t.vn", "password": "wrong"}, 401),
    ({"email": "nobody@t.vn", "password": PW}, 401),
    ({"email": "not-an-email", "password": PW}, 422),
    ({"email": "pm@t.vn"}, 422),
])
def test_login_failures(ctx, body, code):
    assert ctx.post("/auth/login", json=body).status_code == code


def test_error_format(ctx):
    e = ctx.post("/auth/login", json={"email": "pm@t.vn", "password": "x"}).json()["error"]
    assert e["code"] == "BAD_CREDENTIALS" and "message" in e


def test_lockout_after_failed_attempts(ctx):
    for _ in range(5):
        assert ctx.post("/auth/login", json={"email": "m1@t.vn", "password": "bad"}).status_code == 401
    r = ctx.post("/auth/login", json={"email": "m1@t.vn", "password": PW})
    assert r.status_code == 403 and r.json()["error"]["code"] == "ACCOUNT_LOCKED"


def test_failed_counter_resets_on_success(ctx):
    for _ in range(3):
        ctx.post("/auth/login", json={"email": "m1@t.vn", "password": "bad"})
    assert ctx.post("/auth/login", json={"email": "m1@t.vn", "password": PW}).status_code == 200
    with ctx.S() as db:
        assert db.scalar(select(NguoiDung.so_lan_dang_nhap_sai).where(NguoiDung.email == "m1@t.vn")) == 0


@pytest.mark.parametrize("path", ["/auth/me", "/projects", "/dashboard/me", "/me/kpi", "/me/notifications",
                                  "/violation-rules", "/users/lookup?q=ab"])
def test_requires_auth(ctx, path):
    r = ctx.get(path)
    assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.parametrize("tok", ["garbage", "a.b.c"])
def test_invalid_bearer(ctx, tok):
    r = ctx.c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401


def test_refresh_flow(ctx):
    t = ctx.post("/auth/login", json={"email": "pm@t.vn", "password": PW}).json()
    r = ctx.post("/auth/refresh", json={"refresh_token": t["refresh_token"]})
    assert r.status_code == 200 and r.json()["access_token"]


def test_access_token_not_accepted_as_refresh(ctx):
    t = ctx.post("/auth/login", json={"email": "pm@t.vn", "password": PW}).json()
    assert ctx.post("/auth/refresh", json={"refresh_token": t["access_token"]}).status_code == 401


def test_refresh_token_not_accepted_as_access(ctx):
    t = ctx.post("/auth/login", json={"email": "pm@t.vn", "password": PW}).json()
    r = ctx.c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t['refresh_token']}"})
    assert r.status_code == 401


def test_refresh_garbage(ctx):
    assert ctx.post("/auth/refresh", json={"refresh_token": "xxx"}).status_code == 401


def test_me_permissions_director(ctx):
    m = ctx.get("/auth/me", "director").json()
    assert "report.portfolio" in m["permissions"] and "user.manage" not in m["permissions"]


def test_me_permissions_employee_empty(ctx):
    assert ctx.get("/auth/me", "m1").json()["permissions"] == []


def test_me_permissions_admin_all(ctx):
    assert "user.manage" in ctx.get("/auth/me", "admin").json()["permissions"]


def test_change_password_flow(ctx):
    r = ctx.post("/auth/change-password", "m1", {"old_password": PW, "new_password": "NewPass123"})
    assert r.status_code == 200
    assert ctx.post("/auth/login", json={"email": "m1@t.vn", "password": PW}).status_code == 401
    assert ctx.post("/auth/login", json={"email": "m1@t.vn", "password": "NewPass123"}).status_code == 200


def test_change_password_revokes_old_tokens(ctx):
    ctx.post("/auth/change-password", "m1", {"old_password": PW, "new_password": "NewPass123"})
    r = ctx.get("/auth/me", "m1")
    assert r.status_code == 401 and r.json()["error"]["code"] == "TOKEN_REVOKED"


def test_change_password_wrong_old(ctx):
    assert ctx.post("/auth/change-password", "m1", {"old_password": "nope", "new_password": "NewPass123"}).status_code == 401


@pytest.mark.parametrize("weak", ["short1", "allletterss", "12345678", ""])
def test_change_password_weak(ctx, weak):
    assert ctx.post("/auth/change-password", "m1", {"old_password": PW, "new_password": weak}).status_code == 422


def test_change_password_same(ctx):
    assert ctx.post("/auth/change-password", "m1", {"old_password": PW, "new_password": PW}).status_code == 409


def test_disabled_user_token_rejected(ctx):
    ctx.patch(f"/users/{ctx.u['m1']}", "admin", {"trang_thai": "INACTIVE"})
    r = ctx.get("/auth/me", "m1")
    assert r.status_code in (401, 403)


def test_disabled_user_cannot_login(ctx):
    ctx.patch(f"/users/{ctx.u['m1']}", "admin", {"trang_thai": "LOCKED"})
    assert ctx.post("/auth/login", json={"email": "m1@t.vn", "password": PW}).status_code == 403


def test_login_writes_audit(ctx):
    ctx.post("/auth/login", json={"email": "pm@t.vn", "password": PW})
    r = ctx.get("/audit-logs?loai_su_kien=LOGIN", "admin").json()
    assert r["total"] >= 1


def test_password_hash_not_plaintext(ctx):
    with ctx.S() as db:
        h = db.scalar(select(NguoiDung.mat_khau_hash).where(NguoiDung.email == "pm@t.vn"))
    assert PW not in h and h.startswith("pbkdf2_sha256$")


def test_health(ctx):
    assert ctx.c.get("/health").json() == {"status": "ok"}
