from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import TrangThaiDuAn, TrangThaiTask as TS
from app.errors import conflict, invalid
from app.models import (ChiSoDuAn, DuAn, KeHoachGoc, NhanVien, NhatKyGioLam, PhanCong, Task, ThanhVienDuAn, VaiTro)
from app.schemas.common import D
from app.security import utcnow
from app.services.common import audit, f, notify, today
from app.services.projects import OPEN_TASK, ensure_writable
from app.services.tasks import assignees


def _frac(start: date, end: date, as_of: date) -> float:
    if as_of >= end: return 1.0
    if as_of < start: return 0.0
    return ((as_of - start).days + 1) / ((end - start).days + 1)


def compute_evm(db: Session, p: DuAn, as_of: date | None = None, co_so: str = "chi_phi") -> dict:
    """co_so = "chi_phi" | "gio": tham số tính toán tiến độ do Quản lý dự án chọn (DFD 3.1)."""
    as_of = as_of or today()
    hours = co_so == "gio"
    rows = db.execute(select(Task, KeHoachGoc).join(KeHoachGoc, KeHoachGoc.ma_cv == Task.ma_cv)
                      .where(Task.ma_du_an == p.ma_du_an, Task.trang_thai != TS.CANCELLED)).all()
    bac = pv = ev = 0.0
    hours_plan = 0.0
    for t, b in rows:
        c = float(b.gio_du_kien_goc if hours else b.chi_phi_ke_hoach_goc)
        bac += c; hours_plan += float(b.gio_du_kien_goc)
        pv += c * _frac(b.ngay_bat_dau_goc, b.ngay_ket_thuc_goc, as_of)
        ev += c * (100 if t.trang_thai == TS.DONE else t.ty_le_hoan_thanh) / 100
    ac, hrs = db.execute(select(func.coalesce(func.sum(NhatKyGioLam.chi_phi_thuc_te), 0), func.coalesce(func.sum(NhatKyGioLam.so_gio), 0))
                         .join(Task, Task.ma_cv == NhatKyGioLam.ma_cv).where(Task.ma_du_an == p.ma_du_an)).one()
    ac, hrs = float(hrs if hours else ac), float(hrs)
    no_base = db.scalar(select(func.count()).select_from(Task).outerjoin(KeHoachGoc, KeHoachGoc.ma_cv == Task.ma_cv).where(
        Task.ma_du_an == p.ma_du_an, Task.trang_thai != TS.CANCELLED, KeHoachGoc.ma_cv.is_(None)))
    spi = ev / pv if pv > 0 else None
    cpi = ev / ac if ac > 0 else None
    eac = bac / cpi if cpi else None
    health = "GREY"
    vals = [x for x in (spi, cpi) if x is not None]
    if vals:
        m = min(vals); health = "RED" if m < 0.8 else "AMBER" if m < 0.95 else "GREEN"
    return {"as_of": as_of.isoformat(), "bac": f(bac), "pv": f(pv), "ev": f(ev), "ac": f(ac), "sv": f(ev - pv), "cv": f(ev - ac),
            "spi": None if spi is None else round(spi, 3), "cpi": None if cpi is None else round(cpi, 3),
            "eac": f(eac), "etc": None if eac is None else f(eac - ac), "vac": None if eac is None else f(bac - eac),
            "co_so": co_so, "gio_ke_hoach": f(hours_plan), "gio_thuc_te": f(hrs), "so_task_co_baseline": len(rows),
            "so_task_chua_co_baseline": no_base, "suc_khoe": health}


