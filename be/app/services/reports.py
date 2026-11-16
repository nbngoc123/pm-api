import csv, io
from datetime import date, datetime, timedelta

from openpyxl import Workbook
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import TrangThaiDuAn, TrangThaiPhanCong as PC, TrangThaiTask as TS, TrangThaiViPham
from app.errors import invalid
from app.models import (DanhGiaKPI, DuAn, KyKPI, NguoiDung, NhatKyGioLam, PhanCong, Task, ThanhVienDuAn, ThongBao, ViPham)
from app.services import progress
from app.services.common import f, today
from app.services.projects import OPEN_TASK, overview
from app.services.tasks import assignees


def dashboard_me(db: Session, user: NguoiDung, ma_da: int | None = None, tu_ngay: date | None = None, den_ngay: date | None = None) -> dict:
    """6.3 Dashboard cá nhân; ma_da / tu_ngay / den_ngay = "Tham số lọc cá nhân" (DFD 6.1)."""
    t0 = today()
    mine = select(PhanCong.ma_cv).where(PhanCong.ma_nd == user.ma_nd, PhanCong.trang_thai_phan_cong == PC.ASSIGNED)
    if ma_da:
        mine = mine.join(Task, Task.ma_cv == PhanCong.ma_cv).where(Task.ma_du_an == ma_da)
    by = {s.value: n for s, n in db.execute(select(Task.trang_thai, func.count()).where(Task.ma_cv.in_(mine)).group_by(Task.trang_thai))}
    overdue = db.scalar(select(func.count()).select_from(Task).where(Task.ma_cv.in_(mine), Task.trang_thai.in_(OPEN_TASK), Task.han_hoan_thanh < t0))
    upcoming = db.scalars(select(Task).where(Task.ma_cv.in_(mine), Task.trang_thai.in_(OPEN_TASK), Task.han_hoan_thanh >= t0,
                                             Task.han_hoan_thanh <= t0 + timedelta(days=7)).order_by(Task.han_hoan_thanh).limit(10)).all()
    def hrs(since: datetime, until: datetime | None = None):
        q = select(func.coalesce(func.sum(NhatKyGioLam.so_gio), 0)).where(NhatKyGioLam.ma_nd == user.ma_nd, NhatKyGioLam.bat_dau >= since)
        if until:
            q = q.where(NhatKyGioLam.bat_dau < until)
        if ma_da:
            q = q.join(Task, Task.ma_cv == NhatKyGioLam.ma_cv).where(Task.ma_du_an == ma_da)
        return float(db.scalar(q))
    week = datetime.combine(t0 - timedelta(days=t0.weekday()), datetime.min.time())
    month = datetime.combine(t0.replace(day=1), datetime.min.time())
    kpi = db.scalar(select(DanhGiaKPI).where(DanhGiaKPI.ma_nguoi_dung == user.ma_nd).order_by(DanhGiaKPI.ma_ky.desc()).limit(1))
    return {"task_theo_trang_thai": by, "task_tre_han": overdue,
            "deadline_sap_toi": [{"ma_cv": t.ma_cv, "ten_cv": t.ten_cv, "han_hoan_thanh": t.han_hoan_thanh, "uu_tien": t.uu_tien.value} for t in upcoming],
            "gio_tuan_nay": hrs(week), "gio_thang_nay": hrs(month),
            "gio_trong_khoang": None if not (tu_ngay or den_ngay) else hrs(datetime.combine(tu_ngay or date.min, datetime.min.time()),
                                                                          datetime.combine((den_ngay or date.max - timedelta(days=1)) + timedelta(days=1), datetime.min.time())),
            "vi_pham_cho_giai_trinh": db.scalar(select(func.count()).select_from(ViPham).where(ViPham.ma_nd == user.ma_nd, ViPham.trang_thai == TrangThaiViPham.PENDING_EXPLANATION)),
            "kpi_gan_nhat": None if not kpi else {"ma_ky": kpi.ma_ky, "trang_thai": kpi.trang_thai.value, "diem_tong": f(kpi.diem_tong)},
            "thong_bao_chua_doc": db.scalar(select(func.count()).select_from(ThongBao).where(ThongBao.ma_nd == user.ma_nd, ThongBao.da_doc.is_(False))),
            "so_du_an": db.scalar(select(func.count()).select_from(ThanhVienDuAn).where(ThanhVienDuAn.ma_nguoi_dung == user.ma_nd, ThanhVienDuAn.trang_thai == "ACTIVE"))}


