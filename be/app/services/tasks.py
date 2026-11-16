import os, re, uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import (KetQuaDuyet, TrangThaiPhanCong as PC, TrangThaiTask as TS, UuTien)
from app.errors import conflict, forbidden, invalid
from app.models import (DuAn, Epic, MocDuAn, NguoiDung, NhanVien, NhatKyGioLam, PhanCong, SubTask, Task, TepDinhKem,
                        XetDuyetCongViec)
from app.schemas.common import D
from app.security import utcnow
from app.services.access import membership, project_perms
from app.services.common import audit, notify, today
from app.services.projects import OPEN_TASK, check_version, ensure_writable

PRIO_W = {UuTien.CRITICAL: 4, UuTien.HIGH: 3, UuTien.MEDIUM: 2, UuTien.LOW: 1}
ALLOWED = {TS.TODO: {TS.IN_PROGRESS, TS.CANCELLED}, TS.IN_PROGRESS: {TS.IN_REVIEW, TS.TODO, TS.CANCELLED},
           TS.IN_REVIEW: {TS.CANCELLED}, TS.DONE: {TS.IN_PROGRESS}, TS.CANCELLED: {TS.TODO}}
MEMBER_ALLOWED = {(TS.TODO, TS.IN_PROGRESS), (TS.IN_PROGRESS, TS.IN_REVIEW), (TS.IN_PROGRESS, TS.TODO)}


def assignees(db, ma_cv) -> list[int]:
    return list(db.scalars(select(PhanCong.ma_nd).where(PhanCong.ma_cv == ma_cv, PhanCong.trang_thai_phan_cong == PC.ASSIGNED)))


def urgency(t: Task) -> str | None:
    if t.trang_thai not in OPEN_TASK:
        return None
    if not t.han_hoan_thanh:
        return "NO_DEADLINE"
    d = (t.han_hoan_thanh - today()).days
    return "OVERDUE" if d < 0 else "URGENT" if d <= 2 else "SOON" if d <= 7 else "NORMAL"


def task_out(db, t: Task) -> dict:
    o = {c: getattr(t, c) for c in ("ma_cv", "ma_du_an", "ma_moc", "ma_epic", "ten_cv", "mo_ta", "trang_thai", "uu_tien",
                                     "ty_le_hoan_thanh", "ngay_bat_dau_du_kien", "han_hoan_thanh", "gio_du_kien",
                                     "ma_nguoi_tao", "hoan_thanh_luc", "version")}
    o["gio_du_kien"] = float(t.gio_du_kien)
    o["assignees"] = assignees(db, t.ma_cv)
    o["muc_do_khan"] = urgency(t)
    o["tre_han"] = urgency(t) == "OVERDUE"
    return o


def _check_refs(db, p: DuAn, ma_moc, ma_epic):
    if ma_moc is not None:
        m = db.get(MocDuAn, ma_moc)
        if not m or m.ma_du_an != p.ma_du_an:
            raise invalid("INVALID_MILESTONE", "Mốc không thuộc dự án")
    if ma_epic is not None:
        e = db.get(Epic, ma_epic)
        if not e or e.ma_du_an != p.ma_du_an:
            raise invalid("INVALID_EPIC", "Epic không thuộc dự án")


# ---- 2.1 ----
def create_task(db, actor, p: DuAn, d) -> Task:
    ensure_writable(p); _check_refs(db, p, d.ma_moc, d.ma_epic)
    t = Task(ma_du_an=p.ma_du_an, ma_moc=d.ma_moc, ma_epic=d.ma_epic, ten_cv=d.ten_cv, mo_ta=d.mo_ta, uu_tien=d.uu_tien,
             ngay_bat_dau_du_kien=d.ngay_bat_dau_du_kien, han_hoan_thanh=d.han_hoan_thanh,
             gio_du_kien=D(d.gio_du_kien), ma_nguoi_tao=actor.ma_nd)
    db.add(t); db.flush()
    audit(db, actor.ma_nd, "TASK_CREATED", "task", t.ma_cv, t.ten_cv)
    return t


