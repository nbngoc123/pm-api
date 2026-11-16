from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import (NguonDuLieuKPI as SRC, TrangThaiDanhGia as ES, TrangThaiKy as KS, TrangThaiPhanCong as PC,
                       TrangThaiTask as TS, TrangThaiThanhVien, TrangThaiViPham)
from app.errors import conflict, forbidden, invalid
from app.models import (CauHinhKPI, ChiTietKPI, DanhGiaKPI, DuAn, KyKPI, NguoiDung, NhatKyGioLam, PhanCong, QuanLy, Task,
                        ThanhVienDuAn, TieuChiKPI, ViPham)
from app.schemas.common import D
from app.services.access import is_direct_manager, project_perms
from app.services.common import audit, f, notify, today
from app.services.projects import ensure_writable


# ---- tiêu chí ----
def create_criterion(db, actor, d) -> TieuChiKPI:
    if db.scalar(select(TieuChiKPI.ma_tieu_chi).where(func.lower(TieuChiKPI.ten_tieu_chi) == d.ten_tieu_chi.lower())):
        raise conflict("DUPLICATE_CRITERION", "Tên tiêu chí đã tồn tại")
    c = TieuChiKPI(**d.model_dump()); db.add(c); db.flush()
    audit(db, actor.ma_nd, "KPI_CRITERION_CREATED", "tieu_chi_kpi", c.ma_tieu_chi, c.ten_tieu_chi)
    return c


# ---- kỳ ----
def create_period(db, actor, p: DuAn, d) -> KyKPI:
    ensure_writable(p)
    if db.scalar(select(KyKPI.ma_ky).where(KyKPI.ma_du_an == p.ma_du_an, KyKPI.tu_ngay <= d.den_ngay, KyKPI.den_ngay >= d.tu_ngay)):
        raise conflict("PERIOD_OVERLAP", "Kỳ KPI trùng thời gian với kỳ khác của dự án")
    k = KyKPI(ma_du_an=p.ma_du_an, ten_ky=d.ten_ky, tu_ngay=d.tu_ngay, den_ngay=d.den_ngay); db.add(k); db.flush()
    audit(db, actor.ma_nd, "KPI_PERIOD_CREATED", "ky_kpi", k.ma_ky, k.ten_ky)
    return k


def set_config(db, actor, k: KyKPI, d) -> list[CauHinhKPI]:
    if k.trang_thai != KS.DRAFT:
        raise conflict("PERIOD_NOT_EDITABLE", "Chỉ cấu hình khi kỳ ở trạng thái DRAFT")
    ids = [i.ma_tieu_chi for i in d.items]
    if len(set(ids)) != len(ids):
        raise invalid("DUPLICATE_CRITERION", "Tiêu chí bị lặp trong cấu hình")
    found = set(db.scalars(select(TieuChiKPI.ma_tieu_chi).where(TieuChiKPI.ma_tieu_chi.in_(ids))))
    if found != set(ids):
        raise invalid("CRITERION_NOT_FOUND", f"Không tồn tại tiêu chí: {sorted(set(ids) - found)}")
    total = sum(D(i.trong_so) for i in d.items)
    if abs(total - Decimal(100)) > Decimal("0.01"):
        raise invalid("WEIGHT_SUM_INVALID", f"Tổng trọng số phải bằng 100 (hiện {total})")
    for old in db.scalars(select(CauHinhKPI).where(CauHinhKPI.ma_ky == k.ma_ky)):
        db.delete(old)
    db.flush()
    rows = [CauHinhKPI(ma_ky=k.ma_ky, ma_tieu_chi=i.ma_tieu_chi, trong_so=D(i.trong_so), chi_tieu=D(i.chi_tieu)) for i in d.items]
    db.add_all(rows); db.flush()
    audit(db, actor.ma_nd, "KPI_CONFIGURED", "ky_kpi", k.ma_ky)
    return rows


