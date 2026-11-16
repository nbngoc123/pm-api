from datetime import timedelta

import pytest
from sqlalchemy import update

from app.models import ViPham
from app.security import utcnow
from app.services.common import today


def V(c, who="tl", user="m1", ma_cv=None, qd=1, nd="Không hoàn thành đúng hạn"):
    ma_cv = ma_cv or c.task()["ma_cv"]
    return c.post("/violations", who, {"ma_cv": ma_cv, "ma_nd": c.u[user], "ma_qd": qd, "noi_dung": nd})


def mk(c, **kw):
    r = V(c, **kw); assert r.status_code == 201, r.text
    return r.json()


def pending(c, **kw):
    v = mk(c, **kw)
    assert c.post(f"/violations/{v['ma_vp']}/notify", "tl").status_code == 200
    return v


def explained(c, user="m1"):
    v = pending(c, user=user)
    assert c.post(f"/violations/{v['ma_vp']}/explanations", user, {"noi_dung": "Do thiếu tài nguyên"}).status_code == 201
    return v


def conclude(c, vp, who="pm", kq="CONFIRMED", note="Xác nhận", **kw):
    return c.post(f"/violations/{vp}/conclude", who, {"ket_luan": kq, "ghi_chu": note, **kw})


def expire(c, vp):
    with c.S() as db:
        db.execute(update(ViPham).where(ViPham.ma_vp == vp).values(han_giai_trinh=utcnow() - timedelta(hours=1))); db.commit()


def test_create_violation_draft(proj):
    v = mk(proj)
    assert v["trang_thai"] == "DRAFT" and v["diem_tru"] == 5 and v["ma_nguoi_lap"] == proj.u["tl"] and v["giai_trinh"] == []


@pytest.mark.parametrize("who,code", [("pm", 201), ("tl", 201), ("m2", 403), ("m1", 403), ("out", 404)])
def test_create_violation_permission(proj, who, code):
    assert V(proj, who=who).status_code == code


def test_cannot_file_against_self(proj):
    r = V(proj, who="tl", user="tl")
    assert r.status_code == 422 and r.json()["error"]["code"] == "SELF_VIOLATION"


def test_violator_must_be_member(proj):
    r = V(proj, user="out")
    assert r.status_code == 422 and r.json()["error"]["code"] == "NOT_PROJECT_MEMBER"


def test_unknown_rule_and_task(proj):
    assert V(proj, qd=999).status_code == 422
    assert V(proj, ma_cv=99999).status_code == 404


def test_short_description(proj):
    assert V(proj, nd="x").status_code == 422


@pytest.mark.parametrize("tu,den", [(-30, -1), (1, None)])
def test_rule_not_in_effect(proj, tu, den):
    r = proj.post("/violation-rules", "admin", {"ten_quy_dinh": "Quy định test", "diem_tru": 3, "tu_ngay": str(today() + timedelta(days=tu)),
                                               **({"den_ngay": str(today() + timedelta(days=den))} if den is not None else {})})
    res = V(proj, qd=r.json()["ma_qd"])
    assert res.status_code == 422 and res.json()["error"]["code"] == "RULE_NOT_ACTIVE"


def test_duplicate_violation_and_after_dismiss(proj):
    t = proj.task()["ma_cv"]
    v = mk(proj, ma_cv=t)
    assert V(proj, ma_cv=t).status_code == 409
    conclude(proj, v["ma_vp"], kq="DISMISSED")           # DRAFT -> DISMISSED
    assert V(proj, ma_cv=t).status_code == 201


# ---- quy định ----
@pytest.mark.parametrize("who,code", [("admin", 201), ("pm", 201), ("tl", 403), ("m1", 403), ("director", 403)])
def test_rule_create_permission(proj, who, code):
    assert proj.post("/violation-rules", who, {"ten_quy_dinh": "Quy định mới", "diem_tru": 2, "tu_ngay": str(today())}).status_code == code


@pytest.mark.parametrize("over", [{"diem_tru": 0}, {"diem_tru": 101}, {"ten_quy_dinh": "a"}, {"den_ngay": "2000-01-01"}])
def test_rule_validation(proj, over):
    body = {"ten_quy_dinh": "Quy định mới", "diem_tru": 2, "tu_ngay": str(today()), **over}
    assert proj.post("/violation-rules", "admin", body).status_code == 422


