from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user
from app.enums import TrangThaiPhanCong, TrangThaiTask, UuTien
from app.errors import forbidden, not_found
from app.models import (Epic, NguoiDung, NhatKyGioLam, PhanCong, SubTask, Task, TepDinhKem, XetDuyetCongViec)
from app.schemas.common import Msg, Page
from app.schemas.task import *
from app.security import utcnow
from app.services import tasks as svc
from app.services.access import project_perms, require_project_perm, require_task_perm
from app.services.common import audit, get_or_404, paginate, today
from app.services.projects import ensure_writable

router = APIRouter(tags=["2. Quản lý công việc"])


# ---------- Epic ----------
@router.get("/projects/{ma_da}/epics", response_model=list[EpicOut])
def list_epics(ma_da: int, user=Depends(current_user), db: Session = Depends(get_db)):
    require_project_perm(db, user, ma_da, "project.read")
    return db.scalars(select(Epic).where(Epic.ma_du_an == ma_da).order_by(Epic.ma_epic)).all()


@router.post("/projects/{ma_da}/epics", response_model=EpicOut, status_code=201)
def create_epic(ma_da: int, body: EpicIn, user=Depends(current_user), db: Session = Depends(get_db)):
    p = require_project_perm(db, user, ma_da, "task.create"); ensure_writable(p)
    e = Epic(ma_du_an=ma_da, ten_epic=body.ten_epic, mo_ta=body.mo_ta); db.add(e); db.flush()
    audit(db, user.ma_nd, "EPIC_CREATED", "epic", e.ma_epic, e.ten_epic)
    return e


@router.delete("/projects/{ma_da}/epics/{ma_epic}", response_model=Msg)
def delete_epic(ma_da: int, ma_epic: int, user=Depends(current_user), db: Session = Depends(get_db)):
    from app.errors import conflict
    p = require_project_perm(db, user, ma_da, "task.update"); ensure_writable(p)
    e = db.get(Epic, ma_epic)
    if not e or e.ma_du_an != ma_da:
        raise not_found("EPIC_NOT_FOUND", "Epic không tồn tại")
    if db.scalar(select(func.count()).select_from(Task).where(Task.ma_epic == ma_epic)):
        raise conflict("EPIC_HAS_TASKS", "Epic đang có công việc")
    db.delete(e)
    return Msg()


# ---------- Task ----------
@router.post("/projects/{ma_da}/tasks", response_model=TaskOut, status_code=201, summary="2.1 Tạo công việc")
def create_task(ma_da: int, body: TaskCreate, user=Depends(current_user), db: Session = Depends(get_db)):
    p = require_project_perm(db, user, ma_da, "task.create")
    return svc.task_out(db, svc.create_task(db, user, p, body))


@router.get("/projects/{ma_da}/tasks", response_model=Page[TaskOut])
def list_tasks(ma_da: int, trang_thai: TrangThaiTask | None = None, uu_tien: UuTien | None = None,
               ma_nd: int | None = Query(None, description="lọc theo người được giao"), ma_moc: int | None = None,
               ma_epic: int | None = None, q: str | None = None, tre_han: bool | None = None,
               page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
               user=Depends(current_user), db: Session = Depends(get_db)):
    require_project_perm(db, user, ma_da, "project.read")
    st = select(Task).where(Task.ma_du_an == ma_da).order_by(Task.ma_cv.desc())
    if trang_thai: st = st.where(Task.trang_thai == trang_thai)
    if uu_tien: st = st.where(Task.uu_tien == uu_tien)
    if ma_moc: st = st.where(Task.ma_moc == ma_moc)
    if ma_epic: st = st.where(Task.ma_epic == ma_epic)
    if q: st = st.where(Task.ten_cv.ilike(f"%{q}%"))
    if ma_nd:
        st = st.where(Task.ma_cv.in_(select(PhanCong.ma_cv).where(PhanCong.ma_nd == ma_nd, PhanCong.trang_thai_phan_cong == TrangThaiPhanCong.ASSIGNED)))
    if tre_han:
        st = st.where(Task.han_hoan_thanh < today(), Task.trang_thai.in_(("TODO", "IN_PROGRESS", "IN_REVIEW")))
    r = paginate(db, st, page, size)
    r["items"] = [svc.task_out(db, t) for t in r["items"]]
    return r


@router.get("/projects/{ma_da}/tasks/prioritized", response_model=list[TaskOut], summary="2.4 Danh sách ưu tiên & thời hạn")
def prioritized(ma_da: int, user=Depends(current_user), db: Session = Depends(get_db)):
    require_project_perm(db, user, ma_da, "project.read")
    return svc.prioritized(db, ma_da)


