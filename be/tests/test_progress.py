from datetime import timedelta

import pytest

from app.services.common import today


def D(n): return str(today() + timedelta(days=n))


def BL(c, ma, s, e, h=8, cost=1000, who="pm"):
    return c.put(f"/tasks/{ma}/baseline", who, {"ngay_bat_dau_goc": D(s), "ngay_ket_thuc_goc": D(e), "gio_du_kien_goc": h, "chi_phi_ke_hoach_goc": cost})


def evm(c, as_of=None, who="pm"):
    q = f"?as_of={D(as_of)}" if as_of is not None else ""
    return c.get(f"/projects/{c.pid}/progress/evm{q}", who).json()


def test_evm_empty_project(proj):
    e = evm(proj)
    assert e["bac"] == e["pv"] == e["ev"] == e["ac"] == 0 and e["spi"] is None and e["cpi"] is None and e["suc_khoe"] == "GREY"


@pytest.mark.parametrize("off,expected_pv", [(-1, 0), (0, 100), (4, 500), (9, 1000), (20, 1000)])
def test_pv_linear_between_dates(proj, off, expected_pv):
    t = proj.task(); BL(proj, t["ma_cv"], 0, 9, cost=1000)
    assert evm(proj, off)["pv"] == expected_pv


def test_bac_pv_ev_two_tasks(proj):
    a, b = proj.task(), proj.task()
    BL(proj, a["ma_cv"], -9, 0); BL(proj, b["ma_cv"], 0, 9)
    e = evm(proj)
    assert e["bac"] == 2000 and e["pv"] == 1100 and e["ev"] == 0 and e["spi"] == 0


def test_ev_counts_done_as_full_and_partial_progress(proj):
    a = proj.done_task(); b = proj.task(); proj.assign(b["ma_cv"], "m1"); proj.go(b["ma_cv"], "IN_PROGRESS", "m1")
    proj.post(f"/tasks/{b['ma_cv']}/progress", "m1", {"ty_le_hoan_thanh": 50})
    BL(proj, a, -9, 0); BL(proj, b["ma_cv"], -9, 0)
    e = evm(proj)
    assert e["ev"] == 1500 and e["pv"] == 2000 and e["spi"] == 0.75 and e["sv"] == -500


def test_ac_cpi_eac(proj):
    ma = proj.done_task(); BL(proj, ma, -9, 0, cost=1000)
    proj.log(ma, "m1", start_h_ago=3, hours=2) if False else None
    t = proj.task(); proj.assign(t["ma_cv"], "m1"); proj.go(t["ma_cv"], "IN_PROGRESS", "m1"); proj.log(t["ma_cv"], hours=2)
    BL(proj, t["ma_cv"], -9, 0, cost=1000)
    e = evm(proj)
    assert e["ac"] == 200000 and e["cv"] == 1000 - 200000 and e["cpi"] == 0.005 and e["suc_khoe"] == "RED"
    assert e["gio_thuc_te"] == 2 and e["eac"] == round(2000 / 0.005, 2)


def test_spi_cpi_health_green(proj):
    ma = proj.done_task(); BL(proj, ma, -9, 0, cost=200000)
    t = proj.task(); proj.assign(t["ma_cv"], "m1"); proj.go(t["ma_cv"], "IN_PROGRESS", "m1"); proj.log(t["ma_cv"], hours=2)
    e = evm(proj)
    assert e["spi"] == 1.0 and e["cpi"] == 1.0 and e["suc_khoe"] == "GREEN"


def test_cancelled_tasks_excluded_from_bac(proj):
    a, b = proj.task(), proj.task(); BL(proj, a["ma_cv"], 0, 5); BL(proj, b["ma_cv"], 0, 5)
    proj.post(f"/tasks/{b['ma_cv']}/transition", "tl", {"trang_thai": "CANCELLED"})
    assert evm(proj)["bac"] == 1000


def test_tasks_without_baseline_counted(proj):
    a = proj.task(); proj.task(); BL(proj, a["ma_cv"], 0, 5)
    e = evm(proj)
    assert e["so_task_co_baseline"] == 1 and e["so_task_chua_co_baseline"] == 1


@pytest.mark.parametrize("who,code", [("pm", 200), ("tl", 403), ("m1", 403), ("director", 403), ("out", 404)])
def test_evm_permissions(proj, who, code):
    assert proj.get(f"/projects/{proj.pid}/progress/evm", who).status_code == code


def test_baseline_invalid_dates(proj):
    t = proj.task()
    assert BL(proj, t["ma_cv"], 5, 1).status_code == 422
    assert proj.put(f"/tasks/{t['ma_cv']}/baseline", "pm", {"ngay_bat_dau_goc": D(0), "ngay_ket_thuc_goc": D(1), "gio_du_kien_goc": -1, "chi_phi_ke_hoach_goc": 1}).status_code == 422