def test_rule_list_update_delete(proj):
    assert len(proj.get("/violation-rules", "m1").json()) == 3
    r = proj.post("/violation-rules", "admin", {"ten_quy_dinh": "Quy định mới", "diem_tru": 2, "tu_ngay": str(today())}).json()
    assert proj.patch(f"/violation-rules/{r['ma_qd']}", "admin", {"diem_tru": 7}).json()["diem_tru"] == 7
    assert proj.patch(f"/violation-rules/{r['ma_qd']}", "admin", {"den_ngay": "2000-01-01"}).status_code == 422
    assert proj.delete(f"/violation-rules/{r['ma_qd']}", "admin").status_code == 200


def test_rule_in_use_cannot_delete(proj):
    mk(proj)
    r = proj.delete("/violation-rules/1", "admin")
    assert r.status_code == 409 and r.json()["error"]["code"] == "RULE_IN_USE"


# ---- gửi giải trình ----
def test_notify_moves_to_pending(proj):
    v = mk(proj)
    r = proj.post(f"/violations/{v['ma_vp']}/notify", "tl").json()
    assert r["trang_thai"] == "PENDING_EXPLANATION" and r["han_giai_trinh"]
    assert proj.get("/me/notifications", "m1").json()["items"][0]["loai"] == "VIOLATION_NOTICE"


def test_notify_twice(proj):
    v = pending(proj)
    assert proj.post(f"/violations/{v['ma_vp']}/notify", "tl").status_code == 409


def test_violator_cannot_notify(proj):
    v = mk(proj)
    assert proj.post(f"/violations/{v['ma_vp']}/notify", "m1").status_code == 403


def test_my_pending_list(proj):
    pending(proj); mk(proj)
    r = proj.get("/me/violations/pending", "m1").json()
    assert len(r) == 1 and proj.get("/me/violations/pending", "m2").json() == []


# ---- giải trình ----
def test_explain_ok(proj):
    v = pending(proj)
    r = proj.post(f"/violations/{v['ma_vp']}/explanations", "m1", {"noi_dung": "Lý do hợp lý", "duong_dan_bang_chung": "https://x/y.png"})
    assert r.status_code == 201
    got = proj.get(f"/violations/{v['ma_vp']}", "m1").json()
    assert got["trang_thai"] == "EXPLAINED" and got["giai_trinh"][0]["noi_dung"] == "Lý do hợp lý"


def test_explain_only_by_violator(proj):
    v = pending(proj)
    assert proj.post(f"/violations/{v['ma_vp']}/explanations", "m2", {"noi_dung": "Lý do hợp lý"}).status_code == 404


def test_explain_requires_pending(proj):
    v = mk(proj)
    r = proj.post(f"/violations/{v['ma_vp']}/explanations", "m1", {"noi_dung": "Lý do hợp lý"})
    assert r.status_code == 409


def test_explain_multiple_allowed_erd_n_to_1(proj):
    """ERD: GIẢI TRÌNH N–1 VI PHẠM ⇒ được nộp bổ sung nhiều đơn trước khi kết luận."""
    v = explained(proj)
    assert proj.post(f"/violations/{v['ma_vp']}/explanations", "m1", {"noi_dung": "Bổ sung bằng chứng"}).status_code == 201
    assert len(proj.get(f"/violations/{v['ma_vp']}", "m1").json()["giai_trinh"]) == 2
    conclude(proj, v["ma_vp"])
    assert proj.post(f"/violations/{v['ma_vp']}/explanations", "m1", {"noi_dung": "Sau kết luận"}).status_code == 409


def test_explain_short_text(proj):
    v = pending(proj)
    assert proj.post(f"/violations/{v['ma_vp']}/explanations", "m1", {"noi_dung": "ab"}).status_code == 422


