from datetime import date, timedelta

from app.config import settings

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import not_found
from app.models import NhatKyHeThong, ThongBao
from app.security import utcnow


def _project_of(db: Session, obj, obj_id):
    from app.models import Epic, KyKPI, MocDuAn, NhatKyGioLam, Task, ViPham
    if obj_id is None or obj is None:
        return None
    if obj == "du_an":
        return obj_id
    simple = {"task": Task, "moc_du_an": MocDuAn, "epic": Epic, "ky_kpi": KyKPI}
    if obj in simple:
        o = db.get(simple[obj], obj_id)
        return o.ma_du_an if o else None
    if obj in ("vi_pham", "nhat_ky_gio_lam"):
        o = db.get(ViPham if obj == "vi_pham" else NhatKyGioLam, obj_id)
        t = db.get(Task, o.ma_cv) if o else None
        return t.ma_du_an if t else None
    return None


def audit(db: Session, user_id, event: str, obj: str | None = None, obj_id: int | None = None,
          content: str | None = None, ma_da: int | None = None):
    """Ghi nhật ký; tự suy ra dự án phát sinh sự kiện (nếu có) để thỏa quan hệ DỰ ÁN–NHẬT KÝ HỆ THỐNG."""
    db.add(NhatKyHeThong(ma_nguoi_thuc_hien=user_id, loai_su_kien=event, doi_tuong=obj, ma_doi_tuong=obj_id,
                         noi_dung=content, thoi_diem=utcnow(), ma_du_an=ma_da or _project_of(db, obj, obj_id)))


def notify(db: Session, ma_nd: int, loai: str, tieu_de: str, noi_dung: str | None = None,
           ma_cv: int | None = None, dedupe: str | None = None) -> bool:
    if dedupe and db.scalar(select(ThongBao.ma_tb).where(ThongBao.dedupe_key == dedupe)):
        return False
    db.add(ThongBao(ma_nd=ma_nd, loai=loai, tieu_de=tieu_de, noi_dung=noi_dung, ma_cv=ma_cv, dedupe_key=dedupe))
    db.flush()
    return True


def paginate(db: Session, stmt, page: int, size: int):
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = db.scalars(stmt.limit(size).offset((page - 1) * size)).all()
    return {"items": items, "total": total, "page": page, "size": size}


def get_or_404(db: Session, model, pk, code="NOT_FOUND"):
    obj = db.get(model, pk)
    if not obj:
        raise not_found(code, f"{model.__name__} #{pk} không tồn tại")
    return obj


def today() -> date:
    return (utcnow() + timedelta(hours=settings.tz_offset_hours)).date()


def f(x) -> float | None:
    return None if x is None else round(float(x), 2)