# ---- 2.2 / 2.4 ----
def update_task(db, actor, p: DuAn, t: Task, d) -> Task:
    ensure_writable(p); check_version(t, d.version)
    if t.trang_thai in (TS.DONE, TS.CANCELLED):
        raise conflict("TASK_LOCKED", "Công việc đã hoàn thành/hủy, không thể sửa")
    data = d.model_dump(exclude_unset=True, exclude={"version"})
    _check_refs(db, p, data.get("ma_moc"), data.get("ma_epic"))
    start = data.get("ngay_bat_dau_du_kien", t.ngay_bat_dau_du_kien)
    end = data.get("han_hoan_thanh", t.han_hoan_thanh)
    if start and end and end < start:
        raise invalid("INVALID_DATE_RANGE", "Hạn hoàn thành phải >= ngày bắt đầu")
    for k, v in data.items():
        setattr(t, k, D(v) if k == "gio_du_kien" and v is not None else v)
    t.version += 1
    audit(db, actor.ma_nd, "TASK_UPDATED", "task", t.ma_cv, ",".join(data))
    return t


def delete_task(db, actor, p, t: Task):
    ensure_writable(p)
    if t.trang_thai != TS.TODO or db.scalar(select(func.count()).select_from(NhatKyGioLam).where(NhatKyGioLam.ma_cv == t.ma_cv)):
        raise conflict("TASK_NOT_DELETABLE", "Chỉ xóa được task TODO chưa có giờ làm; hãy chuyển sang CANCELLED")
    for model in (PhanCong, SubTask, TepDinhKem):
        for x in db.scalars(select(model).where(model.ma_cv == t.ma_cv)):
            db.delete(x)
    db.delete(t)
    audit(db, actor.ma_nd, "TASK_DELETED", "task", t.ma_cv)


# ---- 2.5 trạng thái ----
def transition(db, actor, p: DuAn, t: Task, target: TS) -> Task:
    ensure_writable(p)
    perms = project_perms(db, actor, p.ma_du_an)
    cur = t.trang_thai
    if target == TS.DONE:
        raise invalid("USE_REVIEW_ENDPOINT", "Hoàn thành công việc phải qua xét duyệt (POST /tasks/{id}/review)")
    if target not in ALLOWED[cur]:
        raise conflict("INVALID_STATUS_TRANSITION", f"Không thể chuyển {cur.value} -> {target.value}")
    is_assignee = actor.ma_nd in assignees(db, t.ma_cv)
    privileged = "task.update" in perms
    if not privileged:
        if not is_assignee:
            raise forbidden("NOT_ASSIGNEE", "Chỉ người được giao mới được cập nhật trạng thái")
        if (cur, target) not in MEMBER_ALLOWED:
            raise forbidden("TRANSITION_REQUIRES_LEAD", "Thao tác này cần quyền trưởng nhóm/PM")
    if cur == TS.DONE and "task.review" not in perms:
        raise forbidden("TRANSITION_REQUIRES_LEAD", "Mở lại công việc cần quyền xét duyệt")
    if cur == TS.DONE:
        t.hoan_thanh_luc, t.ty_le_hoan_thanh = None, min(t.ty_le_hoan_thanh, 99)
        for pc in db.scalars(select(PhanCong).where(PhanCong.ma_cv == t.ma_cv, PhanCong.trang_thai_phan_cong == PC.COMPLETED)):
            pc.trang_thai_phan_cong = PC.ASSIGNED
        db.flush()
    if target in (TS.IN_PROGRESS, TS.IN_REVIEW) and not assignees(db, t.ma_cv):
        raise conflict("TASK_NOT_ASSIGNED", "Công việc chưa được phân công")
    if target == TS.CANCELLED:
        for pc in db.scalars(select(PhanCong).where(PhanCong.ma_cv == t.ma_cv, PhanCong.trang_thai_phan_cong == PC.ASSIGNED)):
            pc.trang_thai_phan_cong = PC.CANCELLED
    if target == TS.TODO and cur == TS.CANCELLED:
        t.ty_le_hoan_thanh = 0
    t.trang_thai = target
    t.version += 1
    audit(db, actor.ma_nd, "TASK_STATUS_CHANGED", "task", t.ma_cv, f"{cur.value}->{target.value}")
    if target == TS.IN_REVIEW:
        for u in _reviewers(db, p):
            notify(db, u, "REVIEW_REQUESTED", f"Công việc '{t.ten_cv}' chờ duyệt", ma_cv=t.ma_cv)
    return t


def _reviewers(db, p: DuAn) -> list[int]:
    from app.models import ThanhVienDuAn, VaiTro
    return list(db.scalars(select(ThanhVienDuAn.ma_nguoi_dung).join(VaiTro, VaiTro.ma_vai_tro == ThanhVienDuAn.ma_vai_tro)
                           .where(ThanhVienDuAn.ma_du_an == p.ma_du_an, ThanhVienDuAn.trang_thai == "ACTIVE",
                                  VaiTro.code.in_(["TEAM_LEAD", "PM"]))))


