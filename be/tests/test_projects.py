from datetime import timedelta

import pytest

from app.services.common import today


@pytest.mark.parametrize("who", ["director", "admin"])
def test_create_project_allowed(ctx, who):
    body = dict(ten_du_an="Dự án X", ngay_bat_dau=str(today()), ngay_ket_thuc_du_kien=str(today() + timedelta(days=30)),
                ngan_sach_gio=500, ma_quan_ly=ctx.u["pm"])
    r = ctx.post("/projects", who, body)
    assert r.status_code == 201 and r.json()["trang_thai"] == "PLANNING" and r.json()["version"] == 1


@pytest.mark.parametrize("who", ["pm", "tl", "m1", "out"])
def test_create_project_forbidden(ctx, who):
    body = dict(ten_du_an="Dự án X", ngay_bat_dau=str(today()), ngay_ket_thuc_du_kien=str(today()), ma_quan_ly=ctx.u["pm"])
    assert ctx.post("/projects", who, body).status_code == 403


def test_create_project_auto_adds_pm_member(ctx):
    p = ctx.project()
    m = ctx.get(f"/projects/{p['ma_du_an']}/members", "pm").json()
    assert len(m) == 1 and m[0]["vai_tro"] == "PM" and m[0]["ma_nguoi_dung"] == ctx.u["pm"]


@pytest.mark.parametrize("over", [
    {"ten_du_an": "ab"}, {"ten_du_an": ""}, {"ngan_sach_gio": -1}, {"ngan_sach_gio": 99999999999},
    {"ngay_ket_thuc_du_kien": "2000-01-01"},
])
def test_create_project_validation(ctx, over):
    body = dict(ten_du_an="Dự án X", ngay_bat_dau=str(today()), ngay_ket_thuc_du_kien=str(today() + timedelta(days=5)),
                ngan_sach_gio=10, ma_quan_ly=ctx.u["pm"])
    body.update(over)
    assert ctx.post("/projects", "director", body).status_code == 422


@pytest.mark.parametrize("mgr_key", ["m1", "tl"])
def test_manager_must_be_quan_ly(ctx, mgr_key):
    r = ctx.post("/projects", "director", dict(ten_du_an="Dự án X", ngay_bat_dau=str(today()),
                 ngay_ket_thuc_du_kien=str(today()), ma_quan_ly=ctx.u[mgr_key]))
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_MANAGER"


def test_manager_nonexistent(ctx):
    r = ctx.post("/projects", "director", dict(ten_du_an="Dự án X", ngay_bat_dau=str(today()),
                 ngay_ket_thuc_du_kien=str(today()), ma_quan_ly=99999))
    assert r.status_code == 422


def test_duplicate_project_name_case_insensitive(ctx):
    ctx.project()
    r = ctx.post("/projects", "director", dict(ten_du_an="DỰ ÁN ALPHA", ngay_bat_dau=str(today()),
                 ngay_ket_thuc_du_kien=str(today()), ma_quan_ly=ctx.u["pm"]))
    assert r.status_code == 409 and r.json()["error"]["code"] == "DUPLICATE_PROJECT_NAME"


def test_project_creation_notifies_manager(ctx):
    ctx.project()
    assert ctx.get("/me/notifications", "pm").json()["total"] == 1


@pytest.mark.parametrize("who,code", [("pm", 200), ("tl", 200), ("m1", 200), ("director", 200), ("admin", 200), ("out", 404), ("mgr2", 404)])
def test_get_project_visibility(proj, who, code):
    assert proj.get(f"/projects/{proj.pid}", who).status_code == code


def test_get_project_not_found(proj):
    assert proj.get("/projects/99999", "pm").status_code == 404


@pytest.mark.parametrize("who,n", [("pm", 1), ("m1", 1), ("out", 0), ("director", 1), ("admin", 1)])
def test_list_projects_scope(proj, who, n):
    assert proj.get("/projects", who).json()["total"] == n


def test_list_projects_filters(proj):
    assert proj.get("/projects?trang_thai=PLANNING", "pm").json()["total"] == 0
    assert proj.get("/projects?trang_thai=ACTIVE", "pm").json()["total"] == 1
    assert proj.get("/projects?q=alpha", "pm").json()["total"] == 1
    assert proj.get("/projects?q=zzz", "pm").json()["total"] == 0


def test_update_info(proj):
    v = proj.get(f"/projects/{proj.pid}", "pm").json()["version"]
    r = proj.patch(f"/projects/{proj.pid}", "pm", {"version": v, "ten_du_an": "Tên mới", "muc_tieu": "MT mới"})
    assert r.status_code == 200 and r.json()["ten_du_an"] == "Tên mới" and r.json()["version"] == v + 1


