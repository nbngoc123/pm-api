from datetime import timedelta

import pytest

from app.services.common import today


def A(c, ma, who, user, **kw): return c.post(f"/tasks/{ma}/assignments", who, {"ma_nd": c.u[user], **kw})


@pytest.mark.parametrize("who", ["pm", "tl", "admin"])
def test_assign_allowed(proj, who):
    t = proj.task()
    r = A(proj, t["ma_cv"], who, "m1")
    assert r.status_code == 201 and r.json()["phan_cong"]["trang_thai_phan_cong"] == "ASSIGNED" and r.json()["warnings"] == []


@pytest.mark.parametrize("who,code", [("m1", 403), ("director", 403), ("out", 404)])
def test_assign_denied(proj, who, code):
    assert A(proj, proj.task()["ma_cv"], who, "m2").status_code == code


def test_assign_defaults_hours_from_task(proj):
    t = proj.task(gio_du_kien=12)
    assert A(proj, t["ma_cv"], "tl", "m1").json()["phan_cong"]["gio_du_kien"] == 12


def test_assign_custom_hours(proj):
    assert A(proj, proj.task()["ma_cv"], "tl", "m1", gio_du_kien=3.5).json()["phan_cong"]["gio_du_kien"] == 3.5


def test_assign_negative_hours(proj):
    assert A(proj, proj.task()["ma_cv"], "tl", "m1", gio_du_kien=-1).status_code == 422


def test_assign_non_member_rejected(proj):
    r = A(proj, proj.task()["ma_cv"], "tl", "out")
    assert r.status_code == 422 and r.json()["error"]["code"] == "NOT_PROJECT_MEMBER"


def test_assign_unknown_user(proj):
    r = proj.post(f"/tasks/{proj.task()['ma_cv']}/assignments", "tl", {"ma_nd": 99999})
    assert r.status_code == 422


def test_assign_duplicate(proj):
    t = proj.task(); A(proj, t["ma_cv"], "tl", "m1")
    r = A(proj, t["ma_cv"], "tl", "m1")
    assert r.status_code == 409 and r.json()["error"]["code"] == "ALREADY_ASSIGNED"


def test_assign_multiple_people(proj):
    t = proj.task(); A(proj, t["ma_cv"], "tl", "m1"); A(proj, t["ma_cv"], "tl", "m2")
    assert sorted(proj.get(f"/tasks/{t['ma_cv']}", "pm").json()["assignees"]) == sorted([proj.u["m1"], proj.u["m2"]])


@pytest.mark.parametrize("status", ["CANCELLED", "DONE"])
def test_assign_finished_task(proj, status):
    if status == "DONE":
        ma = proj.done_task()
    else:
        ma = proj.task()["ma_cv"]; proj.post(f"/tasks/{ma}/transition", "tl", {"trang_thai": "CANCELLED"})
    r = A(proj, ma, "tl", "m2")
    assert r.status_code == 409 and r.json()["error"]["code"] == "TASK_NOT_ASSIGNABLE"


def test_assign_warning_over_budget(proj):
    v = proj.get(f"/projects/{proj.pid}", "pm").json()["version"]
    proj.put(f"/projects/{proj.pid}/goals", "pm", {"version": v, "ngan_sach_gio": 10})
    t1 = proj.task(gio_du_kien=8); t2 = proj.task(gio_du_kien=8)
    assert A(proj, t1["ma_cv"], "tl", "m1").json()["warnings"] == []
    w = A(proj, t2["ma_cv"], "tl", "m2").json()["warnings"]
    assert w and w[0]["code"] == "OVER_HOURS_BUDGET" and w[0]["tong_gio_phan_cong"] == 16 and w[0]["ngan_sach_gio"] == 10


def test_assign_warning_deadline_passed(proj):
    t = proj.task(han_hoan_thanh=str(today() - timedelta(days=2)), ngay_bat_dau_du_kien=str(today() - timedelta(days=4)))
    assert A(proj, t["ma_cv"], "tl", "m1").json()["warnings"][0]["code"] == "DEADLINE_PASSED"


def test_assign_notifies_assignee(proj):
    A(proj, proj.task()["ma_cv"], "tl", "m1")
    assert proj.get("/me/notifications", "m1").json()["items"][0]["loai"] == "TASK_ASSIGNED"


def test_unassign(proj):
    t = proj.task(); A(proj, t["ma_cv"], "tl", "m1")
    assert proj.delete(f"/tasks/{t['ma_cv']}/assignments/{proj.u['m1']}", "tl").status_code == 200
    assert proj.get(f"/tasks/{t['ma_cv']}", "tl").json()["assignees"] == []


def test_unassign_not_assigned(proj):
    t = proj.task()
    assert proj.delete(f"/tasks/{t['ma_cv']}/assignments/{proj.u['m1']}", "tl").status_code == 422


def test_unassign_last_assignee_resets_in_progress(proj):
    t = proj.task(); A(proj, t["ma_cv"], "tl", "m1"); proj.go(t["ma_cv"], "IN_PROGRESS", "m1")
    proj.delete(f"/tasks/{t['ma_cv']}/assignments/{proj.u['m1']}", "tl")
    assert proj.get(f"/tasks/{t['ma_cv']}", "tl").json()["trang_thai"] == "TODO"


def test_unassign_forbidden_for_member(proj):
    t = proj.task(); A(proj, t["ma_cv"], "tl", "m1")
    assert proj.delete(f"/tasks/{t['ma_cv']}/assignments/{proj.u['m1']}", "m1").status_code == 403