def set_progress(db, actor, p, t: Task, pct: int) -> Task:
    ensure_writable(p)
    perms = project_perms(db, actor, p.ma_du_an)
    if "task.update" not in perms and actor.ma_nd not in assignees(db, t.ma_cv):
        raise forbidden("NOT_ASSIGNEE", "Chỉ người được giao mới cập nhật tiến độ")
    if t.trang_thai != TS.IN_PROGRESS:
        raise conflict("TASK_NOT_IN_PROGRESS", "Chỉ cập nhật % khi công việc đang IN_PROGRESS")
    t.ty_le_hoan_thanh = pct; t.version += 1
    audit(db, actor.ma_nd, "TASK_PROGRESS", "task", t.ma_cv, str(pct))
    return t


# ---- 2.3 phân công ----
def assign(db, actor, p: DuAn, t: Task, ma_nd: int, gio: float | None):
    ensure_writable(p)
    if t.trang_thai in (TS.DONE, TS.CANCELLED):
        raise conflict("TASK_NOT_ASSIGNABLE", "Không thể phân công công việc đã hoàn thành/hủy")
    if not membership(db, p.ma_du_an, ma_nd):
        raise invalid("NOT_PROJECT_MEMBER", "Người được giao phải là thành viên dự án (ràng buộc phân quyền)")
    if not db.get(NhanVien, ma_nd):
        raise invalid("ASSIGNEE_MUST_BE_EMPLOYEE", "Chỉ NHÂN VIÊN mới nhận việc (ERD: NHÂN VIÊN –Nhận việc– PHÂN CÔNG)")
    if ma_nd in assignees(db, t.ma_cv):
        raise conflict("ALREADY_ASSIGNED", "Người dùng đã được giao công việc này")
    g = D(gio if gio is not None else t.gio_du_kien)
    pc = db.get(PhanCong, (t.ma_cv, ma_nd))           # khóa ghép (MaCV, MaND): giao lại = kích hoạt lại bản ghi cũ
    if pc:
        pc.trang_thai_phan_cong, pc.ngay_giao, pc.gio_du_kien, pc.ma_nguoi_giao = PC.ASSIGNED, today(), g, actor.ma_nd
    else:
        pc = PhanCong(ma_cv=t.ma_cv, ma_nd=ma_nd, ngay_giao=today(), gio_du_kien=g, ma_nguoi_giao=actor.ma_nd); db.add(pc)
    db.flush()
    warnings = []
    planned = db.scalar(select(func.coalesce(func.sum(PhanCong.gio_du_kien), 0)).join(Task, Task.ma_cv == PhanCong.ma_cv)
                        .where(Task.ma_du_an == p.ma_du_an, PhanCong.trang_thai_phan_cong != PC.CANCELLED))
    if p.ngan_sach_gio and planned > p.ngan_sach_gio:
        warnings.append({"code": "OVER_HOURS_BUDGET", "message": f"Tổng giờ phân công {planned} vượt ngân sách giờ {p.ngan_sach_gio}",
                         "tong_gio_phan_cong": float(planned), "ngan_sach_gio": float(p.ngan_sach_gio)})
        # DFD 2.3 → Quản lý dự án: "Cảnh báo vượt ngân sách giờ"
        notify(db, p.ma_quan_ly, "OVER_HOURS_BUDGET", f"Dự án '{p.ten_du_an}': giờ phân công {planned} vượt ngân sách {p.ngan_sach_gio}",
               ma_cv=t.ma_cv, dedupe=f"OVERPLAN:{p.ma_du_an}:{today()}")
    if t.han_hoan_thanh and t.han_hoan_thanh < today():
        warnings.append({"code": "DEADLINE_PASSED", "message": "Hạn hoàn thành đã qua"})
    audit(db, actor.ma_nd, "TASK_ASSIGNED", "task", t.ma_cv, f"user={ma_nd}")
    notify(db, ma_nd, "TASK_ASSIGNED", f"Bạn được giao công việc '{t.ten_cv}'", ma_cv=t.ma_cv)
    return pc, warnings


def unassign(db, actor, p, t: Task, ma_nd: int):
    ensure_writable(p)
    pc = db.scalar(select(PhanCong).where(PhanCong.ma_cv == t.ma_cv, PhanCong.ma_nd == ma_nd, PhanCong.trang_thai_phan_cong == PC.ASSIGNED))
    if not pc:
        raise invalid("NOT_ASSIGNED", "Người dùng không được giao công việc này")
    pc.trang_thai_phan_cong = PC.CANCELLED
    db.flush()
    if t.trang_thai in (TS.IN_PROGRESS, TS.IN_REVIEW) and not assignees(db, t.ma_cv):
        t.trang_thai = TS.TODO; t.version += 1
    audit(db, actor.ma_nd, "TASK_UNASSIGNED", "task", t.ma_cv, f"user={ma_nd}")