def config_rows(db, k: KyKPI):
    return db.execute(select(CauHinhKPI, TieuChiKPI).join(TieuChiKPI, TieuChiKPI.ma_tieu_chi == CauHinhKPI.ma_tieu_chi)
                      .where(CauHinhKPI.ma_ky == k.ma_ky).order_by(CauHinhKPI.ma_tieu_chi)).all()


def config_out(db, k: KyKPI) -> dict:
    rows = config_rows(db, k)
    return {"ma_ky": k.ma_ky, "tong_trong_so": float(sum(c.trong_so for c, _ in rows)),
            "items": [{"ma_tieu_chi": c.ma_tieu_chi, "ten_tieu_chi": t.ten_tieu_chi, "nguon_du_lieu": t.nguon_du_lieu.value,
                       "trong_so": float(c.trong_so), "chi_tieu": float(c.chi_tieu)} for c, t in rows]}


def _ensure_evals(db, k: KyKPI) -> int:
    crit = [c.ma_tieu_chi for c, _ in config_rows(db, k)]
    existing = set(db.scalars(select(DanhGiaKPI.ma_nguoi_dung).where(DanhGiaKPI.ma_ky == k.ma_ky)))
    n = 0
    for m in db.scalars(select(ThanhVienDuAn).where(ThanhVienDuAn.ma_du_an == k.ma_du_an, ThanhVienDuAn.trang_thai == TrangThaiThanhVien.ACTIVE)):
        if m.ma_nguoi_dung in existing:
            continue
        db.add(DanhGiaKPI(ma_ky=k.ma_ky, ma_nguoi_dung=m.ma_nguoi_dung, trang_thai=ES.DRAFT)); n += 1
        db.flush()                       # cha (ĐÁNH GIÁ KPI) phải có trước con (CHI TIẾT KPI) – FK ghép
        for c in crit:
            db.add(ChiTietKPI(ma_nguoi_dung=m.ma_nguoi_dung, ma_ky=k.ma_ky, ma_tieu_chi=c))
    db.flush()
    return n


def open_period(db, actor, k: KyKPI) -> int:
    if k.trang_thai != KS.DRAFT:
        raise conflict("PERIOD_NOT_EDITABLE", "Kỳ không ở trạng thái DRAFT")
    if not config_rows(db, k):
        raise conflict("NO_CONFIG", "Chưa cấu hình tiêu chí/trọng số cho kỳ")
    k.trang_thai = KS.OPEN
    n = _ensure_evals(db, k)
    audit(db, actor.ma_nd, "KPI_PERIOD_OPENED", "ky_kpi", k.ma_ky, f"{n} người")
    return n


def sync_members(db, actor, k: KyKPI) -> int:
    if k.trang_thai != KS.OPEN:
        raise conflict("PERIOD_NOT_OPEN", "Kỳ chưa mở hoặc đã đóng")
    return _ensure_evals(db, k)


def can_manage(db, actor, k: KyKPI, employee_id: int) -> bool:
    return "kpi.approve" in project_perms(db, actor, k.ma_du_an) or is_direct_manager(db, actor.ma_nd, employee_id)


def set_manual(db, actor, k: KyKPI, items):
    if k.trang_thai != KS.OPEN:
        raise conflict("PERIOD_NOT_OPEN", "Kỳ chưa mở hoặc đã đóng")
    cfg = {c.ma_tieu_chi: t for c, t in config_rows(db, k)}
    n = 0
    for it in items:
        if it.ma_tieu_chi not in cfg:
            raise invalid("CRITERION_NOT_IN_PERIOD", f"Tiêu chí {it.ma_tieu_chi} không thuộc kỳ")
        if cfg[it.ma_tieu_chi].nguon_du_lieu != SRC.MANUAL:
            raise invalid("CRITERION_NOT_MANUAL", f"Tiêu chí {it.ma_tieu_chi} được tính tự động")
        ev = db.scalar(select(DanhGiaKPI).where(DanhGiaKPI.ma_ky == k.ma_ky, DanhGiaKPI.ma_nguoi_dung == it.ma_nd))
        if not ev:
            raise invalid("USER_NOT_IN_PERIOD", f"Người dùng {it.ma_nd} không có đánh giá trong kỳ")
        if not can_manage(db, actor, k, it.ma_nd):
            raise forbidden()
        if ev.trang_thai == ES.APPROVED:
            raise conflict("EVALUATION_LOCKED", "Đánh giá đã được phê duyệt")
        ct = db.get(ChiTietKPI, (it.ma_nd, k.ma_ky, it.ma_tieu_chi))
        ct.gia_tri_thu_cong = D(it.gia_tri)
        if it.ghi_chu is not None:
            ct.ghi_chu = it.ghi_chu
        n += 1
    audit(db, actor.ma_nd, "KPI_MANUAL_INPUT", "ky_kpi", k.ma_ky, f"{n} giá trị")
    return n