@pytest.mark.parametrize("who,code", [("tl", 403), ("m1", 403), ("out", 404)])
def test_baseline_permissions(proj, who, code):
    assert BL(proj, proj.task()["ma_cv"], 0, 5, who=who).status_code == code


def test_baseline_editable_until_locked(proj):
    t = proj.task(); BL(proj, t["ma_cv"], 0, 5, cost=100)
    assert BL(proj, t["ma_cv"], 0, 6, cost=200).json()["chi_phi_ke_hoach_goc"] == 200
    proj.post(f"/projects/{proj.pid}/baseline/lock", "pm")
    r = BL(proj, t["ma_cv"], 0, 7)
    assert r.status_code == 409 and r.json()["error"]["code"] == "BASELINE_LOCKED"


def test_lock_creates_missing_baselines(proj):
    proj.task(gio_du_kien=10); proj.task(gio_du_kien=5)
    assert proj.post(f"/projects/{proj.pid}/baseline/lock", "pm").json()["so_task_duoc_khoa"] == 2
    b = proj.get(f"/projects/{proj.pid}/baseline", "pm").json()
    assert len(b) == 2 and all(x["khoa_luc"] for x in b)
    assert {x["gio_du_kien_goc"] for x in b} == {10, 5}
    assert proj.post(f"/projects/{proj.pid}/baseline/lock", "pm").json()["so_task_duoc_khoa"] == 0


def test_lock_forbidden_for_lead(proj):
    assert proj.post(f"/projects/{proj.pid}/baseline/lock", "tl").status_code == 403


def test_burndown_structure_and_endpoints(proj):
    proj.task(gio_du_kien=8); proj.task(gio_du_kien=12)
    b = proj.get(f"/projects/{proj.pid}/progress/burndown", "pm").json()
    assert b["don_vi"] == "gio" and b["tong_khoi_luong"] == 20 and len(b["diem"]) == 91
    assert b["diem"][0]["ly_tuong"] == 20 and b["diem"][-1]["ly_tuong"] == 0


def test_burndown_actual_drops_when_done(proj):
    proj.done_task(gio_du_kien=8); proj.task(gio_du_kien=12)
    b = proj.get(f"/projects/{proj.pid}/progress/burndown", "pm").json()
    today_pt = next(p for p in b["diem"] if p["ngay"] == str(today()))
    assert today_pt["thuc_te"] == 12 and b["diem"][-1]["thuc_te"] is None


def test_burndown_unit_falls_back_to_tasks(proj):
    proj.task(gio_du_kien=0); proj.task(gio_du_kien=0)
    b = proj.get(f"/projects/{proj.pid}/progress/burndown", "pm").json()
    assert b["don_vi"] == "task" and b["tong_khoi_luong"] == 2


def test_burndown_permission(proj):
    assert proj.get(f"/projects/{proj.pid}/progress/burndown", "m1").status_code == 403


def test_snapshot_idempotent_per_day(proj):
    t = proj.task(); BL(proj, t["ma_cv"], 0, 5)
    a = proj.post(f"/projects/{proj.pid}/progress/snapshots", "pm")
    proj.post(f"/projects/{proj.pid}/progress/snapshots", "pm")
    assert a.status_code == 201 and a.json()["pv"] > 0
    assert len(proj.get(f"/projects/{proj.pid}/progress/snapshots", "pm").json()) == 1


def test_snapshot_forbidden_for_lead(proj):
    assert proj.post(f"/projects/{proj.pid}/progress/snapshots", "tl").status_code == 403


# ---- 3.2 cảnh báo ----
def scan(c, who="admin", as_of=None):
    return c.post("/alerts/scan" + (f"?as_of={D(as_of)}" if as_of is not None else ""), who)


def test_deadline_reminder_and_dedupe(proj):
    t = proj.task(han_hoan_thanh=D(1)); proj.assign(t["ma_cv"], "m1")
    assert scan(proj).json()["nhac_deadline"] == 1
    assert scan(proj).json()["nhac_deadline"] == 0
    assert any(n["loai"] == "DEADLINE_REMINDER" for n in proj.get("/me/notifications", "m1").json()["items"])


def test_reminder_not_sent_outside_window(proj):
    t = proj.task(han_hoan_thanh=D(5)); proj.assign(t["ma_cv"], "m1")
    assert scan(proj).json()["nhac_deadline"] == 0


def test_delay_warning_to_leaders(proj):
    t = proj.task(han_hoan_thanh=D(-2), ngay_bat_dau_du_kien=D(-5)); proj.assign(t["ma_cv"], "m1")
    assert scan(proj).json()["canh_bao_tre_han"] == 1      # DFD 3.2: chỉ Trưởng nhóm
    assert any(n["loai"] == "DELAY_WARNING" for n in proj.get("/me/notifications", "tl").json()["items"])
    assert scan(proj).json()["canh_bao_tre_han"] == 0
    assert scan(proj, as_of=1).json()["canh_bao_tre_han"] == 1       # ngày mới -> cảnh báo mới


