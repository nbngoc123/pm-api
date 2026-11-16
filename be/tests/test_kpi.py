from datetime import timedelta

import pytest

from app.services.common import today

TC, OT, HU, MAN = 1, 2, 3, 4        # tiêu chí seed: hoàn thành / đúng hạn / dùng giờ / thủ công


def _p(e): return f"{e['ma_ky']}/evaluations/{e['ma_nguoi_dung']}"      # khóa ghép ERD: (Mã kỳ, Mã người dùng)


def D(n): return str(today() + timedelta(days=n))


def period(c, who="pm", **kw):
    return c.post(f"/projects/{c.pid}/kpi/periods", who, {"ten_ky": "Kỳ 1", "tu_ngay": D(-10), "den_ngay": D(20), **kw})


CFG = [(TC, 40), (OT, 20), (HU, 20), (MAN, 20)]


def cfg(c, ky, items=CFG, who="pm", target=100):
    return c.put(f"/kpi/periods/{ky}/config", who, {"items": [{"ma_tieu_chi": i, "trong_so": w, "chi_tieu": target} for i, w in items]})


def open_ky(c):
    ky = period(c).json()["ma_ky"]
    assert cfg(c, ky).status_code == 200
    assert c.post(f"/kpi/periods/{ky}/open", "pm").status_code == 200
    return ky


def manual(c, ky, user, val, who="pm", crit=MAN):
    return c.put(f"/kpi/periods/{ky}/manual-inputs", who, {"items": [{"ma_nd": c.u[user], "ma_tieu_chi": crit, "gia_tri": val}]})


def evals(c, ky, who="pm"):
    return {e["ma_nguoi_dung"]: e for e in c.get(f"/kpi/periods/{ky}/evaluations", who).json()}


def scenario(c):
    """m1: 1 task xong đúng hạn + 1 task chưa xong (2h/16h) ; manual=80."""
    c.done_task(user="m1")
    t = c.task(); c.assign(t["ma_cv"], "m1"); c.go(t["ma_cv"], "IN_PROGRESS", "m1"); c.log(t["ma_cv"], hours=2)
    ky = open_ky(c)
    manual(c, ky, "m1", 80)
    return ky


# ---- tiêu chí ----
def test_criteria_seeded(proj):
    r = proj.get("/kpi/criteria", "m1").json()
    assert [c["nguon_du_lieu"] for c in r] == ["TASK_COMPLETION", "ON_TIME_RATE", "HOURS_UTILIZATION", "MANUAL"]


def test_criteria_create_and_duplicate(proj):
    ok = proj.post("/kpi/criteria", "pm", {"ten_tieu_chi": "Chất lượng code", "nguon_du_lieu": "MANUAL", "don_vi": "điểm"})
    assert ok.status_code == 201
    assert proj.post("/kpi/criteria", "pm", {"ten_tieu_chi": "CHẤT LƯỢNG CODE"}).status_code == 409


@pytest.mark.parametrize("who", ["tl", "m1", "director"])
def test_criteria_forbidden(proj, who):
    assert proj.post("/kpi/criteria", who, {"ten_tieu_chi": "Tiêu chí mới"}).status_code == 403


@pytest.mark.parametrize("body", [{"ten_tieu_chi": "a"}, {"ten_tieu_chi": "Hợp lệ", "nguon_du_lieu": "MAGIC"}])
def test_criteria_validation(proj, body):
    assert proj.post("/kpi/criteria", "pm", body).status_code == 422


def test_criteria_update_delete_and_in_use(proj):
    c = proj.post("/kpi/criteria", "pm", {"ten_tieu_chi": "Tạm thời"}).json()
    assert proj.patch(f"/kpi/criteria/{c['ma_tieu_chi']}", "pm", {"don_vi": "%"}).json()["don_vi"] == "%"
    assert proj.delete(f"/kpi/criteria/{c['ma_tieu_chi']}", "pm").status_code == 200
    ky = period(proj).json()["ma_ky"]; cfg(proj, ky)
    assert proj.delete(f"/kpi/criteria/{MAN}", "pm").status_code == 409
    assert proj.patch(f"/kpi/criteria/{MAN}", "pm", {"nguon_du_lieu": "TASK_COMPLETION"}).status_code == 409


# ---- kỳ ----
def test_period_create(proj):
    r = period(proj)
    assert r.status_code == 201 and r.json()["trang_thai"] == "DRAFT"