@router.get("/projects/{ma_da}/reviews/pending", response_model=list[TaskOut], summary="2.6 Danh sách task cần duyệt")
def pending_reviews(ma_da: int, user=Depends(current_user), db: Session = Depends(get_db)):
    require_project_perm(db, user, ma_da, "task.review")
    ts = db.scalars(select(Task).where(Task.ma_du_an == ma_da, Task.trang_thai == TrangThaiTask.IN_REVIEW).order_by(Task.han_hoan_thanh)).all()
    return [svc.task_out(db, t) for t in ts]


@router.get("/tasks/{ma_cv}", response_model=TaskOut)
def get_task(ma_cv: int, user=Depends(current_user), db: Session = Depends(get_db)):
    t, _ = require_task_perm(db, user, ma_cv, "project.read")
    return svc.task_out(db, t)


@router.patch("/tasks/{ma_cv}", response_model=TaskOut, summary="2.2/2.4 Cập nhật công việc, ưu tiên, thời hạn")
def update_task(ma_cv: int, body: TaskUpdate, user=Depends(current_user), db: Session = Depends(get_db)):
    t, p = require_task_perm(db, user, ma_cv, "task.update")
    return svc.task_out(db, svc.update_task(db, user, p, t, body))


@router.delete("/tasks/{ma_cv}", response_model=Msg)
def delete_task(ma_cv: int, user=Depends(current_user), db: Session = Depends(get_db)):
    t, p = require_task_perm(db, user, ma_cv, "task.update")
    svc.delete_task(db, user, p, t)
    return Msg()


@router.post("/tasks/{ma_cv}/transition", response_model=TaskOut, summary="2.5 Theo dõi trạng thái công việc")
def transition(ma_cv: int, body: TransitionIn, user=Depends(current_user), db: Session = Depends(get_db)):
    t, p = require_task_perm(db, user, ma_cv, "task.transition")
    return svc.task_out(db, svc.transition(db, user, p, t, body.trang_thai))


@router.post("/tasks/{ma_cv}/progress", response_model=TaskOut, summary="2.5 Cập nhật % hoàn thành")
def progress(ma_cv: int, body: ProgressIn, user=Depends(current_user), db: Session = Depends(get_db)):
    t, p = require_task_perm(db, user, ma_cv, "task.transition")
    return svc.task_out(db, svc.set_progress(db, user, p, t, body.ty_le_hoan_thanh))


# ---------- 2.3 phân công ----------
@router.get("/tasks/{ma_cv}/assignments", response_model=list[AssignOut])
def list_assignments(ma_cv: int, user=Depends(current_user), db: Session = Depends(get_db)):
    require_task_perm(db, user, ma_cv, "project.read")
    return db.scalars(select(PhanCong).where(PhanCong.ma_cv == ma_cv).order_by(PhanCong.ngay_giao, PhanCong.ma_nd)).all()


@router.post("/tasks/{ma_cv}/assignments", response_model=AssignResult, status_code=201, summary="2.3 Phân công công việc")
def assign(ma_cv: int, body: AssignIn, user=Depends(current_user), db: Session = Depends(get_db)):
    t, p = require_task_perm(db, user, ma_cv, "task.assign")
    pc, warnings = svc.assign(db, user, p, t, body.ma_nd, body.gio_du_kien)
    return {"phan_cong": pc, "warnings": warnings}


@router.delete("/tasks/{ma_cv}/assignments/{ma_nd}", response_model=Msg)
def unassign(ma_cv: int, ma_nd: int, user=Depends(current_user), db: Session = Depends(get_db)):
    t, p = require_task_perm(db, user, ma_cv, "task.assign")
    svc.unassign(db, user, p, t, ma_nd)
    return Msg()


# ---------- 2.6 xét duyệt ----------
@router.post("/tasks/{ma_cv}/review", response_model=ReviewOut, status_code=201, summary="2.6 Xét duyệt công việc")
def review(ma_cv: int, body: ReviewIn, user=Depends(current_user), db: Session = Depends(get_db)):
    t, p = require_task_perm(db, user, ma_cv, "task.review")
    return svc.review(db, user, p, t, body)


@router.get("/tasks/{ma_cv}/reviews", response_model=list[ReviewOut])
def list_reviews(ma_cv: int, user=Depends(current_user), db: Session = Depends(get_db)):
    require_task_perm(db, user, ma_cv, "project.read")
    return db.scalars(select(XetDuyetCongViec).where(XetDuyetCongViec.ma_cv == ma_cv).order_by(XetDuyetCongViec.ma_duyet)).all()