# ---- 4.2 thu thập & tính toán tự động ----
def _auto_value(db, k: KyKPI, uid: int, source: SRC) -> float | None:
    rows = db.execute(select(Task).join(PhanCong, PhanCong.ma_cv == Task.ma_cv).where(
        PhanCong.ma_nd == uid, PhanCong.trang_thai_phan_cong.in_([PC.ASSIGNED, PC.COMPLETED]), Task.ma_du_an == k.ma_du_an,
        Task.trang_thai != TS.CANCELLED, Task.han_hoan_thanh >= k.tu_ngay, Task.han_hoan_thanh <= k.den_ngay)
        .distinct()).scalars().all()
    if source == SRC.TASK_COMPLETION:
        return round(sum(t.trang_thai == TS.DONE for t in rows) / len(rows) * 100, 2) if rows else None
    if source == SRC.ON_TIME_RATE:
        done = [t for t in rows if t.trang_thai == TS.DONE and t.hoan_thanh_luc]
        if not done:
            return None
        ok = sum((t.hoan_thanh_luc + timedelta(hours=settings.tz_offset_hours)).date() <= t.han_hoan_thanh for t in done)
        return round(ok / len(done) * 100, 2)
    if source == SRC.HOURS_UTILIZATION:
        expected = sum(float(t.gio_du_kien) for t in rows)
        if expected <= 0:
            return None
        from datetime import datetime
        s = datetime.combine(k.tu_ngay, datetime.min.time()); e = datetime.combine(k.den_ngay + timedelta(days=1), datetime.min.time())
        h = db.scalar(select(func.coalesce(func.sum(NhatKyGioLam.so_gio), 0)).join(Task, Task.ma_cv == NhatKyGioLam.ma_cv).where(
            NhatKyGioLam.ma_nd == uid, Task.ma_du_an == k.ma_du_an, NhatKyGioLam.bat_dau >= s, NhatKyGioLam.bat_dau < e))
        return round(float(h) / expected * 100, 2)
    return None


def penalty(db, k: KyKPI, uid: int) -> Decimal:
    from app.models import QuyDinhViPham
    r = db.scalar(select(func.coalesce(func.sum(QuyDinhViPham.diem_tru), 0)).join(ViPham, ViPham.ma_qd == QuyDinhViPham.ma_qd).where(
        ViPham.ma_nd == uid, ViPham.ma_ky_ap_dung == k.ma_ky, ViPham.trang_thai == TrangThaiViPham.CONFIRMED))
    return D(r)


def effective(ct: ChiTietKPI, src: SRC):
    return ct.gia_tri_thu_cong if src == SRC.MANUAL else ct.gia_tri_tu_dong


def score(cfg, cts: dict) -> Decimal:
    """Điểm gốc = Σ(trọng số × min(giá trị/chỉ tiêu,1)×100) / Σ trọng số (chỉ tính tiêu chí đã có dữ liệu)."""
    num = den = Decimal(0)
    for c, t in cfg:
        v = effective(cts[c.ma_tieu_chi], t.nguon_du_lieu)
        if v is None:
            continue
        ach = min(D(v) / c.chi_tieu, Decimal(1)) * 100
        num += c.trong_so * ach; den += c.trong_so
    return (num / den).quantize(Decimal("0.01")) if den else Decimal(0)