@pytest.mark.parametrize("tu,den,code", [(-10, 20, 409), (20, 25, 409), (-20, -10, 409), (21, 30, 201), (-30, -11, 201)])
def test_period_overlap_rules(proj, tu, den, code):
    period(proj)
    assert period(proj, ten_ky="Kỳ 2", tu_ngay=D(tu), den_ngay=D(den)).status_code == code


def test_period_invalid_dates(proj):
    assert period(proj, tu_ngay=D(5), den_ngay=D(1)).status_code == 422


@pytest.mark.parametrize("who,code", [("tl", 403), ("m1", 403), ("out", 404)])
def test_period_permission(proj, who, code):
    assert period(proj, who).status_code == code


def test_period_list_and_get(proj):
    ky = period(proj).json()["ma_ky"]
    assert len(proj.get(f"/projects/{proj.pid}/kpi/periods", "m1").json()) == 1
    assert proj.get(f"/kpi/periods/{ky}", "m1").status_code == 200 and proj.get(f"/kpi/periods/{ky}", "out").status_code == 404
    assert proj.get("/kpi/periods/99999", "pm").status_code == 404


# ---- cấu hình ----
@pytest.mark.parametrize("items", [[(TC, 40), (OT, 20), (HU, 20)], [(TC, 50), (OT, 50), (HU, 50)], [(TC, 100.5)]])
def test_config_weight_sum_must_be_100(proj, items):
    ky = period(proj).json()["ma_ky"]
    r = cfg(proj, ky, items)
    assert r.status_code == 422


def test_config_weight_error_code(proj):
    ky = period(proj).json()["ma_ky"]
    assert cfg(proj, ky, [(TC, 60)]).json()["error"]["code"] == "WEIGHT_SUM_INVALID"


def test_config_duplicate_and_unknown_criterion(proj):
    ky = period(proj).json()["ma_ky"]
    assert cfg(proj, ky, [(TC, 50), (TC, 50)]).json()["error"]["code"] == "DUPLICATE_CRITERION"
    assert cfg(proj, ky, [(TC, 50), (999, 50)]).json()["error"]["code"] == "CRITERION_NOT_FOUND"


@pytest.mark.parametrize("items,target", [([(TC, 0)], 100), ([(TC, 100)], 0), ([], 100)])
def test_config_field_validation(proj, items, target):
    ky = period(proj).json()["ma_ky"]
    assert cfg(proj, ky, items, target=target).status_code == 422


def test_config_ok_and_replace(proj):
    ky = period(proj).json()["ma_ky"]
    r = cfg(proj, ky).json()
    assert r["tong_trong_so"] == 100 and len(r["items"]) == 4
    assert len(cfg(proj, ky, [(TC, 60), (OT, 40)]).json()["items"]) == 2
    assert len(proj.get(f"/kpi/periods/{ky}/config", "m1").json()["items"]) == 2


def test_config_forbidden_for_lead(proj):
    ky = period(proj).json()["ma_ky"]
    assert cfg(proj, ky, who="tl").status_code == 403


def test_config_locked_after_open(proj):
    ky = open_ky(proj)
    r = cfg(proj, ky)
    assert r.status_code == 409 and r.json()["error"]["code"] == "PERIOD_NOT_EDITABLE"


# ---- mở kỳ ----
def test_open_without_config(proj):
    ky = period(proj).json()["ma_ky"]
    r = proj.post(f"/kpi/periods/{ky}/open", "pm")
    assert r.status_code == 409 and r.json()["error"]["code"] == "NO_CONFIG"


def test_open_creates_evaluations_for_active_members(proj):
    ky = period(proj).json()["ma_ky"]; cfg(proj, ky)
    assert proj.post(f"/kpi/periods/{ky}/open", "pm").json()["so_danh_gia_tao_moi"] == 4
    ev = evals(proj, ky)
    assert set(ev) == {proj.u[k] for k in ("pm", "tl", "m1", "m2")} and all(e["trang_thai"] == "DRAFT" and len(e["chi_tiet"]) == 4 for e in ev.values())
    assert proj.post(f"/kpi/periods/{ky}/open", "pm").status_code == 409


def test_sync_members(proj):
    ky = open_ky(proj)
    proj.post(f"/projects/{proj.pid}/members", "pm", {"ma_nguoi_dung": proj.u["out"]})
    assert proj.post(f"/kpi/periods/{ky}/sync-members", "pm").json()["so_danh_gia_tao_moi"] == 1
    assert proj.post(f"/kpi/periods/{ky}/sync-members", "pm").json()["so_danh_gia_tao_moi"] == 0