def burndown(db: Session, p: DuAn, as_of: date | None = None) -> dict:
    as_of = as_of or today()
    tasks = db.scalars(select(Task).where(Task.ma_du_an == p.ma_du_an, Task.trang_thai != TS.CANCELLED)).all()
    effort = lambda t: float(t.gio_du_kien) or 0.0
    total = sum(effort(t) for t in tasks)
    unit = "gio"
    if total == 0:
        total, unit, effort = float(len(tasks)), "task", (lambda t: 1.0)
    start, end = p.ngay_bat_dau, p.ngay_ket_thuc_du_kien
    n = min((end - start).days + 1, 731)
    done = [(t.hoan_thanh_luc + timedelta(hours=settings.tz_offset_hours)).date() for t in tasks if t.hoan_thanh_luc and t.trang_thai == TS.DONE]
    done_eff = [effort(t) for t in tasks if t.hoan_thanh_luc and t.trang_thai == TS.DONE]
    pts = []
    for i in range(n):
        d = start + timedelta(days=i)
        ideal = total * (1 - i / (n - 1)) if n > 1 else 0.0
        actual = None
        if d <= as_of:
            actual = total - sum(e for dd, e in zip(done, done_eff) if dd <= d)
        pts.append({"ngay": d.isoformat(), "ly_tuong": round(ideal, 2), "thuc_te": None if actual is None else round(actual, 2)})
    return {"don_vi": unit, "tong_khoi_luong": round(total, 2), "diem": pts}


def set_baseline(db, actor, p: DuAn, t: Task, d) -> KeHoachGoc:
    ensure_writable(p)
    b = db.get(KeHoachGoc, t.ma_cv)
    if b and b.khoa_luc:
        raise conflict("BASELINE_LOCKED", "Kế hoạch gốc đã khóa, không thể thay đổi")
    if not b:
        b = KeHoachGoc(ma_cv=t.ma_cv); db.add(b)
    b.ngay_bat_dau_goc, b.ngay_ket_thuc_goc = d.ngay_bat_dau_goc, d.ngay_ket_thuc_goc
    b.gio_du_kien_goc, b.chi_phi_ke_hoach_goc = D(d.gio_du_kien_goc), D(d.chi_phi_ke_hoach_goc)
    db.flush()
    audit(db, actor.ma_nd, "BASELINE_SET", "task", t.ma_cv)
    return b


def avg_rate(db, ma_da) -> Decimal:
    r = db.scalar(select(func.avg(NhanVien.don_gia_gio)).join(ThanhVienDuAn, ThanhVienDuAn.ma_nguoi_dung == NhanVien.ma_nd)
                  .where(ThanhVienDuAn.ma_du_an == ma_da, NhanVien.don_gia_gio > 0))
    return D(r) if r else D(settings.default_hourly_rate)


def lock_baselines(db, actor, p: DuAn) -> int:
    ensure_writable(p)
    rate = avg_rate(db, p.ma_du_an)
    n = 0
    for t in db.scalars(select(Task).where(Task.ma_du_an == p.ma_du_an, Task.trang_thai != TS.CANCELLED)):
        b = db.get(KeHoachGoc, t.ma_cv)
        if not b:
            b = KeHoachGoc(ma_cv=t.ma_cv, ngay_bat_dau_goc=t.ngay_bat_dau_du_kien or p.ngay_bat_dau,
                           ngay_ket_thuc_goc=t.han_hoan_thanh or p.ngay_ket_thuc_du_kien, gio_du_kien_goc=t.gio_du_kien,
                           chi_phi_ke_hoach_goc=(t.gio_du_kien * rate).quantize(Decimal("0.01")))
            if b.ngay_ket_thuc_goc < b.ngay_bat_dau_goc:
                b.ngay_ket_thuc_goc = b.ngay_bat_dau_goc
            db.add(b)
        if not b.khoa_luc:
            b.khoa_luc = utcnow(); n += 1
    db.flush()
    audit(db, actor.ma_nd, "BASELINE_LOCKED", "du_an", p.ma_du_an, f"{n} task")
    return n


def take_snapshot(db, actor, p: DuAn, as_of: date | None = None) -> ChiSoDuAn:
    e = compute_evm(db, p, as_of)
    d = date.fromisoformat(e["as_of"])
    s = db.scalar(select(ChiSoDuAn).where(ChiSoDuAn.ma_du_an == p.ma_du_an, ChiSoDuAn.ngay == d))
    if not s:
        s = ChiSoDuAn(ma_du_an=p.ma_du_an, ngay=d); db.add(s)
    s.pv, s.ev, s.ac = D(e["pv"]), D(e["ev"]), D(e["ac"])
    s.spi = None if e["spi"] is None else D(e["spi"]); s.cpi = None if e["cpi"] is None else D(e["cpi"])
    db.flush()
    audit(db, actor.ma_nd if actor else None, "METRIC_SNAPSHOT", "du_an", p.ma_du_an)
    return s