# ---------- Subtask ----------
@router.get("/tasks/{ma_cv}/subtasks", response_model=list[SubTaskOut])
def list_subtasks(ma_cv: int, user=Depends(current_user), db: Session = Depends(get_db)):
    require_task_perm(db, user, ma_cv, "project.read")
    return db.scalars(select(SubTask).where(SubTask.ma_cv == ma_cv).order_by(SubTask.ma_subtask)).all()


@router.post("/tasks/{ma_cv}/subtasks", response_model=SubTaskOut, status_code=201)
def create_subtask(ma_cv: int, body: SubTaskIn, user=Depends(current_user), db: Session = Depends(get_db)):
    t, p = require_task_perm(db, user, ma_cv, "task.update"); ensure_writable(p)
    s = SubTask(ma_cv=ma_cv, ten_subtask=body.ten_subtask, mo_ta=body.mo_ta); db.add(s); db.flush()
    return s


def _sub(db, ma_cv, ma_sub) -> SubTask:
    s = db.get(SubTask, ma_sub)
    if not s or s.ma_cv != ma_cv:
        raise not_found("SUBTASK_NOT_FOUND", "Subtask không tồn tại")
    return s


@router.patch("/tasks/{ma_cv}/subtasks/{ma_sub}", response_model=SubTaskOut)
def update_subtask(ma_cv: int, ma_sub: int, body: SubTaskUpdate, user=Depends(current_user), db: Session = Depends(get_db)):
    t, p = require_task_perm(db, user, ma_cv, "task.transition"); ensure_writable(p)
    perms = project_perms(db, user, p.ma_du_an)
    if "task.update" not in perms and user.ma_nd not in svc.assignees(db, ma_cv):
        raise forbidden("NOT_ASSIGNEE", "Chỉ người được giao hoặc trưởng nhóm được cập nhật subtask")
    s = _sub(db, ma_cv, ma_sub)
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(s, k, v)
    return s


@router.delete("/tasks/{ma_cv}/subtasks/{ma_sub}", response_model=Msg)
def delete_subtask(ma_cv: int, ma_sub: int, user=Depends(current_user), db: Session = Depends(get_db)):
    t, p = require_task_perm(db, user, ma_cv, "task.update"); ensure_writable(p)
    db.delete(_sub(db, ma_cv, ma_sub))
    return Msg()


# ---------- Tệp đính kèm ----------
@router.post("/tasks/{ma_cv}/attachments", response_model=AttachmentOut, status_code=201, summary="2.5 Đính kèm tệp")
async def upload(ma_cv: int, file: UploadFile = File(...), user=Depends(current_user), db: Session = Depends(get_db)):
    t, p = require_task_perm(db, user, ma_cv, "task.transition"); ensure_writable(p)
    if "task.update" not in project_perms(db, user, p.ma_du_an) and user.ma_nd not in svc.assignees(db, ma_cv):
        raise forbidden("NOT_ASSIGNEE", "Chỉ người được giao hoặc trưởng nhóm được đính kèm tệp")
    data = await file.read()
    return svc.save_attachment(db, user, t, file.filename, data)


@router.get("/tasks/{ma_cv}/attachments", response_model=list[AttachmentOut])
def list_attachments(ma_cv: int, user=Depends(current_user), db: Session = Depends(get_db)):
    require_task_perm(db, user, ma_cv, "project.read")
    return db.scalars(select(TepDinhKem).where(TepDinhKem.ma_cv == ma_cv)).all()


@router.get("/attachments/{ma_tep}/download")
def download(ma_tep: int, user=Depends(current_user), db: Session = Depends(get_db)):
    a = get_or_404(db, TepDinhKem, ma_tep, "ATTACHMENT_NOT_FOUND")
    require_task_perm(db, user, a.ma_cv, "project.read")
    return FileResponse(a.duong_dan, filename=a.ten_tep)


@router.delete("/attachments/{ma_tep}", response_model=Msg)
def delete_attachment(ma_tep: int, user=Depends(current_user), db: Session = Depends(get_db)):
    a = get_or_404(db, TepDinhKem, ma_tep, "ATTACHMENT_NOT_FOUND")
    t, p = require_task_perm(db, user, a.ma_cv, "task.transition")
    if a.ma_nguoi_tai != user.ma_nd and "task.update" not in project_perms(db, user, p.ma_du_an):
        raise forbidden()
    db.delete(a)
    return Msg()


# ---------- 2.7 giờ làm ----------
def _ts_out(e, tt=None, tp=None):
    o = TimesheetOut.model_validate(e)
    o.tong_gio_tich_luy_task, o.tong_gio_tich_luy_du_an = tt, tp
    return o