def test_update_info_version_conflict(proj):
    r = proj.patch(f"/projects/{proj.pid}", "pm", {"version": 999, "ten_du_an": "Tên mới"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "VERSION_CONFLICT"


def test_update_info_requires_version(proj):
    assert proj.patch(f"/projects/{proj.pid}", "pm", {"ten_du_an": "Tên mới"}).status_code == 422


@pytest.mark.parametrize("who", ["tl", "m1"])
def test_update_info_forbidden(proj, who):
    v = proj.get(f"/projects/{proj.pid}", "pm").json()["version"]
    assert proj.patch(f"/projects/{proj.pid}", who, {"version": v, "ten_du_an": "Tên mới"}).status_code == 403


def test_update_info_outsider_404(proj):
    assert proj.patch(f"/projects/{proj.pid}", "out", {"version": 1, "ten_du_an": "Tên mới"}).status_code == 404


def test_update_info_duplicate_name(proj):
    proj.post("/projects", "director", dict(ten_du_an="Dự án Beta", ngay_bat_dau=str(today()), ngay_ket_thuc_du_kien=str(today()), ma_quan_ly=proj.u["pm"]))
    v = proj.get(f"/projects/{proj.pid}", "pm").json()["version"]
    assert proj.patch(f"/projects/{proj.pid}", "pm", {"version": v, "ten_du_an": "dự án beta"}).status_code == 409


def test_update_info_short_name(proj):
    v = proj.get(f"/projects/{proj.pid}", "pm").json()["version"]
    assert proj.patch(f"/projects/{proj.pid}", "pm", {"version": v, "ten_du_an": "ab"}).status_code == 422


def test_goals_update(proj):
    v = proj.get(f"/projects/{proj.pid}", "pm").json()["version"]
    r = proj.put(f"/projects/{proj.pid}/goals", "pm", {"version": v, "muc_tieu": "Mục tiêu mới", "ngan_sach_gio": 2000,
                                                       "ngay_ket_thuc_du_kien": str(today() + timedelta(days=90))})
    assert r.status_code == 200 and r.json()["ngan_sach_gio"] == 2000 and r.json()["muc_tieu"] == "Mục tiêu mới"


def test_goals_end_before_start(proj):
    v = proj.get(f"/projects/{proj.pid}", "pm").json()["version"]
    r = proj.put(f"/projects/{proj.pid}/goals", "pm", {"version": v, "ngay_ket_thuc_du_kien": str(today() - timedelta(days=60))})
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_DATE_RANGE"


def test_goals_milestone_out_of_new_range(proj):
    proj.post(f"/projects/{proj.pid}/milestones", "pm", {"ten_moc": "M1", "han_hoan_thanh": str(today() + timedelta(days=50))})
    v = proj.get(f"/projects/{proj.pid}", "pm").json()["version"]
    r = proj.put(f"/projects/{proj.pid}/goals", "pm", {"version": v, "ngay_ket_thuc_du_kien": str(today() + timedelta(days=10))})
    assert r.status_code == 422 and r.json()["error"]["code"] == "MILESTONE_OUT_OF_RANGE"


def test_goals_version_conflict(proj):
    assert proj.put(f"/projects/{proj.pid}/goals", "pm", {"version": 50, "ngan_sach_gio": 5}).status_code == 409


def test_goals_negative_budget(proj):
    v = proj.get(f"/projects/{proj.pid}", "pm").json()["version"]
    assert proj.put(f"/projects/{proj.pid}/goals", "pm", {"version": v, "ngan_sach_gio": -5}).status_code == 422


def test_goals_forbidden_for_lead(proj):
    assert proj.put(f"/projects/{proj.pid}/goals", "tl", {"version": 1, "ngan_sach_gio": 5}).status_code == 403


@pytest.mark.parametrize("start,target,code", [
    ("PLANNING", "ACTIVE", 200), ("PLANNING", "COMPLETED", 409), ("PLANNING", "ON_HOLD", 409), ("PLANNING", "PLANNING", 409),
    ("ACTIVE", "ON_HOLD", 200), ("ACTIVE", "COMPLETED", 200), ("ACTIVE", "PLANNING", 409),
    ("ACTIVE", "CLOSED", 422), ("ACTIVE", "ACTIVE", 409),
])
def test_status_transitions(ctx, start, target, code):
    pid = ctx.setup_project(active=(start == "ACTIVE"))
    r = ctx.patch(f"/projects/{pid}/status", "pm", {"trang_thai": target})
    assert r.status_code == code


def test_status_on_hold_back_to_active(proj):
    proj.patch(f"/projects/{proj.pid}/status", "pm", {"trang_thai": "ON_HOLD"})
    assert proj.patch(f"/projects/{proj.pid}/status", "pm", {"trang_thai": "ACTIVE"}).status_code == 200


def test_status_complete_with_open_tasks(proj):
    proj.task()
    r = proj.patch(f"/projects/{proj.pid}/status", "pm", {"trang_thai": "COMPLETED"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "OPEN_TASKS_REMAIN"


def test_status_invalid_value(proj):
    assert proj.patch(f"/projects/{proj.pid}/status", "pm", {"trang_thai": "WHATEVER"}).status_code == 422


def test_status_forbidden_for_lead(proj):
    assert proj.patch(f"/projects/{proj.pid}/status", "tl", {"trang_thai": "ON_HOLD"}).status_code == 403


def test_close_by_director(proj):
    r = proj.post(f"/projects/{proj.pid}/close", "director", {})
    assert r.status_code == 200 and r.json()["trang_thai"] == "CLOSED" and r.json()["ngay_dong"] == str(today())


def test_close_by_admin_without_body(proj):
    assert proj.post(f"/projects/{proj.pid}/close", "admin").status_code == 200


@pytest.mark.parametrize("who", ["pm", "tl", "m1"])
def test_close_forbidden(proj, who):
    assert proj.post(f"/projects/{proj.pid}/close", who, {}).status_code == 403


def test_close_blocked_by_open_tasks(proj):
    proj.task()
    r = proj.post(f"/projects/{proj.pid}/close", "director", {})
    assert r.status_code == 409 and r.json()["error"]["code"] == "OPEN_TASKS_REMAIN"


def test_close_force_cancels_open_tasks_and_assignments(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1")
    assert proj.post(f"/projects/{proj.pid}/close", "director", {"force": True}).status_code == 200
    assert proj.get(f"/tasks/{t['ma_cv']}", "pm").json()["trang_thai"] == "CANCELLED"
    assert proj.get(f"/tasks/{t['ma_cv']}/assignments", "pm").json()[0]["trang_thai_phan_cong"] == "CANCELLED"


def test_close_twice(proj):
    proj.post(f"/projects/{proj.pid}/close", "director", {})
    assert proj.post(f"/projects/{proj.pid}/close", "director", {}).status_code == 409


def test_closed_project_is_read_only(proj):
    proj.post(f"/projects/{proj.pid}/close", "director", {})
    r = proj.post(f"/projects/{proj.pid}/tasks", "pm", {"ten_cv": "x"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "PROJECT_CLOSED"
    assert proj.post(f"/projects/{proj.pid}/milestones", "pm", {"ten_moc": "Mốc M", "han_hoan_thanh": str(today())}).status_code == 409
    assert proj.post(f"/projects/{proj.pid}/members", "pm", {"ma_nguoi_dung": proj.u["out"]}).status_code == 409


def test_closed_project_cannot_change_status(proj):
    proj.post(f"/projects/{proj.pid}/close", "director", {})
    assert proj.patch(f"/projects/{proj.pid}/status", "pm", {"trang_thai": "ACTIVE"}).status_code == 409


def test_overview_empty(proj):
    o = proj.get(f"/projects/{proj.pid}/overview", "m1").json()
    assert o["tong_task"] == 0 and o["ty_le_hoan_thanh"] == 0 and o["so_thanh_vien"] == 4 and o["gio_thuc_te"] == 0


def test_overview_counts(proj):
    proj.done_task(); proj.task(); proj.task()
    o = proj.get(f"/projects/{proj.pid}/overview", "pm").json()
    assert o["tong_task"] == 3 and o["task_hoan_thanh"] == 1 and o["ty_le_hoan_thanh"] == 33.3


def test_overview_overdue_and_hours(proj):
    t = proj.task(han_hoan_thanh=str(today() - timedelta(days=1)), ngay_bat_dau_du_kien=str(today() - timedelta(days=3)))
    proj.assign(t["ma_cv"], "m1"); proj.go(t["ma_cv"], "IN_PROGRESS", "m1"); proj.log(t["ma_cv"], hours=3)
    o = proj.get(f"/projects/{proj.pid}/overview", "pm").json()
    assert o["task_tre_han"] == 1 and o["gio_thuc_te"] == 3 and o["ty_le_su_dung_ngan_sach_gio"] == 0.3


def test_project_lifecycle_audited(proj):
    ev = {x["loai_su_kien"] for x in proj.get("/audit-logs?size=200", "admin").json()["items"]}
    assert {"PROJECT_CREATED", "MEMBER_ADDED", "PROJECT_STATUS_CHANGED"} <= ev


@pytest.mark.parametrize("who,role,has_update", [("pm", "PM", True), ("tl", "TEAM_LEAD", False), ("m1", "MEMBER", False)])
def test_my_permissions(proj, who, role, has_update):
    r = proj.get(f"/projects/{proj.pid}/my-permissions", who).json()
    assert r["vai_tro"] == role and ("project.update" in r["permissions"]) == has_update and "project.read" in r["permissions"]
