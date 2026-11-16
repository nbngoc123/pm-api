from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, require_sys
from app.errors import not_found
from app.models import ChiSoDuAn, KeHoachGoc, NhatKyHeThong, Task, ThongBao
from app.schemas.common import Msg, Page
from app.schemas.progress import *
from app.services import progress as svc
from app.services.access import require_project_perm, require_task_perm
from app.services.common import get_or_404, paginate

router = APIRouter(tags=["3. Theo dõi tiến độ"])


@router.get("/projects/{ma_da}/progress/evm", summary="3.1 Chỉ số EVM (PV/EV/AC/SPI/CPI/EAC)")
def evm(ma_da: int, as_of: date | None = None, co_so: str = Query("chi_phi", pattern="^(chi_phi|gio)$"),
        user=Depends(current_user), db: Session = Depends(get_db)):
    return svc.compute_evm(db, require_project_perm(db, user, ma_da, "report.project"), as_of, co_so)


@router.get("/projects/{ma_da}/progress/burndown", summary="3.1 Biểu đồ Burn-down")
def burndown(ma_da: int, as_of: date | None = None, user=Depends(current_user), db: Session = Depends(get_db)):
    return svc.burndown(db, require_project_perm(db, user, ma_da, "report.project"), as_of)


@router.put("/tasks/{ma_cv}/baseline", response_model=BaselineOut, summary="Thiết lập kế hoạch gốc của task")
def set_baseline(ma_cv: int, body: BaselineIn, user=Depends(current_user), db: Session = Depends(get_db)):
    t, p = require_task_perm(db, user, ma_cv, "progress.manage")
    return svc.set_baseline(db, user, p, t, body)


@router.get("/projects/{ma_da}/baseline", response_model=list[BaselineOut])
def list_baseline(ma_da: int, user=Depends(current_user), db: Session = Depends(get_db)):
    require_project_perm(db, user, ma_da, "report.project")
    return db.scalars(select(KeHoachGoc).join(Task, Task.ma_cv == KeHoachGoc.ma_cv).where(Task.ma_du_an == ma_da)).all()


@router.post("/projects/{ma_da}/baseline/lock", summary="Khóa kế hoạch gốc (tự tạo baseline cho task chưa có)")
def lock(ma_da: int, user=Depends(current_user), db: Session = Depends(get_db)):
    p = require_project_perm(db, user, ma_da, "progress.manage")
    return {"so_task_duoc_khoa": svc.lock_baselines(db, user, p)}


@router.post("/projects/{ma_da}/progress/snapshots", response_model=SnapshotOut, status_code=201, summary="3.3 Lưu bản ghi chỉ số DA")
def snapshot(ma_da: int, as_of: date | None = None, user=Depends(current_user), db: Session = Depends(get_db)):
    return svc.take_snapshot(db, user, require_project_perm(db, user, ma_da, "progress.manage"), as_of)


@router.get("/projects/{ma_da}/progress/snapshots", response_model=list[SnapshotOut])
def snapshots(ma_da: int, user=Depends(current_user), db: Session = Depends(get_db)):
    require_project_perm(db, user, ma_da, "report.project")
    return db.scalars(select(ChiSoDuAn).where(ChiSoDuAn.ma_du_an == ma_da).order_by(ChiSoDuAn.ngay)).all()


@router.post("/alerts/scan", summary="3.2 Quét & sinh cảnh báo (cron gọi hằng ngày)")
def scan(as_of: date | None = None, user=Depends(require_sys("alert.run")), db: Session = Depends(get_db)):
    return svc.scan_alerts(db, as_of)


# ---- thông báo ----
@router.get("/me/notifications", response_model=Page[NotificationOut])
def my_notifications(chua_doc: bool = False, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
                     user=Depends(current_user), db: Session = Depends(get_db)):
    st = select(ThongBao).where(ThongBao.ma_nd == user.ma_nd).order_by(ThongBao.ma_tb.desc())
    if chua_doc:
        st = st.where(ThongBao.da_doc.is_(False))
    return paginate(db, st, page, size)


@router.post("/notifications/{ma_tb}/read", response_model=Msg)
def mark_read(ma_tb: int, user=Depends(current_user), db: Session = Depends(get_db)):
    n = db.get(ThongBao, ma_tb)
    if not n or n.ma_nd != user.ma_nd:
        raise not_found("NOTIFICATION_NOT_FOUND", "Thông báo không tồn tại")
    n.da_doc = True
    return Msg()


@router.post("/me/notifications/read-all", response_model=Msg)
def read_all(user=Depends(current_user), db: Session = Depends(get_db)):
    db.execute(update(ThongBao).where(ThongBao.ma_nd == user.ma_nd, ThongBao.da_doc.is_(False)).values(da_doc=True))
    return Msg()


# ---- 3.3 nhật ký hệ thống ----
@router.get("/audit-logs", response_model=Page[AuditOut], summary="3.3 Nhật ký truy vết thay đổi")
def audit_logs(ma_da: int | None = None, loai_su_kien: str | None = None, doi_tuong: str | None = None, ma_doi_tuong: int | None = None,
               ma_nguoi_thuc_hien: int | None = None, page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=200),
               user=Depends(require_sys("audit.read")), db: Session = Depends(get_db)):
    st = select(NhatKyHeThong).order_by(NhatKyHeThong.ma_log.desc())
    if ma_da: st = st.where(NhatKyHeThong.ma_du_an == ma_da)
    if loai_su_kien: st = st.where(NhatKyHeThong.loai_su_kien == loai_su_kien)
    if doi_tuong: st = st.where(NhatKyHeThong.doi_tuong == doi_tuong)
    if ma_doi_tuong: st = st.where(NhatKyHeThong.ma_doi_tuong == ma_doi_tuong)
    if ma_nguoi_thuc_hien: st = st.where(NhatKyHeThong.ma_nguoi_thuc_hien == ma_nguoi_thuc_hien)
    return paginate(db, st, page, size)