def test_sync_requires_open(proj):
    ky = period(proj).json()["ma_ky"]
    assert proj.post(f"/kpi/periods/{ky}/sync-members", "pm").status_code == 409


# ---- hiệu suất thô ----
def test_manual_input_rules(proj):
    ky = open_ky(proj)
    assert manual(proj, ky, "m1", 80).status_code == 200
    assert manual(proj, ky, "m1", 80, crit=TC).json()["error"]["code"] == "CRITERION_NOT_MANUAL"
    assert manual(proj, ky, "out", 80).json()["error"]["code"] == "USER_NOT_IN_PERIOD"
    assert manual(proj, ky, "m1", -1).status_code == 422
    assert manual(proj, ky, "m1", 80, crit=999).status_code == 422


def test_manual_input_permissions(proj):
    ky = open_ky(proj)
    assert manual(proj, ky, "m2", 70, who="m1").status_code == 403
    assert manual(proj, ky, "m2", 70, who="tl").status_code == 403
    assert manual(proj, ky, "m2", 70, who="mgr2").status_code in (200, 404)   # mgr2 không là thành viên -> 404 ở bước đọc kỳ


def test_manual_requires_open_period(proj):
    ky = period(proj).json()["ma_ky"]; cfg(proj, ky)
    assert manual(proj, ky, "m1", 80).status_code == 409


# ---- tính toán ----
def test_calculate_scores(proj):
    ky = scenario(proj)
    assert proj.post(f"/kpi/periods/{ky}/calculate", "pm").json() == {"da_tinh": 4, "bo_qua": 0}
    e = evals(proj, ky)[proj.u["m1"]]
    by = {x["ma_tieu_chi"]: x for x in e["chi_tiet"]}
    assert by[TC]["gia_tri_tu_dong"] == 50 and by[OT]["gia_tri_tu_dong"] == 100 and by[HU]["gia_tri_tu_dong"] == 12.5
    assert e["trang_thai"] == "PROVISIONAL" and e["diem_goc"] == 58.5 and e["diem_tru"] == 0 and e["diem_tong"] == 58.5


def test_calculate_renormalizes_missing_data(proj):
    ky = open_ky(proj); manual(proj, ky, "m2", 80)       # m2 không có task nào -> chỉ tính tiêu chí thủ công
    proj.post(f"/kpi/periods/{ky}/calculate", "pm")
    e = evals(proj, ky)[proj.u["m2"]]
    assert e["diem_goc"] == 80 and e["chi_tiet"][0]["gia_tri_tu_dong"] is None


def test_calculate_no_data_gives_zero(proj):
    ky = open_ky(proj); proj.post(f"/kpi/periods/{ky}/calculate", "pm")
    assert evals(proj, ky)[proj.u["m1"]]["diem_tong"] == 0


def test_achievement_capped_at_100(proj):
    ky = open_ky(proj); manual(proj, ky, "m1", 150)
    proj.post(f"/kpi/periods/{ky}/calculate", "pm")
    e = evals(proj, ky)[proj.u["m1"]]
    assert e["diem_goc"] == 100 and e["chi_tiet"][3]["ty_le_dat"] == 100


def test_task_outside_period_ignored(proj):
    t = proj.task(han_hoan_thanh=D(25), ngay_bat_dau_du_kien=D(24)); proj.assign(t["ma_cv"], "m1")
    ky = open_ky(proj); proj.post(f"/kpi/periods/{ky}/calculate", "pm")
    assert evals(proj, ky)[proj.u["m1"]]["chi_tiet"][0]["gia_tri_tu_dong"] is None


def test_late_task_lowers_on_time_rate(proj):
    t = proj.task(han_hoan_thanh=D(-1), ngay_bat_dau_du_kien=D(-2)); proj.assign(t["ma_cv"], "m1")
    proj.go(t["ma_cv"], "IN_PROGRESS", "m1"); proj.go(t["ma_cv"], "IN_REVIEW", "m1")
    proj.post(f"/tasks/{t['ma_cv']}/review", "tl", {"ket_qua": "APPROVED"})
    ky = open_ky(proj); proj.post(f"/kpi/periods/{ky}/calculate", "pm")
    by = {x["ma_tieu_chi"]: x for x in evals(proj, ky)[proj.u["m1"]]["chi_tiet"]}
    assert by[TC]["gia_tri_tu_dong"] == 100 and by[OT]["gia_tri_tu_dong"] == 0


