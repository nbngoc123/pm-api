from datetime import timedelta

import pytest

from app.security import utcnow


def started(c, user="m1"):
    t = c.task(); c.assign(t["ma_cv"], user); c.go(t["ma_cv"], "IN_PROGRESS", user)
    return t["ma_cv"]


def iso(dt): return dt.replace(microsecond=0).isoformat()


def test_log_time_ok_with_cost_and_totals(proj):
    ma = started(proj)
    r = proj.log(ma, hours=2)
    b = r.json()
    assert r.status_code == 201 and b["so_gio"] == 2 and b["chi_phi_thuc_te"] == 200000
    assert b["tong_gio_tich_luy_task"] == 2 and b["tong_gio_tich_luy_du_an"] == 2


def test_totals_accumulate(proj):
    ma = started(proj)
    proj.log(ma, start_h_ago=10, hours=2)
    r = proj.log(ma, start_h_ago=6, hours=1.5).json()
    assert r["tong_gio_tich_luy_task"] == 3.5 and r["tong_gio_tich_luy_du_an"] == 3.5


def test_project_total_spans_tasks(proj):
    a, b = started(proj), started(proj)
    proj.log(a, start_h_ago=10, hours=2)
    assert proj.log(b, start_h_ago=6, hours=1).json()["tong_gio_tich_luy_du_an"] == 3


def test_default_rate_when_user_rate_zero(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "tl", who="pm"); proj.go(t["ma_cv"], "IN_PROGRESS", "tl")
    assert proj.log(t["ma_cv"], "tl", hours=1).json()["chi_phi_thuc_te"] == 100000


def test_end_before_start(proj):
    s = utcnow() - timedelta(hours=3)
    r = proj.post(f"/tasks/{started(proj)}/timesheets", "m1", {"bat_dau": iso(s), "ket_thuc": iso(s - timedelta(hours=1))})
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_TIME_RANGE"


def test_future_time_rejected(proj):
    s = utcnow() + timedelta(hours=2)
    r = proj.post(f"/tasks/{started(proj)}/timesheets", "m1", {"bat_dau": iso(s), "ket_thuc": iso(s + timedelta(hours=1))})
    assert r.status_code == 422 and r.json()["error"]["code"] == "FUTURE_TIME"


def test_duration_over_24h(proj):
    s = utcnow() - timedelta(hours=40)
    r = proj.post(f"/tasks/{started(proj)}/timesheets", "m1", {"bat_dau": iso(s), "ket_thuc": iso(s + timedelta(hours=25))})
    assert r.status_code == 422 and r.json()["error"]["code"] == "DURATION_TOO_LONG"


def test_overlap_rejected(proj):
    ma = started(proj)
    proj.log(ma, start_h_ago=5, hours=2)
    r = proj.log(ma, start_h_ago=4, hours=2)
    assert r.status_code == 409 and r.json()["error"]["code"] == "TIMESHEET_OVERLAP"


def test_overlap_across_tasks_same_user(proj):
    a, b = started(proj), started(proj)
    proj.log(a, start_h_ago=5, hours=2)
    assert proj.log(b, start_h_ago=4, hours=2).status_code == 409


def test_overlap_different_users_ok(proj):
    a = started(proj, "m1"); b = started(proj, "m2")
    proj.log(a, "m1", start_h_ago=5, hours=2)
    assert proj.log(b, "m2", start_h_ago=5, hours=2).status_code == 201


def test_adjacent_slots_ok(proj):
    ma = started(proj)
    proj.log(ma, start_h_ago=6, hours=2)
    assert proj.log(ma, start_h_ago=4, hours=2).status_code == 201


def test_log_by_non_assignee(proj):
    ma = started(proj, "m1")
    r = proj.log(ma, "m2")
    assert r.status_code == 403 and r.json()["error"]["code"] == "NOT_ASSIGNEE"


def test_log_by_outsider(proj):
    assert proj.log(started(proj), "out").status_code == 404


@pytest.mark.parametrize("status", ["DONE", "CANCELLED"])
def test_log_on_finished_task(proj, status):
    if status == "DONE":
        ma = proj.done_task()
    else:
        ma = started(proj); proj.post(f"/tasks/{ma}/transition", "tl", {"trang_thai": "CANCELLED"})
        # huỷ làm mất phân công -> chặn do không còn là assignee
    r = proj.log(ma)
    assert r.status_code in (403, 409)


