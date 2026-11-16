from datetime import timedelta

import pytest

from app.services.common import today


def add(c, who, key, role="MEMBER"):
    return c.post(f"/projects/{c.pid}/members", who, {"ma_nguoi_dung": c.u[key], "vai_tro": role})


def test_add_member(proj):
    r = add(proj, "pm", "out")
    assert r.status_code == 201 and r.json()["vai_tro"] == "MEMBER" and r.json()["trang_thai"] == "ACTIVE"


def test_add_member_notifies(proj):
    add(proj, "pm", "out")
    assert proj.get("/me/notifications", "out").json()["items"][0]["loai"] == "ADDED_TO_PROJECT"


def test_add_member_as_team_lead(proj):
    assert add(proj, "pm", "out", "TEAM_LEAD").json()["vai_tro"] == "TEAM_LEAD"


def test_add_duplicate_member(proj):
    r = add(proj, "pm", "m1")
    assert r.status_code == 409 and r.json()["error"]["code"] == "ALREADY_MEMBER"


def test_add_member_pm_role_rejected(proj):
    r = add(proj, "pm", "out", "PM")
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_PROJECT_ROLE"


def test_add_member_unknown_user(proj):
    assert proj.post(f"/projects/{proj.pid}/members", "pm", {"ma_nguoi_dung": 99999}).status_code == 422


def test_add_inactive_user(proj):
    proj.patch(f"/users/{proj.u['out']}", "admin", {"trang_thai": "INACTIVE"})
    r = add(proj, "pm", "out")
    assert r.status_code == 422 and r.json()["error"]["code"] == "USER_INACTIVE"


def test_add_member_invalid_role_value(proj):
    assert proj.post(f"/projects/{proj.pid}/members", "pm", {"ma_nguoi_dung": proj.u["out"], "vai_tro": "BOSS"}).status_code == 422


@pytest.mark.parametrize("who,code", [("tl", 403), ("m1", 403), ("out", 404)])
def test_add_member_permission(proj, who, code):
    assert add(proj, who, "out").status_code == code


def test_remove_and_rejoin(proj):
    assert proj.delete(f"/projects/{proj.pid}/members/{proj.u['m2']}", "pm").status_code == 200
    assert proj.get(f"/projects/{proj.pid}/members", "pm").json().__len__() == 3
    assert add(proj, "pm", "m2", "TEAM_LEAD").json()["vai_tro"] == "TEAM_LEAD"
    assert len(proj.get(f"/projects/{proj.pid}/members", "pm").json()) == 4


def test_removed_member_loses_access(proj):
    proj.delete(f"/projects/{proj.pid}/members/{proj.u['m2']}", "pm")
    assert proj.get(f"/projects/{proj.pid}", "m2").status_code == 404


def test_list_members_include_left(proj):
    proj.delete(f"/projects/{proj.pid}/members/{proj.u['m2']}", "pm")
    r = proj.get(f"/projects/{proj.pid}/members?include_left=true", "pm").json()
    assert len(r) == 4 and any(x["trang_thai"] == "LEFT" and x["ngay_roi"] for x in r)


def test_cannot_remove_manager(proj):
    r = proj.delete(f"/projects/{proj.pid}/members/{proj.u['pm']}", "pm")
    assert r.status_code == 409 and r.json()["error"]["code"] == "CANNOT_REMOVE_MANAGER"