def test_reassign_after_unassign(proj):
    t = proj.task(); A(proj, t["ma_cv"], "tl", "m1")
    proj.delete(f"/tasks/{t['ma_cv']}/assignments/{proj.u['m1']}", "tl")
    assert A(proj, t["ma_cv"], "tl", "m1").status_code == 201
    r = proj.get(f"/tasks/{t['ma_cv']}/assignments", "tl").json()
    assert len(r) == 1 and r[0]["trang_thai_phan_cong"] == "ASSIGNED"     # ERD: khóa ghép (MaCV, MaND) ⇒ 1 bản ghi/cặp


def to_review(c, user="m1"):
    t = c.task(); c.assign(t["ma_cv"], user); c.go(t["ma_cv"], "IN_PROGRESS", user); c.go(t["ma_cv"], "IN_REVIEW", user)
    return t["ma_cv"]


def R(c, ma, who, kq, nx=None): return c.post(f"/tasks/{ma}/review", who, {"ket_qua": kq, "nhan_xet": nx})


def test_review_approve(proj):
    ma = to_review(proj)
    r = R(proj, ma, "tl", "APPROVED", "Tốt")
    t = proj.get(f"/tasks/{ma}", "pm").json()
    assert r.status_code == 201 and t["trang_thai"] == "DONE" and t["ty_le_hoan_thanh"] == 100 and t["hoan_thanh_luc"]
    assert proj.get(f"/tasks/{ma}/assignments", "pm").json()[0]["trang_thai_phan_cong"] == "COMPLETED"


def test_review_by_pm(proj):
    assert R(proj, to_review(proj), "pm", "APPROVED").status_code == 201


def test_review_reject_requires_comment(proj):
    ma = to_review(proj)
    for nx in (None, "", "   "):
        r = R(proj, ma, "tl", "REJECTED", nx)
        assert r.status_code == 422 and r.json()["error"]["code"] == "COMMENT_REQUIRED"


def test_review_reject_returns_to_in_progress(proj):
    ma = to_review(proj)
    assert R(proj, ma, "tl", "REJECTED", "Làm lại").status_code == 201
    assert proj.get(f"/tasks/{ma}", "pm").json()["trang_thai"] == "IN_PROGRESS"


def test_review_notifies_assignee(proj):
    ma = to_review(proj); R(proj, ma, "tl", "REJECTED", "Làm lại")
    assert any(n["loai"] == "TASK_REVIEWED" for n in proj.get("/me/notifications", "m1").json()["items"])


def test_review_requested_notifies_leaders(proj):
    to_review(proj)
    assert any(n["loai"] == "REVIEW_REQUESTED" for n in proj.get("/me/notifications", "tl").json()["items"])


@pytest.mark.parametrize("who,code", [("m1", 403), ("m2", 403), ("director", 403), ("out", 404)])
def test_review_denied(proj, who, code):
    assert R(proj, to_review(proj), who, "APPROVED").status_code == code


def test_review_not_in_review(proj):
    t = proj.task()
    r = R(proj, t["ma_cv"], "tl", "APPROVED")
    assert r.status_code == 409 and r.json()["error"]["code"] == "TASK_NOT_IN_REVIEW"


def test_review_twice(proj):
    ma = to_review(proj); R(proj, ma, "tl", "APPROVED")
    assert R(proj, ma, "tl", "APPROVED").status_code == 409


def test_no_self_review_when_sole_assignee(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "tl", who="pm"); proj.go(t["ma_cv"], "IN_PROGRESS", "tl"); proj.go(t["ma_cv"], "IN_REVIEW", "tl")
    r = R(proj, t["ma_cv"], "tl", "APPROVED")
    assert r.status_code == 403 and r.json()["error"]["code"] == "SELF_REVIEW"
    assert R(proj, t["ma_cv"], "pm", "APPROVED").status_code == 201


def test_review_invalid_result(proj):
    assert R(proj, to_review(proj), "tl", "MAYBE").status_code == 422


def test_pending_review_list(proj):
    to_review(proj); proj.task()
    r = proj.get(f"/projects/{proj.pid}/reviews/pending", "tl").json()
    assert len(r) == 1 and r[0]["trang_thai"] == "IN_REVIEW"
    assert proj.get(f"/projects/{proj.pid}/reviews/pending", "m1").status_code == 403


def test_review_history(proj):
    ma = to_review(proj); R(proj, ma, "tl", "REJECTED", "Sửa")
    proj.go(ma, "IN_REVIEW", "m1"); R(proj, ma, "tl", "APPROVED")
    h = proj.get(f"/tasks/{ma}/reviews", "m1").json()
    assert [x["ket_qua"] for x in h] == ["REJECTED", "APPROVED"]


def test_over_budget_assignment_notifies_project_manager(proj):
    """DFD 2.3 → Quản lý dự án: "Cảnh báo vượt ngân sách giờ" (người giao là TL nhưng PM cũng phải nhận)."""
    v = proj.get(f"/projects/{proj.pid}", "pm").json()["version"]
    proj.put(f"/projects/{proj.pid}/goals", "pm", {"version": v, "ngan_sach_gio": 5})
    A(proj, proj.task(gio_du_kien=8)["ma_cv"], "tl", "m1")
    assert any(n["loai"] == "OVER_HOURS_BUDGET" for n in proj.get("/me/notifications", "pm").json()["items"])


def test_only_employee_can_be_assigned(proj):
    """ERD: NHÂN VIÊN –Nhận việc– PHÂN CÔNG; người loại QUẢN LÝ (PM) không nhận việc."""
    r = A(proj, proj.task()["ma_cv"], "tl", "pm")
    assert r.status_code == 422 and r.json()["error"]["code"] == "ASSIGNEE_MUST_BE_EMPLOYEE"