def test_log_missing_fields(proj):
    assert proj.post(f"/tasks/{started(proj)}/timesheets", "m1", {}).status_code == 422


def test_edit_own_entry(proj):
    e = proj.log(started(proj), hours=2).json()
    r = proj.patch(f"/timesheets/{e['ma_nk']}", "m1", {"ket_thuc": iso(utcnow() - timedelta(hours=2)), "noi_dung": "sửa"})
    assert r.status_code == 200 and r.json()["so_gio"] == 3 and r.json()["chi_phi_thuc_te"] == 300000


def test_edit_other_forbidden(proj):
    e = proj.log(started(proj)).json()
    assert proj.patch(f"/timesheets/{e['ma_nk']}", "m2", {"noi_dung": "x"}).status_code == 403


def test_edit_overlap_blocked(proj):
    ma = started(proj)
    proj.log(ma, start_h_ago=10, hours=2)
    e = proj.log(ma, start_h_ago=6, hours=2).json()
    assert proj.patch(f"/timesheets/{e['ma_nk']}", "m1", {"bat_dau": iso(utcnow() - timedelta(hours=9))}).status_code == 409


def test_edit_locked_after_window(proj):
    ma = started(proj)
    e = proj.log(ma, start_h_ago=24 * 10, hours=2).json()
    r = proj.patch(f"/timesheets/{e['ma_nk']}", "m1", {"noi_dung": "x"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "TIMESHEET_LOCKED"
    assert proj.delete(f"/timesheets/{e['ma_nk']}", "m1").status_code == 409


def test_delete_own_and_other(proj):
    e = proj.log(started(proj)).json()
    assert proj.delete(f"/timesheets/{e['ma_nk']}", "m2").status_code == 403
    assert proj.delete(f"/timesheets/{e['ma_nk']}", "m1").status_code == 200
    assert proj.get("/me/timesheets", "m1").json()["total"] == 0


def test_timesheet_not_found(proj):
    assert proj.patch("/timesheets/99999", "m1", {"noi_dung": "x"}).status_code == 404


def test_my_timesheets_and_summary(proj):
    ma = started(proj)
    proj.log(ma, start_h_ago=10, hours=2); proj.log(ma, start_h_ago=6, hours=1)
    assert proj.get("/me/timesheets", "m1").json()["total"] == 2
    s = proj.get("/me/timesheets/summary", "m1").json()
    assert s["tong_gio"] == 3 and s["tong_chi_phi"] == 300000 and s["theo_du_an"][0]["ma_du_an"] == proj.pid


def test_my_timesheets_date_filter(proj):
    ma = started(proj)
    proj.log(ma, start_h_ago=24 * 3, hours=1)
    far = str(utcnow().date() + timedelta(days=5))
    assert proj.get(f"/me/timesheets?tu_ngay={far}", "m1").json()["total"] == 0


def test_only_own_in_my_timesheets(proj):
    proj.log(started(proj, "m1"))
    assert proj.get("/me/timesheets", "m2").json()["total"] == 0


@pytest.mark.parametrize("who,code", [("pm", 200), ("tl", 403), ("m1", 403), ("out", 404)])
def test_project_timesheets_permission(proj, who, code):
    proj.log(started(proj))
    assert proj.get(f"/projects/{proj.pid}/timesheets", who).status_code == code


def test_task_timesheets_visibility(proj):
    ma = started(proj, "m1"); proj.assign(ma, "m2")
    proj.log(ma, "m1", start_h_ago=10, hours=1)
    assert len(proj.get(f"/tasks/{ma}/timesheets", "pm").json()) == 1
    assert proj.get(f"/tasks/{ma}/timesheets", "m2").json() == []


def test_timezone_offset_is_normalised_to_utc(proj):
    ma = started(proj)
    s = utcnow().replace(microsecond=0, tzinfo=None) - timedelta(hours=5)
    local_start = (s + timedelta(hours=7)).isoformat() + "+07:00"          # cùng thời điểm, biểu diễn theo giờ VN
    local_end = (s + timedelta(hours=9)).isoformat() + "+07:00"
    r = proj.post(f"/tasks/{ma}/timesheets", "m1", {"bat_dau": local_start, "ket_thuc": local_end})
    assert r.status_code == 201 and r.json()["so_gio"] == 2 and r.json()["bat_dau"].startswith(s.isoformat()[:16])