def test_remove_member_with_open_tasks(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1")
    r = proj.delete(f"/projects/{proj.pid}/members/{proj.u['m1']}", "pm")
    assert r.status_code == 409 and r.json()["error"]["code"] == "MEMBER_HAS_OPEN_TASKS"


def test_remove_member_after_unassign(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1")
    proj.delete(f"/tasks/{t['ma_cv']}/assignments/{proj.u['m1']}", "tl")
    assert proj.delete(f"/projects/{proj.pid}/members/{proj.u['m1']}", "pm").status_code == 200


def test_change_role(proj):
    r = proj.patch(f"/projects/{proj.pid}/members/{proj.u['m1']}", "pm", {"vai_tro": "TEAM_LEAD"})
    assert r.status_code == 200 and r.json()["vai_tro"] == "TEAM_LEAD"


def test_promoted_member_gets_permissions(proj):
    proj.patch(f"/projects/{proj.pid}/members/{proj.u['m1']}", "pm", {"vai_tro": "TEAM_LEAD"})
    assert proj.post(f"/projects/{proj.pid}/tasks", "m1", {"ten_cv": "Task mới"}).status_code == 201


def test_change_manager_role_blocked(proj):
    r = proj.patch(f"/projects/{proj.pid}/members/{proj.u['pm']}", "pm", {"vai_tro": "MEMBER"})
    assert r.status_code == 409


def test_change_role_to_pm_blocked(proj):
    assert proj.patch(f"/projects/{proj.pid}/members/{proj.u['m1']}", "pm", {"vai_tro": "PM"}).status_code == 409


def test_change_role_non_member(proj):
    assert proj.patch(f"/projects/{proj.pid}/members/{proj.u['out']}", "pm", {"vai_tro": "MEMBER"}).status_code == 422


def test_list_members_outsider(proj):
    assert proj.get(f"/projects/{proj.pid}/members", "out").status_code == 404


MS = {"ten_moc": "Milestone 1"}


def ms(c, who="pm", days=10, **kw):
    return c.post(f"/projects/{c.pid}/milestones", who, {**MS, "han_hoan_thanh": str(today() + timedelta(days=days)), **kw})


def test_create_milestone(proj):
    r = ms(proj)
    assert r.status_code == 201 and r.json()["trang_thai"] == "PENDING"


def test_milestone_duplicate_name(proj):
    ms(proj)
    assert ms(proj, ten_moc="milestone 1").status_code == 409


@pytest.mark.parametrize("days", [-31, 61, 1000])
def test_milestone_out_of_range(proj, days):
    r = ms(proj, days=days)
    assert r.status_code == 422 and r.json()["error"]["code"] == "MILESTONE_OUT_OF_RANGE"


@pytest.mark.parametrize("days", [-30, 60])
def test_milestone_boundaries_ok(proj, days):
    assert ms(proj, days=days).status_code == 201


@pytest.mark.parametrize("who,code", [("tl", 403), ("m1", 403), ("out", 404)])
def test_milestone_permission(proj, who, code):
    assert ms(proj, who).status_code == code


def test_list_milestones_sorted(proj):
    ms(proj, days=20, ten_moc="Mốc B"); ms(proj, days=5, ten_moc="Mốc A")
    assert [m["ten_moc"] for m in proj.get(f"/projects/{proj.pid}/milestones", "m1").json()] == ["Mốc A", "Mốc B"]


def test_update_milestone(proj):
    m = ms(proj).json()
    r = proj.patch(f"/projects/{proj.pid}/milestones/{m['ma_moc']}", "pm", {"ten_moc": "Đổi tên", "trang_thai": "ACHIEVED"})
    assert r.status_code == 200 and r.json()["trang_thai"] == "ACHIEVED"


def test_achieve_milestone_blocked_by_open_tasks(proj):
    m = ms(proj).json(); proj.task(ma_moc=m["ma_moc"])
    r = proj.patch(f"/projects/{proj.pid}/milestones/{m['ma_moc']}", "pm", {"trang_thai": "ACHIEVED"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "MILESTONE_HAS_OPEN_TASKS"


def test_achieve_milestone_when_tasks_done(proj):
    m = ms(proj).json(); proj.done_task(ma_moc=m["ma_moc"])
    assert proj.patch(f"/projects/{proj.pid}/milestones/{m['ma_moc']}", "pm", {"trang_thai": "ACHIEVED"}).status_code == 200


def test_update_milestone_date_out_of_range(proj):
    m = ms(proj).json()
    assert proj.patch(f"/projects/{proj.pid}/milestones/{m['ma_moc']}", "pm", {"han_hoan_thanh": "2000-01-01"}).status_code == 422


def test_delete_milestone(proj):
    m = ms(proj).json()
    assert proj.delete(f"/projects/{proj.pid}/milestones/{m['ma_moc']}", "pm").status_code == 200
    assert proj.get(f"/projects/{proj.pid}/milestones", "pm").json() == []


def test_delete_milestone_with_tasks(proj):
    m = ms(proj).json(); proj.task(ma_moc=m["ma_moc"])
    assert proj.delete(f"/projects/{proj.pid}/milestones/{m['ma_moc']}", "pm").status_code == 409


def test_milestone_wrong_project_404(proj):
    p2 = proj.project(ten_du_an="Dự án Beta")
    m = ms(proj).json()
    assert proj.patch(f"/projects/{p2['ma_du_an']}/milestones/{m['ma_moc']}", "pm", {"ten_moc": "Zzz"}).status_code == 404
