from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, require_sys
from app.enums import TrangThaiViPham
from app.errors import conflict, forbidden, not_found
from app.models import DuAn, QuyDinhViPham, Task, ViPham
from app.schemas.common import D, Msg, Page
from app.schemas.violation import *
from app.services import violations as svc
from app.services.access import is_direct_manager, project_perms, require_project_perm, require_task_perm
from app.services.common import audit, get_or_404, paginate

router = APIRouter(tags=["5. Vi phạm & chất lượng"])


# ---- quy định ----
@router.get("/violation-rules", response_model=list[RuleOut])
def list_rules(user=Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(QuyDinhViPham).order_by(QuyDinhViPham.ma_qd)).all()


@router.post("/violation-rules", response_model=RuleOut, status_code=201)
def create_rule(body: RuleIn, user=Depends(require_sys("violation.rule.manage")), db: Session = Depends(get_db)):
    r = QuyDinhViPham(ten_quy_dinh=body.ten_quy_dinh, diem_tru=D(body.diem_tru), tu_ngay=body.tu_ngay, den_ngay=body.den_ngay)
    db.add(r); db.flush()
    audit(db, user.ma_nd, "RULE_CREATED", "quy_dinh_vi_pham", r.ma_qd, r.ten_quy_dinh)
    return r


@router.patch("/violation-rules/{ma_qd}", response_model=RuleOut)
def update_rule(ma_qd: int, body: RuleUpdate, user=Depends(require_sys("violation.rule.manage")), db: Session = Depends(get_db)):
    from app.errors import invalid
    r = get_or_404(db, QuyDinhViPham, ma_qd, "RULE_NOT_FOUND")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        if v is not None or k == "den_ngay":
            setattr(r, k, D(v) if k == "diem_tru" else v)
    if r.den_ngay and r.den_ngay < r.tu_ngay:
        raise invalid("INVALID_DATE_RANGE", "den_ngay phải >= tu_ngay")
    audit(db, user.ma_nd, "RULE_UPDATED", "quy_dinh_vi_pham", r.ma_qd, ",".join(data))
    return r


@router.delete("/violation-rules/{ma_qd}", response_model=Msg)
def delete_rule(ma_qd: int, user=Depends(require_sys("violation.rule.manage")), db: Session = Depends(get_db)):
    r = get_or_404(db, QuyDinhViPham, ma_qd, "RULE_NOT_FOUND")
    if db.scalar(select(ViPham.ma_vp).where(ViPham.ma_qd == ma_qd).limit(1)):
        raise conflict("RULE_IN_USE", "Quy định đã được dùng trong biên bản, hãy đặt den_ngay để ngừng hiệu lực")
    db.delete(r)
    return Msg()


# ---- vi phạm ----
def _ctx(db, v: ViPham):
    t = db.get(Task, v.ma_cv)
    return t, t.ma_du_an


def _can_view(db, user, v: ViPham) -> bool:
    if user.ma_nd in (v.ma_nd, v.ma_nguoi_lap):
        return True
    perms = project_perms(db, user, db.get(Task, v.ma_cv).ma_du_an)
    return bool(perms & {"violation.conclude", "violation.create", "report.project"}) or is_direct_manager(db, user.ma_nd, v.ma_nd)


def _load(db, user, ma_vp) -> ViPham:
    v = get_or_404(db, ViPham, ma_vp, "VIOLATION_NOT_FOUND")
    if not _can_view(db, user, v):
        raise not_found("VIOLATION_NOT_FOUND", "Vi phạm không tồn tại")
    return v


@router.post("/violations", response_model=ViolationOut, status_code=201, summary="5.1 Ghi nhận & phân loại vi phạm (hồ sơ dự thảo)")
def create_violation(body: ViolationIn, user=Depends(current_user), db: Session = Depends(get_db)):
    t, p = require_task_perm(db, user, body.ma_cv, "violation.create")
    return svc.vp_out(db, svc.create(db, user, p, t, body))


@router.get("/violations", response_model=Page[ViolationOut])
def list_violations(ma_da: int | None = None, ma_nd: int | None = None, trang_thai: TrangThaiViPham | None = None,
                    page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
                    user=Depends(current_user), db: Session = Depends(get_db)):
    st = select(ViPham).join(Task, Task.ma_cv == ViPham.ma_cv).order_by(ViPham.ma_vp.desc())
    if ma_da and project_perms(db, user, ma_da) & {"violation.conclude", "violation.create", "report.project"}:
        st = st.where(Task.ma_du_an == ma_da)
    else:
        st = st.where(or_(ViPham.ma_nd == user.ma_nd, ViPham.ma_nguoi_lap == user.ma_nd))
        if ma_da:
            st = st.where(Task.ma_du_an == ma_da)
    if ma_nd: st = st.where(ViPham.ma_nd == ma_nd)
    if trang_thai: st = st.where(ViPham.trang_thai == trang_thai)
    r = paginate(db, st, page, size)
    r["items"] = [svc.vp_out(db, v) for v in r["items"]]
    return r


@router.get("/me/violations/pending", response_model=list[ViolationOut], summary="5.1 Danh sách chờ giải trình của tôi")
def my_pending(user=Depends(current_user), db: Session = Depends(get_db)):
    st = select(ViPham).where(ViPham.ma_nd == user.ma_nd, ViPham.trang_thai == TrangThaiViPham.PENDING_EXPLANATION).order_by(ViPham.han_giai_trinh)
    return [svc.vp_out(db, v) for v in db.scalars(st)]


@router.get("/violations/{ma_vp}", response_model=ViolationOut)
def get_violation(ma_vp: int, user=Depends(current_user), db: Session = Depends(get_db)):
    return svc.vp_out(db, _load(db, user, ma_vp))


@router.post("/violations/{ma_vp}/notify", response_model=ViolationOut, summary="5.1 Gửi thông báo & yêu cầu giải trình")
def notify_violator(ma_vp: int, user=Depends(current_user), db: Session = Depends(get_db)):
    v = _load(db, user, ma_vp)
    t, ma_da = _ctx(db, v)
    require_project_perm(db, user, ma_da, "violation.create")
    return svc.vp_out(db, svc.send_for_explanation(db, user, v))


@router.post("/violations/{ma_vp}/explanations", response_model=ExplanationOut, status_code=201, summary="5.2 Nộp đơn giải trình & bằng chứng")
def explain(ma_vp: int, body: ExplainIn, user=Depends(current_user), db: Session = Depends(get_db)):
    v = get_or_404(db, ViPham, ma_vp, "VIOLATION_NOT_FOUND")
    if v.ma_nd != user.ma_nd:
        raise not_found("VIOLATION_NOT_FOUND", "Vi phạm không tồn tại")
    return svc.explain(db, user, v, body)


@router.post("/violations/{ma_vp}/conclude", response_model=ViolationOut, summary="5.2 Kết luận xử lý vi phạm (Biên bản lỗi, Lệnh xử phạt)")
def conclude(ma_vp: int, body: ConcludeIn, user=Depends(current_user), db: Session = Depends(get_db)):
    v = _load(db, user, ma_vp)
    t, ma_da = _ctx(db, v)
    p = db.get(DuAn, ma_da)   # người quản lý trực tiếp có thể không phải thành viên dự án
    return svc.vp_out(db, svc.conclude(db, user, p, v, body))
