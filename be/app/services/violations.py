from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import TrangThaiKy, TrangThaiViPham as VS
from app.errors import conflict, forbidden, invalid
from app.models import (DuAn, GiaiTrinh, KyKPI, NhanVien, QuanLy, QuyDinhViPham, Task, ViPham)
from app.schemas.common import D
from app.security import utcnow
from app.services.access import is_direct_manager, membership, project_perms
from app.services.common import audit, notify, today
from app.services.projects import ensure_writable


def rule_active(r: QuyDinhViPham, d: date) -> bool:
    return r.tu_ngay <= d and (r.den_ngay is None or r.den_ngay >= d)


def vp_out(db, v: ViPham) -> dict:
    r = db.get(QuyDinhViPham, v.ma_qd)
    g = db.scalars(select(GiaiTrinh).where(GiaiTrinh.ma_vp == v.ma_vp).order_by(GiaiTrinh.ma_gt)).all()
    o = {c: getattr(v, c) for c in ("ma_vp", "ma_cv", "ma_nd", "ma_nguoi_lap", "ma_qd", "noi_dung", "trang_thai", "thoi_diem",
                                     "han_giai_trinh", "ngay_xu_ly", "ket_luan", "ma_nguoi_xu_ly", "ma_ky_ap_dung")}
    o["diem_tru"] = float(r.diem_tru) if r else None
    o["giai_trinh"] = g
    return o


def create(db: Session, actor, p: DuAn, t: Task, d) -> ViPham:
    # vi phạm vẫn có thể ghi nhận sau khi dự án hoàn thành (không gọi ensure_writable)
    if d.ma_nd == actor.ma_nd:
        raise invalid("SELF_VIOLATION", "Không thể tự lập biên bản vi phạm cho chính mình")
    if not membership(db, p.ma_du_an, d.ma_nd):
        raise invalid("NOT_PROJECT_MEMBER", "Người vi phạm phải là thành viên dự án")
    if not db.get(NhanVien, d.ma_nd):
        raise invalid("VIOLATOR_MUST_BE_EMPLOYEE", "Chỉ NHÂN VIÊN mới bị ghi nhận vi phạm (ERD: NHÂN VIÊN –Bị ghi nhận– VI PHẠM)")
    r = db.get(QuyDinhViPham, d.ma_qd)
    if not r:
        raise invalid("RULE_NOT_FOUND", "Quy định vi phạm không tồn tại")
    if not rule_active(r, today()):
        raise invalid("RULE_NOT_ACTIVE", "Quy định không còn hiệu lực")
    if db.scalar(select(ViPham.ma_vp).where(ViPham.ma_cv == t.ma_cv, ViPham.ma_nd == d.ma_nd, ViPham.ma_qd == d.ma_qd,
                                            ViPham.trang_thai != VS.DISMISSED)):
        raise conflict("DUPLICATE_VIOLATION", "Vi phạm tương tự đã được ghi nhận cho công việc này")
    v = ViPham(ma_cv=t.ma_cv, ma_nd=d.ma_nd, ma_nguoi_lap=actor.ma_nd, ma_qd=d.ma_qd, noi_dung=d.noi_dung)
    db.add(v); db.flush()
    audit(db, actor.ma_nd, "VIOLATION_CREATED", "vi_pham", v.ma_vp, r.ten_quy_dinh)
    return v


def send_for_explanation(db, actor, v: ViPham) -> ViPham:
    if v.trang_thai != VS.DRAFT:
        raise conflict("INVALID_VIOLATION_STATE", "Chỉ gửi giải trình từ hồ sơ dự thảo")
    v.trang_thai = VS.PENDING_EXPLANATION
    v.han_giai_trinh = utcnow() + timedelta(days=settings.explanation_days)
    audit(db, actor.ma_nd, "VIOLATION_NOTIFIED", "vi_pham", v.ma_vp)
    notify(db, v.ma_nd, "VIOLATION_NOTICE", "Bạn có vi phạm cần giải trình",
           f"Hạn giải trình: {v.han_giai_trinh:%Y-%m-%d %H:%M} UTC", ma_cv=v.ma_cv)
    return v


