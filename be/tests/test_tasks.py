from datetime import timedelta

import pytest

from app.services.common import today


def D(n): return str(today() + timedelta(days=n))


@pytest.mark.parametrize("prio", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
def test_create_task_priorities(proj, prio):
    r = proj.post(f"/projects/{proj.pid}/tasks", "pm", {"ten_cv": "Task", "uu_tien": prio})
    assert r.status_code == 201 and r.json()["uu_tien"] == prio and r.json()["trang_thai"] == "TODO" and r.json()["version"] == 1


@pytest.mark.parametrize("who", ["pm", "tl", "admin"])
def test_create_task_allowed(proj, who):
    assert proj.post(f"/projects/{proj.pid}/tasks", who, {"ten_cv": "Task"}).status_code == 201


@pytest.mark.parametrize("who,code", [("m1", 403), ("director", 403), ("out", 404)])
def test_create_task_denied(proj, who, code):
    assert proj.post(f"/projects/{proj.pid}/tasks", who, {"ten_cv": "Task"}).status_code == code


@pytest.mark.parametrize("over", [
    {"ten_cv": ""}, {"ten_cv": "x" * 201}, {"gio_du_kien": -1}, {"gio_du_kien": 10001}, {"uu_tien": "URGENT"},
    {"ngay_bat_dau_du_kien": D(5), "han_hoan_thanh": D(1)}, {"han_hoan_thanh": "not-a-date"},
])
def test_create_task_validation(proj, over):
    assert proj.post(f"/projects/{proj.pid}/tasks", "pm", {"ten_cv": "Task", **over}).status_code == 422


def test_create_task_creator_recorded(proj):
    assert proj.task(who="tl")["ma_nguoi_tao"] == proj.u["tl"]


def test_task_milestone_from_other_project(proj):
    p2 = proj.project(ten_du_an="Dự án Beta")
    m = proj.post(f"/projects/{p2['ma_du_an']}/milestones", "pm", {"ten_moc": "Mốc X", "han_hoan_thanh": D(5)}).json()
    r = proj.post(f"/projects/{proj.pid}/tasks", "pm", {"ten_cv": "T", "ma_moc": m["ma_moc"]})
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_MILESTONE"


def test_task_epic_from_other_project(proj):
    p2 = proj.project(ten_du_an="Dự án Beta")
    e = proj.post(f"/projects/{p2['ma_du_an']}/epics", "pm", {"ten_epic": "E"}).json()
    r = proj.post(f"/projects/{proj.pid}/tasks", "pm", {"ten_cv": "T", "ma_epic": e["ma_epic"]})
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_EPIC"


def test_task_with_epic(proj):
    e = proj.post(f"/projects/{proj.pid}/epics", "pm", {"ten_epic": "Epic 1"}).json()
    assert proj.task(ma_epic=e["ma_epic"])["ma_epic"] == e["ma_epic"]


def test_epic_delete_with_tasks_blocked(proj):
    e = proj.post(f"/projects/{proj.pid}/epics", "pm", {"ten_epic": "Epic 1"}).json()
    proj.task(ma_epic=e["ma_epic"])
    assert proj.delete(f"/projects/{proj.pid}/epics/{e['ma_epic']}", "pm").status_code == 409


def test_epic_delete_ok_and_list(proj):
    e = proj.post(f"/projects/{proj.pid}/epics", "pm", {"ten_epic": "Epic 1"}).json()
    assert len(proj.get(f"/projects/{proj.pid}/epics", "m1").json()) == 1
    assert proj.delete(f"/projects/{proj.pid}/epics/{e['ma_epic']}", "pm").status_code == 200


def test_get_task_ok_and_outsider(proj):
    t = proj.task()
    assert proj.get(f"/tasks/{t['ma_cv']}", "m1").status_code == 200
    assert proj.get(f"/tasks/{t['ma_cv']}", "out").status_code == 404
    assert proj.get("/tasks/99999", "pm").status_code == 404


def test_list_tasks_filters(proj):
    a = proj.task(ten_cv="Thiết kế", uu_tien="HIGH"); proj.task(ten_cv="Code", uu_tien="LOW")
    proj.assign(a["ma_cv"], "m1")
    g = lambda q: proj.get(f"/projects/{proj.pid}/tasks?{q}", "m2").json()["total"]
    assert g("") == 2 and g("uu_tien=HIGH") == 1 and g("q=thiết") == 1 and g(f"ma_nd={proj.u['m1']}") == 1
    assert g("trang_thai=DONE") == 0 and g("trang_thai=TODO") == 2


def test_list_tasks_overdue_filter(proj):
    proj.task(han_hoan_thanh=D(-2), ngay_bat_dau_du_kien=D(-5)); proj.task()
    assert proj.get(f"/projects/{proj.pid}/tasks?tre_han=true", "pm").json()["total"] == 1


def test_list_tasks_pagination(proj):
    for i in range(5): proj.task(ten_cv=f"T{i}")
    r = proj.get(f"/projects/{proj.pid}/tasks?size=2&page=3", "pm").json()
    assert r["total"] == 5 and len(r["items"]) == 1
    assert proj.get(f"/projects/{proj.pid}/tasks?size=101", "pm").status_code == 422


def test_update_task(proj):
    t = proj.task()
    r = proj.patch(f"/tasks/{t['ma_cv']}", "tl", {"version": 1, "ten_cv": "Mới", "uu_tien": "CRITICAL", "han_hoan_thanh": D(3)})
    assert r.status_code == 200 and r.json()["version"] == 2 and r.json()["uu_tien"] == "CRITICAL"


def test_update_task_version_conflict(proj):
    t = proj.task()
    proj.patch(f"/tasks/{t['ma_cv']}", "tl", {"version": 1, "ten_cv": "A1"})
    r = proj.patch(f"/tasks/{t['ma_cv']}", "pm", {"version": 1, "ten_cv": "A2"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "VERSION_CONFLICT"


def test_update_task_date_range(proj):
    t = proj.task(ngay_bat_dau_du_kien=D(1), han_hoan_thanh=D(5))
    assert proj.patch(f"/tasks/{t['ma_cv']}", "tl", {"version": 1, "han_hoan_thanh": D(0)}).status_code == 422


def test_update_task_member_forbidden(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1")
    assert proj.patch(f"/tasks/{t['ma_cv']}", "m1", {"version": 1, "ten_cv": "Hack"}).status_code == 403


def test_update_done_task_locked(proj):
    ma = proj.done_task()
    r = proj.patch(f"/tasks/{ma}", "tl", {"version": proj.get(f"/tasks/{ma}", "tl").json()["version"], "ten_cv": "Sửa"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "TASK_LOCKED"


def test_delete_todo_task(proj):
    t = proj.task()
    assert proj.delete(f"/tasks/{t['ma_cv']}", "pm").status_code == 200
    assert proj.get(f"/tasks/{t['ma_cv']}", "pm").status_code == 404


def test_delete_task_with_timesheet_blocked(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1"); proj.go(t["ma_cv"], "IN_PROGRESS", "m1"); proj.log(t["ma_cv"])
    proj.go(t["ma_cv"], "TODO", "m1")
    assert proj.delete(f"/tasks/{t['ma_cv']}", "pm").status_code == 409


def test_delete_in_progress_blocked(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1"); proj.go(t["ma_cv"], "IN_PROGRESS", "m1")
    assert proj.delete(f"/tasks/{t['ma_cv']}", "pm").status_code == 409


# ---- chuyển trạng thái ----
def tr(c, ma, who, st): return c.post(f"/tasks/{ma}/transition", who, {"trang_thai": st})


def test_member_starts_task(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1")
    r = tr(proj, t["ma_cv"], "m1", "IN_PROGRESS")
    assert r.status_code == 200 and r.json()["trang_thai"] == "IN_PROGRESS"


@pytest.mark.parametrize("target,code", [("IN_REVIEW", 409), ("DONE", 422), ("TODO", 409), ("CANCELLED", 403)])
def test_member_invalid_from_todo(proj, target, code):
    t = proj.task(); proj.assign(t["ma_cv"], "m1")
    assert tr(proj, t["ma_cv"], "m1", target).status_code == code


def test_non_assignee_cannot_transition(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1")
    r = tr(proj, t["ma_cv"], "m2", "IN_PROGRESS")
    assert r.status_code == 403 and r.json()["error"]["code"] == "NOT_ASSIGNEE"


def test_unassigned_cannot_start(proj):
    t = proj.task()
    r = tr(proj, t["ma_cv"], "pm", "IN_PROGRESS")
    assert r.status_code == 409 and r.json()["error"]["code"] == "TASK_NOT_ASSIGNED"


def test_in_progress_back_to_todo_and_to_review(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1"); proj.go(t["ma_cv"], "IN_PROGRESS", "m1")
    assert tr(proj, t["ma_cv"], "m1", "TODO").status_code == 200
    proj.go(t["ma_cv"], "IN_PROGRESS", "m1")
    assert tr(proj, t["ma_cv"], "m1", "IN_REVIEW").json()["trang_thai"] == "IN_REVIEW"


def test_review_state_cannot_go_back_via_transition(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1"); proj.go(t["ma_cv"], "IN_PROGRESS", "m1"); proj.go(t["ma_cv"], "IN_REVIEW", "m1")
    assert tr(proj, t["ma_cv"], "tl", "IN_PROGRESS").status_code == 409


def test_done_only_via_review(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1"); proj.go(t["ma_cv"], "IN_PROGRESS", "m1"); proj.go(t["ma_cv"], "IN_REVIEW", "m1")
    r = tr(proj, t["ma_cv"], "pm", "DONE")
    assert r.status_code == 422 and r.json()["error"]["code"] == "USE_REVIEW_ENDPOINT"


def test_lead_cancels_task_and_assignments(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1")
    assert tr(proj, t["ma_cv"], "tl", "CANCELLED").status_code == 200
    assert proj.get(f"/tasks/{t['ma_cv']}", "tl").json()["assignees"] == []


def test_reopen_cancelled_by_lead_only(proj):
    t = proj.task(); tr(proj, t["ma_cv"], "tl", "CANCELLED")
    assert tr(proj, t["ma_cv"], "m1", "TODO").status_code == 403
    assert tr(proj, t["ma_cv"], "tl", "TODO").status_code == 200


def test_reopen_done_task(proj):
    ma = proj.done_task()
    assert tr(proj, ma, "m1", "IN_PROGRESS").status_code == 403
    r = tr(proj, ma, "tl", "IN_PROGRESS")
    assert r.status_code == 200 and r.json()["ty_le_hoan_thanh"] == 99 and r.json()["hoan_thanh_luc"] is None


def test_transition_outsider(proj):
    t = proj.task()
    assert tr(proj, t["ma_cv"], "out", "CANCELLED").status_code == 404


def test_progress_update(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1"); proj.go(t["ma_cv"], "IN_PROGRESS", "m1")
    assert proj.post(f"/tasks/{t['ma_cv']}/progress", "m1", {"ty_le_hoan_thanh": 60}).json()["ty_le_hoan_thanh"] == 60


@pytest.mark.parametrize("pct", [-1, 101, "x"])
def test_progress_invalid(proj, pct):
    t = proj.task(); proj.assign(t["ma_cv"], "m1"); proj.go(t["ma_cv"], "IN_PROGRESS", "m1")
    assert proj.post(f"/tasks/{t['ma_cv']}/progress", "m1", {"ty_le_hoan_thanh": pct}).status_code == 422


def test_progress_requires_in_progress(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1")
    assert proj.post(f"/tasks/{t['ma_cv']}/progress", "m1", {"ty_le_hoan_thanh": 10}).status_code == 409


def test_progress_non_assignee(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1"); proj.go(t["ma_cv"], "IN_PROGRESS", "m1")
    assert proj.post(f"/tasks/{t['ma_cv']}/progress", "m2", {"ty_le_hoan_thanh": 10}).status_code == 403


# ---- 2.4 ưu tiên & thời hạn ----
@pytest.mark.parametrize("days,level", [(-3, "OVERDUE"), (0, "URGENT"), (2, "URGENT"), (3, "SOON"), (7, "SOON"), (8, "NORMAL"), (None, "NO_DEADLINE")])
def test_urgency_levels(proj, days, level):
    kw = {} if days is None else {"han_hoan_thanh": D(days), "ngay_bat_dau_du_kien": D(min(days, 0) - 1)}
    t = proj.task(**({"han_hoan_thanh": None} if days is None else kw))
    assert proj.get(f"/tasks/{t['ma_cv']}", "pm").json()["muc_do_khan"] == level


def test_done_task_has_no_urgency(proj):
    assert proj.get(f"/tasks/{proj.done_task()}", "pm").json()["muc_do_khan"] is None


def test_prioritized_order(proj):
    a = proj.task(ten_cv="normal-low", uu_tien="LOW", han_hoan_thanh=D(20))
    b = proj.task(ten_cv="overdue", uu_tien="LOW", han_hoan_thanh=D(-1), ngay_bat_dau_du_kien=D(-3))
    c = proj.task(ten_cv="urgent-crit", uu_tien="CRITICAL", han_hoan_thanh=D(1))
    d = proj.task(ten_cv="urgent-high", uu_tien="HIGH", han_hoan_thanh=D(1))
    r = [x["ten_cv"] for x in proj.get(f"/projects/{proj.pid}/tasks/prioritized", "m1").json()]
    assert r == ["overdue", "urgent-crit", "urgent-high", "normal-low"]


def test_prioritized_excludes_done(proj):
    proj.done_task(); proj.task()
    assert len(proj.get(f"/projects/{proj.pid}/tasks/prioritized", "pm").json()) == 1


# ---- subtask ----
def test_subtask_crud(proj):
    t = proj.task()
    s = proj.post(f"/tasks/{t['ma_cv']}/subtasks", "tl", {"ten_subtask": "Sub 1"}).json()
    assert s["trang_thai"] == "TODO"
    assert proj.patch(f"/tasks/{t['ma_cv']}/subtasks/{s['ma_subtask']}", "tl", {"trang_thai": "DONE"}).json()["trang_thai"] == "DONE"
    assert len(proj.get(f"/tasks/{t['ma_cv']}/subtasks", "m1").json()) == 1
    assert proj.delete(f"/tasks/{t['ma_cv']}/subtasks/{s['ma_subtask']}", "tl").status_code == 200


def test_subtask_assignee_can_update_status(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1")
    s = proj.post(f"/tasks/{t['ma_cv']}/subtasks", "tl", {"ten_subtask": "Sub 1"}).json()
    assert proj.patch(f"/tasks/{t['ma_cv']}/subtasks/{s['ma_subtask']}", "m1", {"trang_thai": "DONE"}).status_code == 200
    assert proj.patch(f"/tasks/{t['ma_cv']}/subtasks/{s['ma_subtask']}", "m2", {"trang_thai": "TODO"}).status_code == 403


# ---- tệp đính kèm ----
def up(c, ma, who, name="report.txt", data=b"hello"):
    return c.req("POST", f"/tasks/{ma}/attachments", who, files={"file": (name, data)})


def test_upload_attachment(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1")
    r = up(proj, t["ma_cv"], "m1")
    assert r.status_code == 201 and r.json()["kich_thuoc"] == 5 and r.json()["ten_tep"] == "report.txt"


def test_download_attachment(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1")
    a = up(proj, t["ma_cv"], "m1", data=b"noi dung").json()
    r = proj.get(f"/attachments/{a['ma_tep']}/download", "m2")
    assert r.status_code == 200 and r.content == b"noi dung"
    assert proj.get(f"/attachments/{a['ma_tep']}/download", "out").status_code == 404


@pytest.mark.parametrize("name", ["virus.exe", "script.sh", "noext", "a.php"])
def test_upload_rejects_extension(proj, name):
    t = proj.task(); proj.assign(t["ma_cv"], "m1")
    assert up(proj, t["ma_cv"], "m1", name).status_code == 422


def test_upload_empty_file(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1")
    assert up(proj, t["ma_cv"], "m1", data=b"").status_code == 422


def test_upload_path_traversal_sanitized(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1")
    r = up(proj, t["ma_cv"], "m1", "../../etc/passwd.txt")
    assert r.status_code == 201 and "/" not in r.json()["ten_tep"]


def test_upload_too_large(proj, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "max_upload_mb", 0)
    t = proj.task(); proj.assign(t["ma_cv"], "m1")
    assert up(proj, t["ma_cv"], "m1", data=b"x").status_code == 413


def test_upload_by_non_assignee_forbidden(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1")
    assert up(proj, t["ma_cv"], "m2").status_code == 403


def test_delete_attachment_rules(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1")
    a = up(proj, t["ma_cv"], "m1").json()
    assert proj.delete(f"/attachments/{a['ma_tep']}", "m2").status_code == 403
    assert proj.delete(f"/attachments/{a['ma_tep']}", "m1").status_code == 200
    assert proj.get(f"/tasks/{t['ma_cv']}/attachments", "m1").json() == []
