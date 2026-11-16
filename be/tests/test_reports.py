import io
from datetime import timedelta

import pytest
from openpyxl import load_workbook

from app.services.common import today


def D(n): return str(today() + timedelta(days=n))


def test_dashboard_fresh_user(ctx):
    d = ctx.get("/dashboard/me", "out").json()
    assert d["task_theo_trang_thai"] == {} and d["task_tre_han"] == 0 and d["gio_tuan_nay"] == 0 and d["kpi_gan_nhat"] is None and d["so_du_an"] == 0


def test_dashboard_counts(proj):
    proj.done_task()
    t = proj.task(han_hoan_thanh=D(-1), ngay_bat_dau_du_kien=D(-3)); proj.assign(t["ma_cv"], "m1"); proj.go(t["ma_cv"], "IN_PROGRESS", "m1")
    u = proj.task(han_hoan_thanh=D(3)); proj.assign(u["ma_cv"], "m1")
    proj.log(t["ma_cv"], hours=2)
    d = proj.get("/dashboard/me", "m1").json()
    assert d["task_theo_trang_thai"] == {"IN_PROGRESS": 1, "TODO": 1} or d["task_theo_trang_thai"].get("IN_PROGRESS") == 1
    assert d["task_tre_han"] == 1 and len(d["deadline_sap_toi"]) == 1 and d["deadline_sap_toi"][0]["ma_cv"] == u["ma_cv"]
    assert d["gio_thang_nay"] >= 0 and d["so_du_an"] == 1 and d["thong_bao_chua_doc"] >= 2


def test_dashboard_pending_explanations(proj):
    v = proj.post("/violations", "tl", {"ma_cv": proj.task()["ma_cv"], "ma_nd": proj.u["m1"], "ma_qd": 1, "noi_dung": "Trễ deadline"}).json()
    proj.post(f"/violations/{v['ma_vp']}/notify", "tl")
    assert proj.get("/dashboard/me", "m1").json()["vi_pham_cho_giai_trinh"] == 1


@pytest.mark.parametrize("who,code", [("director", 200), ("admin", 200), ("pm", 403), ("m1", 403)])
def test_portfolio_permission(proj, who, code):
    assert proj.get("/reports/portfolio", who).status_code == code


def test_portfolio_content(proj):
    proj.project(ten_du_an="Dự án Beta")
    proj.done_task(); proj.task()
    r = proj.get("/reports/portfolio", "director").json()
    assert r["tong_du_an"] == 2 and r["theo_trang_thai"] == {"ACTIVE": 1, "PLANNING": 1}
    a = next(x for x in r["du_an"] if x["ma_du_an"] == proj.pid)
    assert a["ty_le_hoan_thanh"] == 50 and a["tong_task"] == 2 and a["vuot_ngan_sach_gio"] is False
    assert proj.get("/reports/portfolio?trang_thai=PLANNING", "director").json()["tong_du_an"] == 1


@pytest.mark.parametrize("who,code", [("pm", 200), ("tl", 403), ("director", 403), ("m1", 403), ("out", 404)])
def test_project_report_permission(proj, who, code):
    assert proj.get(f"/reports/projects/{proj.pid}", who).status_code == code


def test_project_report_content(proj):
    proj.done_task()
    r = proj.get(f"/reports/projects/{proj.pid}", "pm").json()
    assert r["tong_quan"]["task_hoan_thanh"] == 1 and "evm" in r and len(r["nhan_su"]) == 4 and r["vi_pham"] == {}


def get_export(c, who, ds, fmt="csv", ma_da=True):
    return c.get(f"/exports?dataset={ds}&format={fmt}" + (f"&ma_da={c.pid}" if ma_da else ""), who)


def test_export_csv_has_bom_and_header(proj):
    proj.task(ten_cv="Công việc A")
    r = get_export(proj, "pm", "tasks")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert r.content.startswith(b"\xef\xbb\xbf") and "Công việc A" in r.content.decode("utf-8-sig") and "attachment" in r.headers["content-disposition"]