def test_scan_ignores_done_and_inactive_projects(proj):
    proj.done_task(han_hoan_thanh=D(-2), ngay_bat_dau_du_kien=D(-5))
    assert scan(proj).json() == {"nhac_deadline": 0, "canh_bao_tre_han": 0, "canh_bao_vuot_ngan_sach": 0}
    t = proj.task(han_hoan_thanh=D(1)); proj.assign(t["ma_cv"], "m1")
    proj.patch(f"/projects/{proj.pid}/status", "pm", {"trang_thai": "ON_HOLD"})
    assert scan(proj).json()["nhac_deadline"] == 0


def test_budget_exceeded_alert(proj):
    v = proj.get(f"/projects/{proj.pid}", "pm").json()["version"]
    proj.put(f"/projects/{proj.pid}/goals", "pm", {"version": v, "ngan_sach_gio": 1})
    t = proj.task(); proj.assign(t["ma_cv"], "m1"); proj.go(t["ma_cv"], "IN_PROGRESS", "m1"); proj.log(t["ma_cv"], hours=2)
    assert scan(proj).json()["canh_bao_vuot_ngan_sach"] == 1
    assert scan(proj).json()["canh_bao_vuot_ngan_sach"] == 0


@pytest.mark.parametrize("who", ["director", "pm", "tl", "m1"])
def test_scan_forbidden(proj, who):
    assert scan(proj, who).status_code == 403


def test_notifications_read_flow(proj):
    t = proj.task(); proj.assign(t["ma_cv"], "m1"); proj.assign(proj.task()["ma_cv"], "m1")
    n = proj.get("/me/notifications?chua_doc=true", "m1").json()
    assert n["total"] == 3        # 2 phân công + 1 "được thêm vào dự án"
    assert proj.post(f"/notifications/{n['items'][0]['ma_tb']}/read", "m1").status_code == 200
    assert proj.get("/me/notifications?chua_doc=true", "m1").json()["total"] == 2
    proj.post("/me/notifications/read-all", "m1")
    assert proj.get("/me/notifications?chua_doc=true", "m1").json()["total"] == 0


def test_cannot_read_others_notification(proj):
    proj.assign(proj.task()["ma_cv"], "m1")
    n = proj.get("/me/notifications", "m1").json()["items"][0]
    assert proj.post(f"/notifications/{n['ma_tb']}/read", "m2").status_code == 404


# ---- 3.3 audit ----
@pytest.mark.parametrize("who,code", [("admin", 200), ("director", 200), ("pm", 403), ("m1", 403)])
def test_audit_permission(proj, who, code):
    assert proj.get("/audit-logs", who).status_code == code


def test_audit_filters(proj):
    t = proj.task()
    r = proj.get(f"/audit-logs?doi_tuong=task&ma_doi_tuong={t['ma_cv']}", "admin").json()
    assert r["total"] == 1 and r["items"][0]["loai_su_kien"] == "TASK_CREATED"
    assert proj.get(f"/audit-logs?ma_nguoi_thuc_hien={proj.u['pm']}", "admin").json()["total"] >= 1


def test_delay_warning_falls_back_to_pm_when_no_team_lead(proj):
    proj.delete(f"/projects/{proj.pid}/members/{proj.u['tl']}", "pm")
    t = proj.task(han_hoan_thanh=D(-2), ngay_bat_dau_du_kien=D(-5)); proj.assign(t["ma_cv"], "m1", who="pm")
    assert scan(proj).json()["canh_bao_tre_han"] == 1
    assert any(n["loai"] == "DELAY_WARNING" for n in proj.get("/me/notifications", "pm").json()["items"])


def test_evm_calculation_parameter_hours_basis(proj):
    """DFD 3.1: "Tham số tính toán tiến độ" – QLDA chọn tính theo chi phí hay theo giờ."""
    t = proj.task(); BL(proj, t["ma_cv"], 0, 9, h=40, cost=1000)
    e = proj.get(f"/projects/{proj.pid}/progress/evm?co_so=gio&as_of={D(4)}", "pm").json()
    assert e["co_so"] == "gio" and e["bac"] == 40 and e["pv"] == 20
    assert proj.get(f"/projects/{proj.pid}/progress/evm?co_so=xxx", "pm").status_code == 422


def test_audit_log_is_linked_to_project(proj):
    """ERD: DỰ ÁN 1–N NHẬT KÝ HỆ THỐNG ("Phát sinh")."""
    t = proj.task()
    r = proj.get(f"/audit-logs?ma_da={proj.pid}&doi_tuong=task&ma_doi_tuong={t['ma_cv']}", "admin").json()
    assert r["total"] == 1 and r["items"][0]["ma_du_an"] == proj.pid