def _leaders(db, ma_da) -> list[int]:
    return list(db.scalars(select(ThanhVienDuAn.ma_nguoi_dung).join(VaiTro, VaiTro.ma_vai_tro == ThanhVienDuAn.ma_vai_tro)
                           .where(ThanhVienDuAn.ma_du_an == ma_da, ThanhVienDuAn.trang_thai == "ACTIVE",
                                  VaiTro.code.in_(["TEAM_LEAD", "PM"]))))


def _team_leads(db, ma_da) -> list[int]:
    """DFD 3.2: "Cảnh báo trễ hạn cục bộ" gửi Trưởng nhóm; dự án chưa có Trưởng nhóm thì dự phòng gửi Quản lý dự án."""
    tl = list(db.scalars(select(ThanhVienDuAn.ma_nguoi_dung).join(VaiTro, VaiTro.ma_vai_tro == ThanhVienDuAn.ma_vai_tro)
                         .where(ThanhVienDuAn.ma_du_an == ma_da, ThanhVienDuAn.trang_thai == "ACTIVE", VaiTro.code == "TEAM_LEAD")))
    return tl or [db.get(DuAn, ma_da).ma_quan_ly]


def scan_alerts(db: Session, as_of: date | None = None) -> dict:
    """3.2 Cảnh báo rủi ro & tự động hóa. Idempotent nhờ dedupe_key – an toàn khi chạy cron nhiều lần/ngày."""
    t0 = as_of or today()
    rem = dl = delay = bud = 0
    q = select(Task, DuAn).join(DuAn, DuAn.ma_du_an == Task.ma_du_an).where(
        DuAn.trang_thai == TrangThaiDuAn.ACTIVE, Task.trang_thai.in_(OPEN_TASK), Task.han_hoan_thanh.is_not(None))
    for t, p in db.execute(q).all():
        days = (t.han_hoan_thanh - t0).days
        if 0 <= days <= settings.alert_deadline_days:
            for u in assignees(db, t.ma_cv):
                dl += notify(db, u, "DEADLINE_REMINDER", f"Công việc '{t.ten_cv}' sắp đến hạn ({t.han_hoan_thanh})", ma_cv=t.ma_cv,
                             dedupe=f"DL:{t.ma_cv}:{u}:{t.han_hoan_thanh}")
        elif days < 0:
            for u in _team_leads(db, p.ma_du_an):
                delay += notify(db, u, "DELAY_WARNING", f"Công việc '{t.ten_cv}' trễ hạn {-days} ngày", ma_cv=t.ma_cv,
                                dedupe=f"DELAY:{t.ma_cv}:{u}:{t0}")
    for p in db.scalars(select(DuAn).where(DuAn.trang_thai == TrangThaiDuAn.ACTIVE, DuAn.ngan_sach_gio > 0)):
        h = db.scalar(select(func.coalesce(func.sum(NhatKyGioLam.so_gio), 0)).join(Task, Task.ma_cv == NhatKyGioLam.ma_cv).where(Task.ma_du_an == p.ma_du_an))
        if h > p.ngan_sach_gio:
            bud += notify(db, p.ma_quan_ly, "BUDGET_EXCEEDED", f"Dự án '{p.ten_du_an}' vượt ngân sách giờ ({h}/{p.ngan_sach_gio})",
                          dedupe=f"BUDGET:{p.ma_du_an}:{t0}")
    audit(db, None, "ALERT_SCAN", None, None, f"dl={dl},delay={delay},budget={bud}")
    return {"nhac_deadline": dl, "canh_bao_tre_han": delay, "canh_bao_vuot_ngan_sach": bud}