def test_penalty_from_confirmed_violation(proj):
    ky = scenario(proj)
    v = proj.post("/violations", "tl", {"ma_cv": proj.task()["ma_cv"], "ma_nd": proj.u["m1"], "ma_qd": 1, "noi_dung": "Trễ deadline"}).json()
    proj.post(f"/violations/{v['ma_vp']}/notify", "tl")
    proj.post(f"/violations/{v['ma_vp']}/explanations", "m1", {"noi_dung": "Không có lý do"})
    c = proj.post(f"/violations/{v['ma_vp']}/conclude", "pm", {"ket_luan": "CONFIRMED", "ghi_chu": "Xử phạt"}).json()
    assert c["ma_ky_ap_dung"] == ky                          # tự gắn vào kỳ đang mở
    proj.post(f"/kpi/periods/{ky}/calculate", "pm")
    e = evals(proj, ky)[proj.u["m1"]]
    assert e["diem_tru"] == 5 and e["diem_tong"] == 53.5 and e["diem_goc"] == 58.5


def test_dismissed_violation_has_no_penalty(proj):
    ky = scenario(proj)
    v = proj.post("/violations", "tl", {"ma_cv": proj.task()["ma_cv"], "ma_nd": proj.u["m1"], "ma_qd": 1, "noi_dung": "Trễ deadline"}).json()
    proj.post(f"/violations/{v['ma_vp']}/conclude", "pm", {"ket_luan": "DISMISSED", "ghi_chu": "Bác bỏ"})
    proj.post(f"/kpi/periods/{ky}/calculate", "pm")
    assert evals(proj, ky)[proj.u["m1"]]["diem_tru"] == 0


def test_score_never_negative(proj):
    ky = open_ky(proj); manual(proj, ky, "m1", 10)
    for i in range(3):
        qd = proj.post("/violation-rules", "pm", {"ten_quy_dinh": f"Phạt nặng {i}", "diem_tru": 50, "tu_ngay": D(-1)}).json()["ma_qd"]
        v = proj.post("/violations", "tl", {"ma_cv": proj.task()["ma_cv"], "ma_nd": proj.u["m1"], "ma_qd": qd, "noi_dung": "Vi phạm nặng"}).json()
        proj.post(f"/violations/{v['ma_vp']}/conclude", "pm", {"ket_luan": "DISMISSED", "ghi_chu": "tạm"}) if False else None
        proj.post(f"/violations/{v['ma_vp']}/notify", "tl")
        proj.post(f"/violations/{v['ma_vp']}/explanations", "m1", {"noi_dung": "Giải trình nè"})
        proj.post(f"/violations/{v['ma_vp']}/conclude", "pm", {"ket_luan": "CONFIRMED", "ghi_chu": "Phạt"})
    proj.post(f"/kpi/periods/{ky}/calculate", "pm")
    assert evals(proj, ky)[proj.u["m1"]]["diem_tong"] == 0


@pytest.mark.parametrize("who", ["tl", "m1"])
def test_calculate_forbidden(proj, who):
    ky = open_ky(proj)
    assert proj.post(f"/kpi/periods/{ky}/calculate", who).status_code == 403


def test_calculate_requires_open(proj):
    ky = period(proj).json()["ma_ky"]
    assert proj.post(f"/kpi/periods/{ky}/calculate", "pm").status_code == 409


# ---- xác nhận & phê duyệt ----
def provisional(c):
    ky = scenario(c); c.post(f"/kpi/periods/{ky}/calculate", "pm")
    return ky, evals(c, ky)


def test_confirm_flow_copies_values(proj):
    ky, ev = provisional(proj)
    e = ev[proj.u["m1"]]
    r = proj.post(f"/kpi/periods/{_p(e)}/confirm", "m1").json()
    assert r["trang_thai"] == "MEMBER_CONFIRMED" and r["ngay_xac_nhan"] == str(today())
    assert [x["gia_tri_xac_nhan"] for x in r["chi_tiet"]] == [50, 100, 12.5, 80]


def test_confirm_before_calculation(proj):
    ky = open_ky(proj)
    e = evals(proj, ky)[proj.u["m1"]]
    r = proj.post(f"/kpi/periods/{_p(e)}/confirm", "m1")
    assert r.status_code == 409 and r.json()["error"]["code"] == "INVALID_EVALUATION_STATE"


def test_confirm_only_by_owner(proj):
    ky, ev = provisional(proj)
    e = ev[proj.u["m1"]]
    assert proj.post(f"/kpi/periods/{_p(e)}/confirm", "pm").status_code == 403
    assert proj.post(f"/kpi/periods/{_p(e)}/confirm", "m2").status_code == 404