def test_explain_after_deadline(proj):
    v = pending(proj); expire(proj, v["ma_vp"])
    r = proj.post(f"/violations/{v['ma_vp']}/explanations", "m1", {"noi_dung": "Muộn rồi mà"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "EXPLANATION_DEADLINE_PASSED"


def test_explanation_notifies_creator(proj):
    explained(proj)
    assert any(n["loai"] == "EXPLANATION_SUBMITTED" for n in proj.get("/me/notifications", "tl").json()["items"])


# ---- kết luận ----
def test_conclude_confirmed(proj):
    v = explained(proj)
    r = conclude(proj, v["ma_vp"]).json()
    assert r["trang_thai"] == "CONFIRMED" and r["ngay_xu_ly"] == str(today()) and r["ma_nguoi_xu_ly"] == proj.u["pm"]


def test_conclude_dismissed_has_no_period(proj):
    v = explained(proj)
    assert conclude(proj, v["ma_vp"], kq="DISMISSED").json()["trang_thai"] == "DISMISSED"


def test_conclude_notifies_violator(proj):
    v = explained(proj); conclude(proj, v["ma_vp"])
    assert proj.get("/me/notifications", "m1").json()["items"][0]["loai"] == "VIOLATION_CONCLUDED"


@pytest.mark.parametrize("who,code", [("tl", 403), ("m1", 403), ("m2", 404), ("out", 404)])
def test_conclude_permission(proj, who, code):
    v = explained(proj)
    assert conclude(proj, v["ma_vp"], who=who).status_code == code


def test_conclude_before_explanation_deadline(proj):
    v = pending(proj)
    r = conclude(proj, v["ma_vp"])
    assert r.status_code == 409 and r.json()["error"]["code"] == "INVALID_VIOLATION_STATE"


def test_conclude_after_deadline_without_explanation(proj):
    v = pending(proj); expire(proj, v["ma_vp"])
    assert conclude(proj, v["ma_vp"]).json()["trang_thai"] == "CONFIRMED"


def test_conclude_draft_only_dismiss(proj):
    v = mk(proj)
    assert conclude(proj, v["ma_vp"]).status_code == 409
    assert conclude(proj, v["ma_vp"], kq="DISMISSED").status_code == 200


def test_conclude_twice(proj):
    v = explained(proj); conclude(proj, v["ma_vp"])
    assert conclude(proj, v["ma_vp"]).status_code == 409


@pytest.mark.parametrize("body", [{"ket_luan": "CONFIRMED", "ghi_chu": "x"}, {"ket_luan": "MAYBE", "ghi_chu": "xác nhận"}, {"ghi_chu": "xác nhận"}])
def test_conclude_validation(proj, body):
    v = explained(proj)
    assert proj.post(f"/violations/{v['ma_vp']}/conclude", "pm", body).status_code == 422


def test_only_employee_can_be_violator(proj):
    """ERD: NHÂN VIÊN –Bị ghi nhận– VI PHẠM ⇒ người thuộc loại QUẢN LÝ (vd PM) không bị lập biên bản."""
    r = V(proj, user="pm")
    assert r.status_code == 422 and r.json()["error"]["code"] == "VIOLATOR_MUST_BE_EMPLOYEE"


def test_direct_manager_outside_project_can_conclude(proj):
    v = explained(proj, user="m2")                       # mgr2 là quản lý trực tiếp của m2, không thuộc dự án
    assert proj.get(f"/violations/{v['ma_vp']}", "mgr2").status_code == 200
    assert conclude(proj, v["ma_vp"], who="mgr2").status_code == 200


# ---- xem ----
def test_get_visibility(proj):
    v = mk(proj)
    for who, code in (("m1", 200), ("tl", 200), ("pm", 200), ("m2", 404), ("out", 404)):
        assert proj.get(f"/violations/{v['ma_vp']}", who).status_code == code, who


def test_list_scope(proj):
    mk(proj, user="m1"); mk(proj, user="m2")
    q = lambda who, extra="": proj.get(f"/violations?ma_da={proj.pid}{extra}", who).json()["total"]
    assert q("pm") == 2 and q("tl") == 2 and q("m1") == 1 and q("m2") == 1 and q("out") == 0
    assert q("pm", f"&ma_nd={proj.u['m1']}") == 1 and q("pm", "&trang_thai=CONFIRMED") == 0


def test_list_without_project_only_own(proj):
    mk(proj, user="m1")
    assert proj.get("/violations", "m1").json()["total"] == 1 and proj.get("/violations", "m2").json()["total"] == 0