def explain(db, actor, v: ViPham, d) -> GiaiTrinh:
    if v.ma_nd != actor.ma_nd:
        raise forbidden("NOT_VIOLATOR", "Chỉ người bị lập biên bản mới được giải trình")
    if v.trang_thai not in (VS.PENDING_EXPLANATION, VS.EXPLAINED):       # ERD: GIẢI TRÌNH N–1 VI PHẠM ⇒ được bổ sung nhiều đơn
        raise conflict("INVALID_VIOLATION_STATE", "Vi phạm không ở trạng thái chờ giải trình")
    if v.han_giai_trinh and v.han_giai_trinh < utcnow():
        raise conflict("EXPLANATION_DEADLINE_PASSED", "Đã quá hạn giải trình")
    g = GiaiTrinh(ma_vp=v.ma_vp, noi_dung=d.noi_dung, duong_dan_bang_chung=d.duong_dan_bang_chung); db.add(g)
    v.trang_thai = VS.EXPLAINED
    db.flush()
    audit(db, actor.ma_nd, "VIOLATION_EXPLAINED", "vi_pham", v.ma_vp)
    notify(db, v.ma_nguoi_lap, "EXPLANATION_SUBMITTED", "Thành viên đã gửi giải trình", ma_cv=v.ma_cv)
    return g


def find_period(db, ma_da: int, d: date) -> KyKPI | None:
    return db.scalar(select(KyKPI).where(KyKPI.ma_du_an == ma_da, KyKPI.trang_thai == TrangThaiKy.OPEN,
                                         KyKPI.tu_ngay <= d, KyKPI.den_ngay >= d).order_by(KyKPI.ma_ky))


def conclude(db, actor, p: DuAn, v: ViPham, d) -> ViPham:
    perms = project_perms(db, actor, p.ma_du_an)
    if "violation.conclude" not in perms and not is_direct_manager(db, actor.ma_nd, v.ma_nd):
        raise forbidden()
    if not db.get(QuanLy, actor.ma_nd):
        raise forbidden("MANAGER_ONLY", "Chỉ QUẢN LÝ mới kết luận vi phạm (ERD: QUẢN LÝ –Kết luận– VI PHẠM)")
    if v.ma_nd == actor.ma_nd:
        raise forbidden("SELF_CONCLUDE", "Không được kết luận vi phạm của chính mình")
    expired = v.trang_thai == VS.PENDING_EXPLANATION and v.han_giai_trinh and v.han_giai_trinh < utcnow()
    ok = v.trang_thai == VS.EXPLAINED or expired or (v.trang_thai == VS.DRAFT and d.ket_luan == "DISMISSED")
    if not ok:
        raise conflict("INVALID_VIOLATION_STATE", "Chỉ kết luận khi đã giải trình hoặc quá hạn giải trình")
    ky = None
    if d.ket_luan == "CONFIRMED":
        if d.ma_ky_ap_dung is not None:
            ky = db.get(KyKPI, d.ma_ky_ap_dung)
            if not ky or ky.ma_du_an != p.ma_du_an:
                raise invalid("INVALID_PERIOD", "Kỳ KPI không thuộc dự án")
            if ky.trang_thai == TrangThaiKy.CLOSED:
                raise conflict("PERIOD_CLOSED", "Kỳ KPI đã đóng")
        else:
            ky = find_period(db, p.ma_du_an, (v.thoi_diem + timedelta(hours=settings.tz_offset_hours)).date())
    v.trang_thai = VS.CONFIRMED if d.ket_luan == "CONFIRMED" else VS.DISMISSED
    v.ket_luan, v.ngay_xu_ly, v.ma_nguoi_xu_ly = d.ghi_chu, today(), actor.ma_nd
    v.ma_ky_ap_dung = ky.ma_ky if ky else None
    audit(db, actor.ma_nd, "VIOLATION_CONCLUDED", "vi_pham", v.ma_vp, d.ket_luan)
    msg = "Vi phạm đã có kết luận: " + ("xử phạt" if d.ket_luan == "CONFIRMED" else "bác bỏ")
    notify(db, v.ma_nd, "VIOLATION_CONCLUDED", msg, d.ghi_chu, ma_cv=v.ma_cv)           # DFD 5.2 → Thành viên: Biên bản lỗi, Lệnh xử phạt
    if v.ma_nguoi_lap != v.ma_nd:
        notify(db, v.ma_nguoi_lap, "VIOLATION_CONCLUDED", msg, d.ghi_chu, ma_cv=v.ma_cv)  # DFD mức 0: Trưởng nhóm cũng nhận Biên bản lỗi, Lệnh xử phạt
    return v