@router.post("/tasks/{ma_cv}/timesheets", response_model=TimesheetOut, status_code=201, summary="2.7 Ghi nhận thời gian làm việc")
def log_time(ma_cv: int, body: TimesheetIn, user=Depends(current_user), db: Session = Depends(get_db)):
    t, p = require_task_perm(db, user, ma_cv, "timesheet.log")
    e = svc.log_time(db, user, p, t, body)
    tt, tp = svc.totals(db, t, user.ma_nd)
    return _ts_out(e, tt, tp)


@router.get("/tasks/{ma_cv}/timesheets", response_model=list[TimesheetOut])
def task_timesheets(ma_cv: int, user=Depends(current_user), db: Session = Depends(get_db)):
    t, p = require_task_perm(db, user, ma_cv, "project.read")
    st = select(NhatKyGioLam).where(NhatKyGioLam.ma_cv == ma_cv).order_by(NhatKyGioLam.bat_dau)
    if "report.project" not in project_perms(db, user, p.ma_du_an):
        st = st.where(NhatKyGioLam.ma_nd == user.ma_nd)
    return db.scalars(st).all()


@router.get("/me/timesheets", response_model=Page[TimesheetOut])
def my_timesheets(tu_ngay: date | None = None, den_ngay: date | None = None, page: int = Query(1, ge=1),
                  size: int = Query(50, ge=1, le=200), user=Depends(current_user), db: Session = Depends(get_db)):
    st = select(NhatKyGioLam).where(NhatKyGioLam.ma_nd == user.ma_nd).order_by(NhatKyGioLam.bat_dau.desc())
    if tu_ngay: st = st.where(NhatKyGioLam.bat_dau >= datetime.combine(tu_ngay, datetime.min.time()))
    if den_ngay: st = st.where(NhatKyGioLam.bat_dau < datetime.combine(den_ngay + timedelta(days=1), datetime.min.time()))
    return paginate(db, st, page, size)


@router.get("/me/timesheets/summary", summary="Tổng giờ làm tích lũy")
def my_summary(tu_ngay: date | None = None, den_ngay: date | None = None, user=Depends(current_user), db: Session = Depends(get_db)):
    st = select(Task.ma_du_an, func.sum(NhatKyGioLam.so_gio), func.sum(NhatKyGioLam.chi_phi_thuc_te)).join(
        Task, Task.ma_cv == NhatKyGioLam.ma_cv).where(NhatKyGioLam.ma_nd == user.ma_nd).group_by(Task.ma_du_an)
    if tu_ngay: st = st.where(NhatKyGioLam.bat_dau >= datetime.combine(tu_ngay, datetime.min.time()))
    if den_ngay: st = st.where(NhatKyGioLam.bat_dau < datetime.combine(den_ngay + timedelta(days=1), datetime.min.time()))
    rows = db.execute(st).all()
    return {"tong_gio": float(sum(r[1] for r in rows)), "tong_chi_phi": float(sum(r[2] for r in rows)),
            "theo_du_an": [{"ma_du_an": r[0], "gio": float(r[1]), "chi_phi": float(r[2])} for r in rows]}


@router.get("/projects/{ma_da}/timesheets", response_model=Page[TimesheetOut])
def project_timesheets(ma_da: int, ma_nd: int | None = None, page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=200),
                       user=Depends(current_user), db: Session = Depends(get_db)):
    require_project_perm(db, user, ma_da, "report.project")
    st = select(NhatKyGioLam).join(Task, Task.ma_cv == NhatKyGioLam.ma_cv).where(Task.ma_du_an == ma_da).order_by(NhatKyGioLam.bat_dau.desc())
    if ma_nd: st = st.where(NhatKyGioLam.ma_nd == ma_nd)
    return paginate(db, st, page, size)


@router.patch("/timesheets/{ma_nk}", response_model=TimesheetOut)
def edit_timesheet(ma_nk: int, body: TimesheetUpdate, user=Depends(current_user), db: Session = Depends(get_db)):
    e = get_or_404(db, NhatKyGioLam, ma_nk, "TIMESHEET_NOT_FOUND")
    return _ts_out(svc.edit_time(db, user, e, body))


@router.delete("/timesheets/{ma_nk}", response_model=Msg)
def delete_timesheet(ma_nk: int, user=Depends(current_user), db: Session = Depends(get_db)):
    svc.delete_time(db, user, get_or_404(db, NhatKyGioLam, ma_nk, "TIMESHEET_NOT_FOUND"))
    return Msg()