def test_approve_requires_member_confirmation(proj):
    ky, ev = provisional(proj)
    assert proj.post(f"/kpi/periods/{_p(ev[proj.u['m1']])}/approve", "pm").status_code == 409


def test_approve_flow(proj):
    ky, ev = provisional(proj); dg = _p(ev[proj.u['m1']])
    proj.post(f"/kpi/periods/{dg}/confirm", "m1")
    r = proj.post(f"/kpi/periods/{dg}/approve", "pm", {"nhan_xet": "Tốt"}).json()
    assert r["trang_thai"] == "APPROVED" and r["ma_nguoi_duyet"] == proj.u["pm"] and r["ngay_duyet"] == str(today())
    assert any(n["loai"] == "KPI_DECISION" for n in proj.get("/me/notifications", "m1").json()["items"])


def test_approve_without_body(proj):
    ky, ev = provisional(proj); dg = _p(ev[proj.u['m1']])
    proj.post(f"/kpi/periods/{dg}/confirm", "m1")
    assert proj.post(f"/kpi/periods/{dg}/approve", "pm").status_code == 200


def test_no_self_approval(proj):
    ky, ev = provisional(proj); dg = _p(ev[proj.u['pm']])
    proj.post(f"/kpi/periods/{dg}/confirm", "pm")
    r = proj.post(f"/kpi/periods/{dg}/approve", "pm")
    assert r.status_code == 403 and r.json()["error"]["code"] == "SELF_APPROVAL"
    assert proj.post(f"/kpi/periods/{dg}/approve", "admin").status_code == 200


def test_lead_cannot_approve(proj):
    ky, ev = provisional(proj); dg = _p(ev[proj.u['m1']])
    proj.post(f"/kpi/periods/{dg}/confirm", "m1")
    assert proj.post(f"/kpi/periods/{dg}/approve", "tl").status_code == 404      # TL không thuộc luồng KPI của người khác


def test_direct_manager_can_approve_outside_project(proj):
    ky, ev = provisional(proj); dg = _p(ev[proj.u['m2']])
    proj.post(f"/kpi/periods/{dg}/confirm", "m2")
    assert proj.post(f"/kpi/periods/{dg}/approve", "mgr2").status_code == 200


def test_reject_requires_comment_then_recalculate(proj):
    ky, ev = provisional(proj); dg = _p(ev[proj.u['m1']])
    proj.post(f"/kpi/periods/{dg}/confirm", "m1")
    assert proj.post(f"/kpi/periods/{dg}/reject", "pm", {}).status_code == 422
    assert proj.post(f"/kpi/periods/{dg}/reject", "pm", {"nhan_xet": "Cần xem lại"}).json()["trang_thai"] == "REJECTED"
    assert proj.post(f"/kpi/periods/{ky}/calculate", "pm").json()["da_tinh"] >= 1
    assert proj.get(f"/kpi/periods/{dg}", "m1").json()["trang_thai"] == "PROVISIONAL"


def test_recalculate_skips_confirmed_and_approved(proj):
    ky, ev = provisional(proj)
    a, b = _p(ev[proj.u['m1']]), _p(ev[proj.u['m2']])
    proj.post(f"/kpi/periods/{a}/confirm", "m1"); proj.post(f"/kpi/periods/{b}/confirm", "m2")
    proj.post(f"/kpi/periods/{b}/approve", "pm")
    assert proj.post(f"/kpi/periods/{ky}/calculate", "pm").json() == {"da_tinh": 2, "bo_qua": 2}


# ---- đóng kỳ ----
def approve_all(c, ky):
    ev = evals(c, ky)
    for k, e in ev.items():
        who = next(n for n in ("pm", "tl", "m1", "m2") if c.u[n] == k)
        c.post(f"/kpi/periods/{_p(e)}/confirm", who)
        approver = "admin" if who == "pm" else "pm"
        assert c.post(f"/kpi/periods/{_p(e)}/approve", approver).status_code == 200


def test_close_blocked_while_pending(proj):
    ky, _ = provisional(proj)
    r = proj.post(f"/kpi/periods/{ky}/close", "pm")
    assert r.status_code == 409 and r.json()["error"]["code"] == "PENDING_EVALUATIONS"