def portfolio(db: Session, trang_thai=None, ma_quan_ly=None, tu_ngay=None, den_ngay=None, suc_khoe=None) -> dict:
    """6.4 Báo cáo portfolio; các tham số = "Tham số lọc báo cáo tổng" từ Ban giám đốc (DFD 6.1)."""
    st = select(DuAn).order_by(DuAn.ma_du_an)
    if trang_thai:
        st = st.where(DuAn.trang_thai == trang_thai)
    if ma_quan_ly:
        st = st.where(DuAn.ma_quan_ly == ma_quan_ly)
    if tu_ngay:
        st = st.where(DuAn.ngay_ket_thuc_du_kien >= tu_ngay)
    if den_ngay:
        st = st.where(DuAn.ngay_bat_dau <= den_ngay)
    items = []
    for p in db.scalars(st):
        ov, e = overview(db, p), progress.compute_evm(db, p)
        if suc_khoe and e["suc_khoe"] != suc_khoe:
            continue
        nvp = db.scalar(select(func.count()).select_from(ViPham).join(Task, Task.ma_cv == ViPham.ma_cv).where(
            Task.ma_du_an == p.ma_du_an, ViPham.trang_thai == TrangThaiViPham.CONFIRMED))
        items.append({"ma_du_an": p.ma_du_an, "ten_du_an": p.ten_du_an, "trang_thai": p.trang_thai.value, "ma_quan_ly": p.ma_quan_ly,
                      "ty_le_hoan_thanh": ov["ty_le_hoan_thanh"], "tong_task": ov["tong_task"], "task_tre_han": ov["task_tre_han"],
                      "gio_thuc_te": ov["gio_thuc_te"], "ngan_sach_gio": ov["ngan_sach_gio"],
                      "vuot_ngan_sach_gio": bool(ov["ngan_sach_gio"]) and ov["gio_thuc_te"] > ov["ngan_sach_gio"],
                      "spi": e["spi"], "cpi": e["cpi"], "suc_khoe": e["suc_khoe"], "vi_pham_da_xu_ly": nvp,
                      "ngay_ket_thuc_du_kien": p.ngay_ket_thuc_du_kien})
    cnt = {}
    for i in items:
        cnt[i["trang_thai"]] = cnt.get(i["trang_thai"], 0) + 1
    return {"tong_du_an": len(items), "theo_trang_thai": cnt, "du_an": items}


def project_report(db: Session, p: DuAn) -> dict:
    members = []
    for m in db.scalars(select(ThanhVienDuAn).where(ThanhVienDuAn.ma_du_an == p.ma_du_an, ThanhVienDuAn.trang_thai == "ACTIVE")):
        mine = select(PhanCong.ma_cv).join(Task, Task.ma_cv == PhanCong.ma_cv).where(
            PhanCong.ma_nd == m.ma_nguoi_dung, PhanCong.trang_thai_phan_cong == PC.ASSIGNED, Task.ma_du_an == p.ma_du_an)
        h = db.scalar(select(func.coalesce(func.sum(NhatKyGioLam.so_gio), 0)).join(Task, Task.ma_cv == NhatKyGioLam.ma_cv).where(
            NhatKyGioLam.ma_nd == m.ma_nguoi_dung, Task.ma_du_an == p.ma_du_an))
        members.append({"ma_nd": m.ma_nguoi_dung, "ho_ten": db.get(NguoiDung, m.ma_nguoi_dung).ho_ten,
                        "task_dang_lam": db.scalar(select(func.count()).select_from(Task).where(Task.ma_cv.in_(mine), Task.trang_thai.in_(OPEN_TASK))),
                        "gio_thuc_te": float(h)})
    vp = {s.value: n for s, n in db.execute(select(ViPham.trang_thai, func.count()).join(Task, Task.ma_cv == ViPham.ma_cv).where(Task.ma_du_an == p.ma_du_an).group_by(ViPham.trang_thai))}
    kp = db.execute(select(KyKPI.ma_ky, KyKPI.ten_ky, KyKPI.trang_thai, func.avg(DanhGiaKPI.diem_tong)).join(DanhGiaKPI, DanhGiaKPI.ma_ky == KyKPI.ma_ky, isouter=True)
                    .where(KyKPI.ma_du_an == p.ma_du_an).group_by(KyKPI.ma_ky)).all()
    return {"tong_quan": overview(db, p), "evm": progress.compute_evm(db, p), "nhan_su": members, "vi_pham": vp,
            "kpi": [{"ma_ky": a, "ten_ky": b, "trang_thai": c.value, "diem_trung_binh": f(d)} for a, b, c, d in kp]}