def calculate(db, actor, k: KyKPI) -> dict:
    if k.trang_thai != KS.OPEN:
        raise conflict("PERIOD_NOT_OPEN", "Kỳ chưa mở hoặc đã đóng")
    cfg = config_rows(db, k)
    done = skipped = 0
    for ev in db.scalars(select(DanhGiaKPI).where(DanhGiaKPI.ma_ky == k.ma_ky)):
        if ev.trang_thai in (ES.MEMBER_CONFIRMED, ES.APPROVED):
            skipped += 1; continue
        cts = {ct.ma_tieu_chi: ct for ct in db.scalars(select(ChiTietKPI).where(
            ChiTietKPI.ma_ky == k.ma_ky, ChiTietKPI.ma_nguoi_dung == ev.ma_nguoi_dung))}
        for c, t in cfg:
            if t.nguon_du_lieu != SRC.MANUAL:
                v = _auto_value(db, k, ev.ma_nguoi_dung, t.nguon_du_lieu)
                cts[c.ma_tieu_chi].gia_tri_tu_dong = None if v is None else D(v)
        ev.diem_goc = score(cfg, cts)
        ev.diem_tru = penalty(db, k, ev.ma_nguoi_dung)
        ev.diem_tong = max(Decimal(0), ev.diem_goc - ev.diem_tru)
        ev.trang_thai = ES.PROVISIONAL
        done += 1
    audit(db, actor.ma_nd, "KPI_CALCULATED", "ky_kpi", k.ma_ky, f"{done} tính, {skipped} bỏ qua")
    return {"da_tinh": done, "bo_qua": skipped}


# ---- 4.3 đánh giá & phê duyệt ----
def eval_out(db, ev: DanhGiaKPI) -> dict:
    k = db.get(KyKPI, ev.ma_ky)
    cts = {ct.ma_tieu_chi: ct for ct in db.scalars(select(ChiTietKPI).where(ChiTietKPI.ma_ky == ev.ma_ky, ChiTietKPI.ma_nguoi_dung == ev.ma_nguoi_dung))}
    ch = []
    for c, t in config_rows(db, k):
        ct = cts.get(c.ma_tieu_chi)
        v = effective(ct, t.nguon_du_lieu) if ct else None
        ch.append({"ma_tieu_chi": c.ma_tieu_chi, "ten_tieu_chi": t.ten_tieu_chi, "trong_so": float(c.trong_so), "chi_tieu": float(c.chi_tieu),
                   "gia_tri_tu_dong": f(ct.gia_tri_tu_dong) if ct else None, "gia_tri_thu_cong": f(ct.gia_tri_thu_cong) if ct else None,
                   "gia_tri_xac_nhan": f(ct.gia_tri_xac_nhan) if ct else None,
                   "ty_le_dat": None if v is None else round(min(float(v) / float(c.chi_tieu), 1) * 100, 2), "ghi_chu": ct.ghi_chu if ct else None})
    prev = db.scalar(select(DanhGiaKPI.diem_tong).join(KyKPI, KyKPI.ma_ky == DanhGiaKPI.ma_ky).where(
        DanhGiaKPI.ma_nguoi_dung == ev.ma_nguoi_dung, KyKPI.ma_du_an == k.ma_du_an, KyKPI.den_ngay < k.tu_ngay,
        DanhGiaKPI.trang_thai == ES.APPROVED).order_by(KyKPI.den_ngay.desc()).limit(1))     # DFD: D4 → 4.2 "Lịch sử KPI cũ"
    return {"diem_ky_truoc": f(prev), "ma_ky": ev.ma_ky, "ma_nguoi_dung": ev.ma_nguoi_dung, "ho_ten": db.get(NguoiDung, ev.ma_nguoi_dung).ho_ten,
            "trang_thai": ev.trang_thai, "diem_goc": f(ev.diem_goc), "diem_tru": f(ev.diem_tru) or 0.0, "diem_tong": f(ev.diem_tong),
            "ma_nguoi_duyet": ev.ma_nguoi_duyet, "ngay_xac_nhan": ev.ngay_xac_nhan, "ngay_duyet": ev.ngay_duyet, "nhan_xet": ev.nhan_xet,
            "chi_tiet": ch}


