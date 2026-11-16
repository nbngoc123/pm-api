import pytest

NEW = {"email": "new@t.vn", "ho_ten": "Nguyen Van A", "password": "Passw0rd1", "vai_tro_he_thong": "EMPLOYEE"}


def test_admin_creates_user(ctx):
    r = ctx.post("/users", "admin", NEW)
    assert r.status_code == 201 and r.json()["loai"] == "NHAN_VIEN" and r.json()["vai_tro"] == "EMPLOYEE"


@pytest.mark.parametrize("role,loai", [("DIRECTOR", "QUAN_LY"), ("MANAGER", "QUAN_LY"), ("EMPLOYEE", "NHAN_VIEN")])
def test_loai_derived_from_role(ctx, role, loai):
    r = ctx.post("/users", "admin", {**NEW, "vai_tro_he_thong": role})
    assert r.status_code == 201 and r.json()["loai"] == loai


@pytest.mark.parametrize("who", ["director", "pm", "tl", "m1", "out"])
def test_non_admin_cannot_create(ctx, who):
    assert ctx.post("/users", who, NEW).status_code == 403


def test_duplicate_email_case_insensitive(ctx):
    ctx.post("/users", "admin", NEW)
    r = ctx.post("/users", "admin", {**NEW, "email": "NEW@t.vn"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "EMAIL_EXISTS"


@pytest.mark.parametrize("patch", [{"email": "bad"}, {"password": "short1"}, {"password": "lettersonly"},
                                    {"password": "12345678"}, {"ho_ten": "A"}, {"don_gia_gio": -1}])
def test_create_validation(ctx, patch):
    assert ctx.post("/users", "admin", {**NEW, **patch}).status_code == 422


def test_unknown_role(ctx):
    r = ctx.post("/users", "admin", {**NEW, "vai_tro_he_thong": "PM"})   # PM là vai trò dự án, không phải hệ thống
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_ROLE"


def test_invalid_manager(ctx):
    r = ctx.post("/users", "admin", {**NEW, "ma_quan_ly": ctx.u["m1"]})
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_MANAGER"


def test_valid_manager(ctx):
    r = ctx.post("/users", "admin", {**NEW, "ma_quan_ly": ctx.u["pm"], "don_gia_gio": 50000})
    assert r.json()["ma_quan_ly"] == ctx.u["pm"] and r.json()["don_gia_gio"] == 50000


def test_list_users_paging(ctx):
    r = ctx.get("/users?size=3&page=1", "admin").json()
    assert len(r["items"]) == 3 and r["total"] >= 8


def test_list_users_filter_q(ctx):
    r = ctx.get("/users?q=m1@", "admin").json()
    assert r["total"] == 1


def test_list_users_filter_role(ctx):
    r = ctx.get("/users?vai_tro=MANAGER", "admin").json()
    assert r["total"] == 2


@pytest.mark.parametrize("who", ["m1"])
def test_list_users_forbidden(ctx, who):
    assert ctx.get("/users", who).status_code == 403


def test_page_size_limit(ctx):
    assert ctx.get("/users?size=1000", "admin").status_code == 422


def test_get_self_allowed(ctx):
    assert ctx.get(f"/users/{ctx.u['m1']}", "m1").status_code == 200


def test_get_other_forbidden(ctx):
    assert ctx.get(f"/users/{ctx.u['m2']}", "m1").status_code == 403


def test_patch_user_fields(ctx):
    r = ctx.patch(f"/users/{ctx.u['m1']}", "admin", {"ho_ten": "Tên Mới", "don_gia_gio": 123000, "ma_quan_ly": ctx.u["mgr2"]})
    b = r.json()
    assert r.status_code == 200 and b["ho_ten"] == "Tên Mới" and b["don_gia_gio"] == 123000 and b["ma_quan_ly"] == ctx.u["mgr2"]


def test_patch_user_role(ctx):
    assert ctx.patch(f"/users/{ctx.u['m1']}", "admin", {"vai_tro_he_thong": "DIRECTOR"}).json()["vai_tro"] == "DIRECTOR"


def test_patch_invalid_role(ctx):
    assert ctx.patch(f"/users/{ctx.u['m1']}", "admin", {"vai_tro_he_thong": "NOPE"}).status_code == 422


def test_cannot_disable_self(ctx):
    r = ctx.patch(f"/users/{ctx.u['admin']}", "admin", {"trang_thai": "LOCKED"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "CANNOT_DISABLE_SELF"


def test_reactivate_user(ctx):
    ctx.patch(f"/users/{ctx.u['m1']}", "admin", {"trang_thai": "LOCKED"})
    ctx.patch(f"/users/{ctx.u['m1']}", "admin", {"trang_thai": "ACTIVE"})
    assert ctx.post("/auth/login", json={"email": "m1@t.vn", "password": "Passw0rd!"}).status_code == 200


def test_reset_password(ctx):
    assert ctx.post(f"/users/{ctx.u['m1']}/reset-password", "admin", {"new_password": "Reset1234"}).status_code == 200
    assert ctx.post("/auth/login", json={"email": "m1@t.vn", "password": "Reset1234"}).status_code == 200


def test_reset_password_revokes_tokens(ctx):
    ctx.post(f"/users/{ctx.u['m1']}/reset-password", "admin", {"new_password": "Reset1234"})
    assert ctx.get("/auth/me", "m1").status_code == 401


def test_reset_password_forbidden(ctx):
    assert ctx.post(f"/users/{ctx.u['m2']}/reset-password", "pm", {"new_password": "Reset1234"}).status_code == 403


def test_lookup_min_length(ctx):
    assert ctx.get("/users/lookup?q=a", "pm").status_code == 422


def test_lookup_returns_minimal_fields(ctx):
    r = ctx.get("/users/lookup?q=m1", "pm").json()
    assert r and set(r[0]) == {"ma_nd", "ho_ten", "email"}


def test_lookup_only_active(ctx):
    ctx.patch(f"/users/{ctx.u['m1']}", "admin", {"trang_thai": "INACTIVE"})
    assert ctx.get("/users/lookup?q=m1", "pm").json() == []


def test_roles_listing(ctx):
    r = ctx.get("/roles", "m1").json()
    assert {x["code"] for x in r} == {"ADMIN", "DIRECTOR", "MANAGER", "EMPLOYEE", "PM", "TEAM_LEAD", "MEMBER"}


def test_roles_scope(ctx):
    r = {x["code"]: x for x in ctx.get("/roles", "m1").json()}
    assert r["PM"]["pham_vi"] == "PROJECT" and r["ADMIN"]["pham_vi"] == "SYSTEM"
    assert "kpi.approve" in r["PM"]["permissions"] and "kpi.approve" not in r["TEAM_LEAD"]["permissions"]


def test_user_creation_audited(ctx):
    ctx.post("/users", "admin", NEW)
    assert ctx.get("/audit-logs?loai_su_kien=USER_CREATED", "admin").json()["total"] == 1