# ---- 6.5 xuất báo cáo ----
def dataset(db: Session, name: str, ma_da: int | None):
    if ma_da is None:
        raise invalid("MISSING_PROJECT", "Cần tham số ma_da")
    if name == "tasks":
        h = ["ma_cv", "ten_cv", "trang_thai", "uu_tien", "ty_le_hoan_thanh", "han_hoan_thanh", "gio_du_kien", "nguoi_duoc_giao"]
        rows = [[t.ma_cv, t.ten_cv, t.trang_thai.value, t.uu_tien.value, t.ty_le_hoan_thanh, t.han_hoan_thanh, float(t.gio_du_kien),
                 ";".join(str(x) for x in assignees(db, t.ma_cv))] for t in db.scalars(select(Task).where(Task.ma_du_an == ma_da).order_by(Task.ma_cv))]
        return h, rows
    if name == "timesheets":
        h = ["ma_nk", "ma_cv", "ma_nd", "bat_dau", "ket_thuc", "so_gio", "chi_phi_thuc_te", "noi_dung"]
        q = select(NhatKyGioLam).join(Task, Task.ma_cv == NhatKyGioLam.ma_cv).where(Task.ma_du_an == ma_da).order_by(NhatKyGioLam.ma_nk)
        return h, [[e.ma_nk, e.ma_cv, e.ma_nd, e.bat_dau, e.ket_thuc, float(e.so_gio), float(e.chi_phi_thuc_te), e.noi_dung] for e in db.scalars(q)]
    if name == "violations":
        h = ["ma_vp", "ma_cv", "ma_nd", "ma_qd", "trang_thai", "thoi_diem", "ngay_xu_ly", "ket_luan"]
        q = select(ViPham).join(Task, Task.ma_cv == ViPham.ma_cv).where(Task.ma_du_an == ma_da).order_by(ViPham.ma_vp)
        return h, [[v.ma_vp, v.ma_cv, v.ma_nd, v.ma_qd, v.trang_thai.value, v.thoi_diem, v.ngay_xu_ly, v.ket_luan] for v in db.scalars(q)]
    if name == "kpi":
        h = ["ma_ky", "ma_nguoi_dung", "trang_thai", "diem_goc", "diem_tru", "diem_tong", "ngay_duyet"]
        q = select(DanhGiaKPI).join(KyKPI, KyKPI.ma_ky == DanhGiaKPI.ma_ky).where(KyKPI.ma_du_an == ma_da).order_by(DanhGiaKPI.ma_ky, DanhGiaKPI.ma_nguoi_dung)
        return h, [[e.ma_ky, e.ma_nguoi_dung, e.trang_thai.value, f(e.diem_goc), f(e.diem_tru), f(e.diem_tong), e.ngay_duyet] for e in db.scalars(q)]
    raise invalid("UNKNOWN_DATASET", f"dataset '{name}' không hợp lệ")


def _safe(v):
    """Chống CSV/Excel formula injection."""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return v


def to_csv(headers, rows) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf); w.writerow(headers)
    for r in rows:
        w.writerow([_safe(x) for x in r])
    return ("\ufeff" + buf.getvalue()).encode("utf-8")      # BOM để Excel hiển thị tiếng Việt đúng


def to_xlsx(headers, rows) -> bytes:
    wb = Workbook(); ws = wb.active; ws.append(headers)
    for r in rows:
        ws.append([_safe(x) if not isinstance(x, (datetime,)) else x for x in r])
    out = io.BytesIO(); wb.save(out)
    return out.getvalue()
