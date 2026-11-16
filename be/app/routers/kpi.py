from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, require_sys
from app.enums import TrangThaiDanhGia
from app.errors import conflict, forbidden, not_found
from app.models import CauHinhKPI, ChiTietKPI, DanhGiaKPI, KyKPI, TieuChiKPI
from app.schemas.common import Msg
from app.schemas.kpi import *
from app.services import kpi as svc
from app.services.access import is_direct_manager, project_perms, require_project_perm, system_role_code
from app.services.common import audit, get_or_404

router = APIRouter(tags=["4. Quản lý KPI"])


# ---- tiêu chí ----
@router.get("/kpi/criteria", response_model=list[CriterionOut])
def list_criteria(user=Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(TieuChiKPI).order_by(TieuChiKPI.ma_tieu_chi)).all()


@router.post("/kpi/criteria", response_model=CriterionOut, status_code=201, summary="4.1 Tạo tiêu chí KPI")
def create_criterion(body: CriterionIn, user=Depends(require_sys("kpi.criteria.manage")), db: Session = Depends(get_db)):
    return svc.create_criterion(db, user, body)


@router.patch("/kpi/criteria/{ma_tc}", response_model=CriterionOut)
def update_criterion(ma_tc: int, body: CriterionUpdate, user=Depends(require_sys("kpi.criteria.manage")), db: Session = Depends(get_db)):
    c = get_or_404(db, TieuChiKPI, ma_tc, "CRITERION_NOT_FOUND")
    if body.nguon_du_lieu and body.nguon_du_lieu != c.nguon_du_lieu and db.scalar(select(CauHinhKPI.ma_ky).where(CauHinhKPI.ma_tieu_chi == ma_tc).limit(1)):
        raise conflict("CRITERION_IN_USE", "Tiêu chí đã dùng trong kỳ KPI, không thể đổi nguồn dữ liệu")
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(c, k, v)
    audit(db, user.ma_nd, "KPI_CRITERION_UPDATED", "tieu_chi_kpi", c.ma_tieu_chi)
    return c


@router.delete("/kpi/criteria/{ma_tc}", response_model=Msg)
def delete_criterion(ma_tc: int, user=Depends(require_sys("kpi.criteria.manage")), db: Session = Depends(get_db)):
    c = get_or_404(db, TieuChiKPI, ma_tc, "CRITERION_NOT_FOUND")
    if db.scalar(select(CauHinhKPI.ma_ky).where(CauHinhKPI.ma_tieu_chi == ma_tc).limit(1)):
        raise conflict("CRITERION_IN_USE", "Tiêu chí đã dùng trong kỳ KPI")
    db.delete(c)
    return Msg()


# ---- kỳ ----
def _period(db, user, ma_ky, perm):
    k = get_or_404(db, KyKPI, ma_ky, "PERIOD_NOT_FOUND")
    return k, require_project_perm(db, user, k.ma_du_an, perm)


@router.get("/projects/{ma_da}/kpi/periods", response_model=list[PeriodOut])
def list_periods(ma_da: int, user=Depends(current_user), db: Session = Depends(get_db)):
    require_project_perm(db, user, ma_da, "project.read")
    return db.scalars(select(KyKPI).where(KyKPI.ma_du_an == ma_da).order_by(KyKPI.tu_ngay)).all()


@router.post("/projects/{ma_da}/kpi/periods", response_model=PeriodOut, status_code=201, summary="4.1 Tạo kỳ KPI")
def create_period(ma_da: int, body: PeriodIn, user=Depends(current_user), db: Session = Depends(get_db)):
    return svc.create_period(db, user, require_project_perm(db, user, ma_da, "kpi.period.manage"), body)


@router.get("/kpi/periods/{ma_ky}", response_model=PeriodOut)
def get_period(ma_ky: int, user=Depends(current_user), db: Session = Depends(get_db)):
    return _period(db, user, ma_ky, "project.read")[0]


@router.put("/kpi/periods/{ma_ky}/config", response_model=ConfigOut, summary="4.1 Cấu hình & phân bổ KPI (tiêu chí, trọng số, chỉ tiêu)")
def set_config(ma_ky: int, body: ConfigIn, user=Depends(current_user), db: Session = Depends(get_db)):
    k, _ = _period(db, user, ma_ky, "kpi.period.manage")
    svc.set_config(db, user, k, body)
    return svc.config_out(db, k)


@router.get("/kpi/periods/{ma_ky}/config", response_model=ConfigOut)
def get_config(ma_ky: int, user=Depends(current_user), db: Session = Depends(get_db)):
    return svc.config_out(db, _period(db, user, ma_ky, "project.read")[0])


@router.post("/kpi/periods/{ma_ky}/open", summary="Mở kỳ: tạo bảng đánh giá cho thành viên")
def open_period(ma_ky: int, user=Depends(current_user), db: Session = Depends(get_db)):
    k, _ = _period(db, user, ma_ky, "kpi.period.manage")
    return {"so_danh_gia_tao_moi": svc.open_period(db, user, k)}


@router.post("/kpi/periods/{ma_ky}/sync-members", summary="Bổ sung đánh giá cho thành viên mới")
def sync(ma_ky: int, user=Depends(current_user), db: Session = Depends(get_db)):
    k, _ = _period(db, user, ma_ky, "kpi.period.manage")
    return {"so_danh_gia_tao_moi": svc.sync_members(db, user, k)}


@router.put("/kpi/periods/{ma_ky}/manual-inputs", summary="4.2 Nhập hiệu suất thô (tiêu chí MANUAL) – Quản lý")
def manual(ma_ky: int, body: ManualIn, user=Depends(current_user), db: Session = Depends(get_db)):
    k, _ = _period(db, user, ma_ky, "project.read")
    return {"so_gia_tri_cap_nhat": svc.set_manual(db, user, k, body.items)}