def confirm(db, actor, ev: DanhGiaKPI) -> DanhGiaKPI:
    if ev.ma_nguoi_dung != actor.ma_nd:
        raise forbidden("NOT_OWNER", "Chỉ chủ đánh giá mới được xác nhận")
    if ev.trang_thai != ES.PROVISIONAL:
        raise conflict("INVALID_EVALUATION_STATE", "Chỉ xác nhận bảng điểm tạm tính")
    k = db.get(KyKPI, ev.ma_ky)
    srcs = {t.ma_tieu_chi: t.nguon_du_lieu for _, t in config_rows(db, k)}
    for ct in db.scalars(select(ChiTietKPI).where(ChiTietKPI.ma_ky == ev.ma_ky, ChiTietKPI.ma_nguoi_dung == ev.ma_nguoi_dung)):
        ct.gia_tri_xac_nhan = effective(ct, srcs[ct.ma_tieu_chi])
    ev.trang_thai, ev.ngay_xac_nhan = ES.MEMBER_CONFIRMED, today()
    audit(db, actor.ma_nd, "KPI_CONFIRMED", "danh_gia_kpi", ev.ma_nguoi_dung, ma_da=k.ma_du_an)
    return ev


def decide(db, actor, ev: DanhGiaKPI, approve: bool, note: str | None) -> DanhGiaKPI:
    k = db.get(KyKPI, ev.ma_ky)
    if ev.ma_nguoi_dung == actor.ma_nd:
        raise forbidden("SELF_APPROVAL", "Không được tự phê duyệt KPI của chính mình")
    if not can_manage(db, actor, k, ev.ma_nguoi_dung):
        raise forbidden()
    if not db.get(QuanLy, actor.ma_nd):
        raise forbidden("MANAGER_ONLY", "Chỉ QUẢN LÝ mới phê duyệt KPI (ERD: QUẢN LÝ –Phê duyệt– ĐÁNH GIÁ KPI)")
    if ev.trang_thai != ES.MEMBER_CONFIRMED:
        raise conflict("INVALID_EVALUATION_STATE", "Chỉ duyệt khi thành viên đã xác nhận kết quả")
    if not approve and not (note or "").strip():
        raise invalid("COMMENT_REQUIRED", "Từ chối phải kèm nhận xét")
    ev.trang_thai = ES.APPROVED if approve else ES.REJECTED
    ev.ma_nguoi_duyet, ev.ngay_duyet, ev.nhan_xet = actor.ma_nd, today(), note
    audit(db, actor.ma_nd, "KPI_APPROVED" if approve else "KPI_REJECTED", "danh_gia_kpi", ev.ma_nguoi_dung, ma_da=k.ma_du_an)
    notify(db, ev.ma_nguoi_dung, "KPI_DECISION", f"Đánh giá KPI kỳ '{k.ten_ky}' đã được {'phê duyệt' if approve else 'từ chối'}", note)
    return ev


def close_period(db, actor, k: KyKPI):
    if k.trang_thai != KS.OPEN:
        raise conflict("PERIOD_NOT_OPEN", "Kỳ chưa mở hoặc đã đóng")
    n = db.scalar(select(func.count()).select_from(DanhGiaKPI).where(DanhGiaKPI.ma_ky == k.ma_ky, DanhGiaKPI.trang_thai != ES.APPROVED))
    if n:
        raise conflict("PENDING_EVALUATIONS", f"Còn {n} đánh giá chưa được phê duyệt")
    k.trang_thai = KS.CLOSED
    audit(db, actor.ma_nd, "KPI_PERIOD_CLOSED", "ky_kpi", k.ma_ky)