def test_close_after_all_approved_locks_period(proj):
    ky, _ = provisional(proj); approve_all(proj, ky)
    assert proj.post(f"/kpi/periods/{ky}/close", "pm").json()["trang_thai"] == "CLOSED"
    assert manual(proj, ky, "m1", 50).status_code == 409
    assert proj.post(f"/kpi/periods/{ky}/calculate", "pm").status_code == 409
    assert proj.post(f"/kpi/periods/{ky}/close", "pm").status_code == 409


def test_violation_cannot_target_closed_period(proj):
    ky, _ = provisional(proj); approve_all(proj, ky); proj.post(f"/kpi/periods/{ky}/close", "pm")
    v = proj.post("/violations", "tl", {"ma_cv": proj.task()["ma_cv"], "ma_nd": proj.u["m1"], "ma_qd": 1, "noi_dung": "Trễ deadline"}).json()
    proj.post(f"/violations/{v['ma_vp']}/notify", "tl"); proj.post(f"/violations/{v['ma_vp']}/explanations", "m1", {"noi_dung": "giải trình"})
    r = proj.post(f"/violations/{v['ma_vp']}/conclude", "pm", {"ket_luan": "CONFIRMED", "ghi_chu": "Phạt", "ma_ky_ap_dung": ky})
    assert r.status_code == 409 and r.json()["error"]["code"] == "PERIOD_CLOSED"


def test_violation_invalid_period_of_other_project(proj):
    p2 = proj.project(ten_du_an="Dự án Beta")["ma_du_an"]
    other = proj.post(f"/projects/{p2}/kpi/periods", "pm", {"ten_ky": "Kỳ Z", "tu_ngay": D(-10), "den_ngay": D(20)}).json()["ma_ky"]
    v = proj.post("/violations", "tl", {"ma_cv": proj.task()["ma_cv"], "ma_nd": proj.u["m1"], "ma_qd": 1, "noi_dung": "Trễ deadline"}).json()
    proj.post(f"/violations/{v['ma_vp']}/notify", "tl"); proj.post(f"/violations/{v['ma_vp']}/explanations", "m1", {"noi_dung": "giải trình"})
    assert proj.post(f"/violations/{v['ma_vp']}/conclude", "pm", {"ket_luan": "CONFIRMED", "ghi_chu": "Phạt", "ma_ky_ap_dung": other}).status_code == 422


# ---- hiển thị ----
def test_member_sees_only_own_evaluation(proj):
    ky, ev = provisional(proj)
    mine = proj.get(f"/kpi/periods/{ky}/evaluations", "m1").json()
    assert len(mine) == 1 and mine[0]["ma_nguoi_dung"] == proj.u["m1"]
    assert len(proj.get(f"/kpi/periods/{ky}/evaluations", "pm").json()) == 4
    assert proj.get(f"/kpi/periods/{_p(ev[proj.u['m2']])}", "m1").status_code == 404


def test_my_kpi(proj):
    ky, _ = provisional(proj)
    r = proj.get("/me/kpi", "m1").json()
    assert len(r) == 1 and r[0]["ma_ky"] == ky and r[0]["diem_tong"] == 58.5


def test_history_only_approved_and_permissions(proj):
    ky, _ = provisional(proj)
    assert proj.get(f"/kpi/users/{proj.u['m1']}/history", "m1").json() == []
    approve_all(proj, ky)
    h = proj.get(f"/kpi/users/{proj.u['m1']}/history", "m1").json()
    assert len(h) == 1 and h[0]["diem_tong"] == 58.5 and h[0]["ten_ky"] == "Kỳ 1"
    assert proj.get(f"/kpi/users/{proj.u['m1']}/history", "pm").status_code == 200       # quản lý trực tiếp
    assert proj.get(f"/kpi/users/{proj.u['m1']}/history", "director").status_code == 200
    assert proj.get(f"/kpi/users/{proj.u['m1']}/history", "m2").status_code == 403


def test_previous_period_score_is_exposed(proj):
    """DFD 4.2 nhận "Lịch sử KPI cũ" từ D4: bảng điểm kỳ sau có điểm kỳ trước của cùng người."""
    ky, _ = provisional(proj); approve_all(proj, ky); proj.post(f"/kpi/periods/{ky}/close", "pm")
    ky2 = period(proj, ten_ky="Kỳ 2", tu_ngay=D(21), den_ngay=D(40)).json()["ma_ky"]
    cfg(proj, ky2); proj.post(f"/kpi/periods/{ky2}/open", "pm")
    assert evals(proj, ky2)[proj.u["m1"]]["diem_ky_truoc"] == 58.5
    assert evals(proj, ky)[proj.u["m1"]]["diem_ky_truoc"] is None