@router.post("/kpi/periods/{ma_ky}/calculate", summary="4.2 Thu thập & tính toán tự động → bảng điểm tạm tính")
def calculate(ma_ky: int, user=Depends(current_user), db: Session = Depends(get_db)):
    k, _ = _period(db, user, ma_ky, "kpi.period.manage")
    return svc.calculate(db, user, k)


@router.post("/kpi/periods/{ma_ky}/close", response_model=PeriodOut, summary="Đóng kỳ KPI")
def close_period(ma_ky: int, user=Depends(current_user), db: Session = Depends(get_db)):
    k, _ = _period(db, user, ma_ky, "kpi.period.manage")
    svc.close_period(db, user, k)
    return k


@router.get("/kpi/periods/{ma_ky}/evaluations", response_model=list[EvaluationOut])
def list_evaluations(ma_ky: int, user=Depends(current_user), db: Session = Depends(get_db)):
    k, p = _period(db, user, ma_ky, "project.read")
    st = select(DanhGiaKPI).where(DanhGiaKPI.ma_ky == ma_ky).order_by(DanhGiaKPI.ma_nguoi_dung)
    if not (project_perms(db, user, p.ma_du_an) & {"kpi.approve", "kpi.period.manage", "report.project"}):
        st = st.where(DanhGiaKPI.ma_nguoi_dung == user.ma_nd)
    return [svc.eval_out(db, e) for e in db.scalars(st)]


# ---- 4.3 đánh giá ----
def _eval(db, user, ma_ky, ma_nd) -> DanhGiaKPI:
    ev = db.get(DanhGiaKPI, (ma_ky, ma_nd))          # khóa ghép theo ERD: (Mã kỳ, Mã người dùng)
    if not ev:
        raise not_found("EVALUATION_NOT_FOUND", "Đánh giá không tồn tại")
    k = db.get(KyKPI, ev.ma_ky)
    perms = project_perms(db, user, k.ma_du_an)
    if ev.ma_nguoi_dung != user.ma_nd and not (perms & {"kpi.approve", "kpi.period.manage", "report.project"}) \
            and not is_direct_manager(db, user.ma_nd, ev.ma_nguoi_dung):
        raise not_found("EVALUATION_NOT_FOUND", "Đánh giá không tồn tại")
    return ev


@router.get("/kpi/periods/{ma_ky}/evaluations/{ma_nd}", response_model=EvaluationOut)
def get_eval(ma_ky: int, ma_nd: int, user=Depends(current_user), db: Session = Depends(get_db)):
    return svc.eval_out(db, _eval(db, user, ma_ky, ma_nd))


@router.post("/kpi/periods/{ma_ky}/evaluations/{ma_nd}/confirm", response_model=EvaluationOut, summary="4.3 Thành viên xác nhận kết quả")
def confirm(ma_ky: int, ma_nd: int, user=Depends(current_user), db: Session = Depends(get_db)):
    return svc.eval_out(db, svc.confirm(db, user, _eval(db, user, ma_ky, ma_nd)))


@router.post("/kpi/periods/{ma_ky}/evaluations/{ma_nd}/approve", response_model=EvaluationOut, summary="4.3 Quản lý phê duyệt KPI")
def approve(ma_ky: int, ma_nd: int, body: DecisionIn | None = None, user=Depends(current_user), db: Session = Depends(get_db)):
    return svc.eval_out(db, svc.decide(db, user, _eval(db, user, ma_ky, ma_nd), True, body.nhan_xet if body else None))


@router.post("/kpi/periods/{ma_ky}/evaluations/{ma_nd}/reject", response_model=EvaluationOut, summary="4.3 Quản lý từ chối (yêu cầu tính lại)")
def reject(ma_ky: int, ma_nd: int, body: DecisionIn, user=Depends(current_user), db: Session = Depends(get_db)):
    return svc.eval_out(db, svc.decide(db, user, _eval(db, user, ma_ky, ma_nd), False, body.nhan_xet))


@router.get("/me/kpi", response_model=list[EvaluationOut], summary="KPI của tôi (mọi kỳ)")
def my_kpi(user=Depends(current_user), db: Session = Depends(get_db)):
    st = select(DanhGiaKPI).where(DanhGiaKPI.ma_nguoi_dung == user.ma_nd).order_by(DanhGiaKPI.ma_ky.desc())
    return [svc.eval_out(db, e) for e in db.scalars(st)]


@router.get("/kpi/users/{ma_nd}/history", summary="Lịch sử KPI cũ của một người")
def history(ma_nd: int, user=Depends(current_user), db: Session = Depends(get_db)):
    sysrole = system_role_code(db, user)
    if ma_nd != user.ma_nd and sysrole not in ("ADMIN", "DIRECTOR") and not is_direct_manager(db, user.ma_nd, ma_nd):
        raise forbidden()
    rows = db.execute(select(DanhGiaKPI, KyKPI).join(KyKPI, KyKPI.ma_ky == DanhGiaKPI.ma_ky).where(
        DanhGiaKPI.ma_nguoi_dung == ma_nd, DanhGiaKPI.trang_thai == TrangThaiDanhGia.APPROVED).order_by(KyKPI.tu_ngay)).all()
    return [{"ma_ky": k.ma_ky, "ma_du_an": k.ma_du_an, "ten_ky": k.ten_ky, "tu_ngay": k.tu_ngay, "den_ngay": k.den_ngay,
             "diem_tong": float(e.diem_tong or 0), "diem_tru": float(e.diem_tru or 0), "ngay_duyet": e.ngay_duyet} for e, k in rows]