# ---- 2.6 xét duyệt ----
def review(db, actor, p, t: Task, d) -> XetDuyetCongViec:
    ensure_writable(p)
    if t.trang_thai != TS.IN_REVIEW:
        raise conflict("TASK_NOT_IN_REVIEW", "Công việc không ở trạng thái chờ duyệt")
    asg = assignees(db, t.ma_cv)
    if actor.ma_nd in asg and len(asg) == 1:
        raise forbidden("SELF_REVIEW", "Không được tự duyệt công việc của chính mình")
    if d.ket_qua == KetQuaDuyet.REJECTED and not (d.nhan_xet or "").strip():
        raise invalid("COMMENT_REQUIRED", "Từ chối phải kèm nhận xét")
    r = XetDuyetCongViec(ma_cv=t.ma_cv, ma_nguoi_duyet=actor.ma_nd, ket_qua=d.ket_qua, nhan_xet=d.nhan_xet); db.add(r)
    if d.ket_qua == KetQuaDuyet.APPROVED:
        t.trang_thai, t.ty_le_hoan_thanh, t.hoan_thanh_luc = TS.DONE, 100, utcnow()
        for pc in db.scalars(select(PhanCong).where(PhanCong.ma_cv == t.ma_cv, PhanCong.trang_thai_phan_cong == PC.ASSIGNED)):
            pc.trang_thai_phan_cong = PC.COMPLETED
    else:
        t.trang_thai = TS.IN_PROGRESS
    t.version += 1
    db.flush()
    audit(db, actor.ma_nd, "TASK_REVIEWED", "task", t.ma_cv, d.ket_qua.value)
    for u in asg:
        notify(db, u, "TASK_REVIEWED", f"Công việc '{t.ten_cv}' đã {'được duyệt' if d.ket_qua == KetQuaDuyet.APPROVED else 'bị từ chối'}",
               d.nhan_xet, ma_cv=t.ma_cv)
    return r


# ---- tệp đính kèm ----
def save_attachment(db, actor, t: Task, filename: str, data: bytes) -> TepDinhKem:
    name = os.path.basename(filename or "")
    name = re.sub(r"[^\w.\- ]", "_", name).strip()
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if not name or ext not in settings.allowed_upload_ext.split(","):
        raise invalid("FILE_TYPE_NOT_ALLOWED", f"Định dạng tệp không được hỗ trợ ({settings.allowed_upload_ext})")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise AppErrorTooLarge()
    if not data:
        raise invalid("EMPTY_FILE", "Tệp rỗng")
    folder = os.path.join(settings.upload_dir, str(t.ma_cv)); os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{uuid.uuid4().hex}_{name}")
    with open(path, "wb") as fh:
        fh.write(data)
    a = TepDinhKem(ma_cv=t.ma_cv, ten_tep=name, duong_dan=path, kich_thuoc=len(data), ma_nguoi_tai=actor.ma_nd)
    db.add(a); db.flush()
    audit(db, actor.ma_nd, "ATTACHMENT_UPLOADED", "task", t.ma_cv, name)
    return a


def AppErrorTooLarge():
    from app.errors import AppError
    return AppError(413, "FILE_TOO_LARGE", f"Tệp vượt quá {settings.max_upload_mb}MB")


# ---- 2.7 giờ làm ----
def _hours(a: datetime, b: datetime) -> Decimal:
    return (D((b - a).total_seconds()) / D(3600)).quantize(Decimal("0.01"))


def _validate_slot(db, user_id, start, end, exclude=None):
    if end <= start:
        raise invalid("INVALID_TIME_RANGE", "Giờ kết thúc phải sau giờ bắt đầu")
    if end > utcnow() + timedelta(minutes=5):
        raise invalid("FUTURE_TIME", "Không thể ghi giờ làm trong tương lai")
    if end - start > timedelta(hours=24):
        raise invalid("DURATION_TOO_LONG", "Một bản ghi không quá 24 giờ")
    q = select(NhatKyGioLam.ma_nk).where(NhatKyGioLam.ma_nd == user_id, NhatKyGioLam.bat_dau < end, NhatKyGioLam.ket_thuc > start)
    if exclude:
        q = q.where(NhatKyGioLam.ma_nk != exclude)
    if db.scalar(q.limit(1)):
        raise conflict("TIMESHEET_OVERLAP", "Khoảng thời gian trùng với bản ghi giờ làm khác")