def test_export_xlsx_is_valid_workbook(proj):
    proj.task(ten_cv="Công việc A")
    r = get_export(proj, "pm", "tasks", "xlsx")
    ws = load_workbook(io.BytesIO(r.content)).active
    assert ws["B1"].value == "ten_cv" and ws["B2"].value == "Công việc A"


def test_export_prevents_formula_injection(proj):
    proj.task(ten_cv="=HYPERLINK(\"http://evil\")")
    assert "'=HYPERLINK" in get_export(proj, "pm", "tasks").content.decode("utf-8-sig")


@pytest.mark.parametrize("ds", ["tasks", "timesheets", "violations", "kpi"])
def test_export_all_project_datasets(proj, ds):
    assert get_export(proj, "pm", ds).status_code == 200


def test_export_permissions(proj):
    assert get_export(proj, "m1", "tasks").status_code == 403
    assert get_export(proj, "out", "tasks").status_code == 404
    assert get_export(proj, "tl", "tasks").status_code == 403          # DFD 6.5: "File báo cáo" chỉ đến Quản lý dự án
    assert get_export(proj, "director", "tasks").status_code == 403
    assert get_export(proj, "admin", "tasks").status_code == 200
    assert proj.get("/exports?dataset=portfolio&format=csv", "director").status_code == 422     # không có luồng xuất portfolio trong DFD


@pytest.mark.parametrize("q", ["dataset=hack", "dataset=tasks&format=pdf"])
def test_export_validation(proj, q):
    assert proj.get(f"/exports?{q}" + ("" if "ma_da" in q else ""), "pm").status_code in (422,)


def test_export_is_audited(proj):
    get_export(proj, "pm", "tasks")
    assert proj.get("/audit-logs?loai_su_kien=REPORT_EXPORTED", "admin").json()["total"] == 1


def test_dashboard_personal_filters(proj):
    """DFD 6.1: "Tham số lọc cá nhân" của Thành viên."""
    p2 = proj.project(ten_du_an="Dự án Beta")["ma_du_an"]
    proj.post(f"/projects/{p2}/members", "pm", {"ma_nguoi_dung": proj.u["m1"]})
    proj.post(f"/projects/{p2}/members", "pm", {"ma_nguoi_dung": proj.u["tl"], "vai_tro": "TEAM_LEAD"})
    proj.patch(f"/projects/{p2}/status", "pm", {"trang_thai": "ACTIVE"})
    a = proj.task(); proj.assign(a["ma_cv"], "m1")
    b = proj.task(pid=p2); proj.assign(b["ma_cv"], "m1", who="tl") if False else proj.post(f"/tasks/{b['ma_cv']}/assignments", "pm", {"ma_nd": proj.u["m1"]})
    assert sum(proj.get("/dashboard/me", "m1").json()["task_theo_trang_thai"].values()) == 2
    assert sum(proj.get(f"/dashboard/me?ma_da={p2}", "m1").json()["task_theo_trang_thai"].values()) == 1
    assert proj.get(f"/dashboard/me?tu_ngay={D(-1)}&den_ngay={D(1)}", "m1").json()["gio_trong_khoang"] == 0


def test_portfolio_filters(proj):
    """DFD 6.1: "Tham số lọc báo cáo tổng" của Ban giám đốc."""
    proj.project(ten_du_an="Dự án Beta")
    q = lambda s: proj.get(f"/reports/portfolio?{s}", "director").json()["tong_du_an"]
    assert q("") == 2 and q(f"ma_quan_ly={proj.u['pm']}") == 2 and q(f"ma_quan_ly={proj.u['mgr2']}") == 0
    assert q(f"tu_ngay={D(500)}") == 0 and q(f"den_ngay={D(-500)}") == 0 and q("suc_khoe=GREY") == 2 and q("suc_khoe=RED") == 0
    assert proj.get("/reports/portfolio?suc_khoe=PINK", "director").status_code == 422