def totals(db, t: Task, user_id):
    a = db.scalar(select(func.coalesce(func.sum(NhatKyGioLam.so_gio), 0)).where(NhatKyGioLam.ma_cv == t.ma_cv))
    b = db.scalar(select(func.coalesce(func.sum(NhatKyGioLam.so_gio), 0)).join(Task, Task.ma_cv == NhatKyGioLam.ma_cv)
                  .where(Task.ma_du_an == t.ma_du_an, NhatKyGioLam.ma_nd == user_id))
    return float(a), float(b)


def log_time(db, actor, p: DuAn, t: Task, d) -> NhatKyGioLam:
    ensure_writable(p)
    if actor.ma_nd not in assignees(db, t.ma_cv):
        raise forbidden("NOT_ASSIGNEE", "Chỉ ghi giờ cho công việc được giao cho bạn")
    if t.trang_thai in (TS.DONE, TS.CANCELLED):
        raise conflict("TASK_LOCKED", "Không ghi giờ cho công việc đã hoàn thành/hủy")
    _validate_slot(db, actor.ma_nd, d.bat_dau, d.ket_thuc)
    nv = db.get(NhanVien, actor.ma_nd)
    rate = nv.don_gia_gio if nv and nv.don_gia_gio else D(settings.default_hourly_rate)
    h = _hours(d.bat_dau, d.ket_thuc)
    e = NhatKyGioLam(ma_cv=t.ma_cv, ma_nd=actor.ma_nd, bat_dau=d.bat_dau, ket_thuc=d.ket_thuc, so_gio=h,
                     noi_dung=d.noi_dung, chi_phi_thuc_te=(h * rate).quantize(Decimal("0.01")))
    db.add(e); db.flush()
    audit(db, actor.ma_nd, "TIMESHEET_LOGGED", "nhat_ky_gio_lam", e.ma_nk, f"{h}h")
    return e


def edit_time(db, actor, e: NhatKyGioLam, d) -> NhatKyGioLam:
    if e.ma_nd != actor.ma_nd:
        raise forbidden("NOT_OWNER", "Chỉ sửa được bản ghi giờ làm của chính mình")
    if e.bat_dau < utcnow() - timedelta(days=settings.timesheet_edit_days):
        raise conflict("TIMESHEET_LOCKED", f"Chỉ sửa/xóa trong {settings.timesheet_edit_days} ngày")
    data = d.model_dump(exclude_unset=True)
    s, en = data.get("bat_dau", e.bat_dau), data.get("ket_thuc", e.ket_thuc)
    _validate_slot(db, e.ma_nd, s, en, exclude=e.ma_nk)
    nv = db.get(NhanVien, e.ma_nd)
    rate = nv.don_gia_gio if nv and nv.don_gia_gio else D(settings.default_hourly_rate)
    e.bat_dau, e.ket_thuc, e.so_gio = s, en, _hours(s, en)
    e.chi_phi_thuc_te = (e.so_gio * rate).quantize(Decimal("0.01"))
    if "noi_dung" in data:
        e.noi_dung = data["noi_dung"]
    audit(db, actor.ma_nd, "TIMESHEET_UPDATED", "nhat_ky_gio_lam", e.ma_nk)
    return e


def delete_time(db, actor, e: NhatKyGioLam):
    if e.ma_nd != actor.ma_nd:
        raise forbidden("NOT_OWNER", "Chỉ xóa được bản ghi giờ làm của chính mình")
    if e.bat_dau < utcnow() - timedelta(days=settings.timesheet_edit_days):
        raise conflict("TIMESHEET_LOCKED", f"Chỉ sửa/xóa trong {settings.timesheet_edit_days} ngày")
    db.delete(e)
    audit(db, actor.ma_nd, "TIMESHEET_DELETED", "nhat_ky_gio_lam", e.ma_nk)


def prioritized(db, ma_da: int) -> list[dict]:
    ts = db.scalars(select(Task).where(Task.ma_du_an == ma_da, Task.trang_thai.in_(OPEN_TASK))).all()
    order = {"OVERDUE": 0, "URGENT": 1, "SOON": 2, "NORMAL": 3, "NO_DEADLINE": 4}
    ts = sorted(ts, key=lambda t: (order[urgency(t)], -PRIO_W[t.uu_tien], t.han_hoan_thanh or date.max))
    return [task_out(db, t) for t in ts]
