from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import (ProjRole, TrangThaiDuAn as PS, TrangThaiMoc, TrangThaiPhanCong, TrangThaiTask as TS,
                       TrangThaiThanhVien)
from app.errors import conflict, invalid
from app.models import (DuAn, MocDuAn, NguoiDung, NhatKyGioLam, PhanCong, QuanLy, Task, ThanhVienDuAn, VaiTro)
from app.schemas.common import D
from app.services.common import audit, notify, today

OPEN_TASK = (TS.TODO, TS.IN_PROGRESS, TS.IN_REVIEW)
TRANSITIONS = {PS.PLANNING: {PS.ACTIVE}, PS.ACTIVE: {PS.ON_HOLD, PS.COMPLETED}, PS.ON_HOLD: {PS.ACTIVE},
               PS.COMPLETED: {PS.ACTIVE}, PS.CLOSED: set()}


def role_id(db, code) -> int:
    return db.scalar(select(VaiTro.ma_vai_tro).where(VaiTro.code == str(code)))


def ensure_writable(p: DuAn):
    if p.trang_thai in (PS.CLOSED, PS.COMPLETED):
        raise conflict("PROJECT_CLOSED", "Dự án đã hoàn thành/đóng, không thể thay đổi")


def check_version(obj, version: int):
    if obj.version != version:
        raise conflict("VERSION_CONFLICT", f"Dữ liệu đã được người khác cập nhật (version hiện tại {obj.version})")


def create_project(db: Session, actor: NguoiDung, d) -> DuAn:
    if not db.get(QuanLy, d.ma_quan_ly):
        raise invalid("INVALID_MANAGER", "ma_quan_ly phải là người dùng loại QUAN_LY")
    mgr = db.get(NguoiDung, d.ma_quan_ly)
    if mgr.trang_thai.value != "ACTIVE":
        raise invalid("USER_INACTIVE", "Quản lý dự án không ở trạng thái ACTIVE")
    if db.scalar(select(DuAn.ma_du_an).where(func.lower(DuAn.ten_du_an) == d.ten_du_an.lower())):
        raise conflict("DUPLICATE_PROJECT_NAME", "Tên dự án đã tồn tại")
    p = DuAn(ten_du_an=d.ten_du_an, muc_tieu=d.muc_tieu, ngay_bat_dau=d.ngay_bat_dau,
             ngay_ket_thuc_du_kien=d.ngay_ket_thuc_du_kien, ngan_sach_gio=D(d.ngan_sach_gio),
             ma_quan_ly=d.ma_quan_ly, created_by=actor.ma_nd)
    db.add(p); db.flush()
    db.add(ThanhVienDuAn(ma_du_an=p.ma_du_an, ma_nguoi_dung=d.ma_quan_ly, ma_vai_tro=role_id(db, ProjRole.PM),
                         ngay_tham_gia=today()))
    audit(db, actor.ma_nd, "PROJECT_CREATED", "du_an", p.ma_du_an, p.ten_du_an)
    notify(db, d.ma_quan_ly, "PROJECT_ASSIGNED", f"Bạn được giao quản lý dự án {p.ten_du_an}")
    return p


def update_info(db, actor, p: DuAn, d) -> DuAn:
    ensure_writable(p); check_version(p, d.version)
    data = d.model_dump(exclude_unset=True, exclude={"version"})
    if data.get("ten_du_an") and data["ten_du_an"].lower() != p.ten_du_an.lower():
        if db.scalar(select(DuAn.ma_du_an).where(func.lower(DuAn.ten_du_an) == data["ten_du_an"].lower())):
            raise conflict("DUPLICATE_PROJECT_NAME", "Tên dự án đã tồn tại")
    for k, v in data.items():
        if v is not None or k == "muc_tieu":
            setattr(p, k, v)
    p.version += 1
    audit(db, actor.ma_nd, "PROJECT_UPDATED", "du_an", p.ma_du_an, ",".join(data))
    return p


def update_goals(db, actor, p: DuAn, d) -> DuAn:
    ensure_writable(p); check_version(p, d.version)
    data = d.model_dump(exclude_unset=True, exclude={"version"})
    start = data.get("ngay_bat_dau") or p.ngay_bat_dau
    end = data.get("ngay_ket_thuc_du_kien") or p.ngay_ket_thuc_du_kien
    if end < start:
        raise invalid("INVALID_DATE_RANGE", "Ngày kết thúc phải >= ngày bắt đầu")
    out = db.scalar(select(func.count()).select_from(MocDuAn).where(
        MocDuAn.ma_du_an == p.ma_du_an, (MocDuAn.han_hoan_thanh < start) | (MocDuAn.han_hoan_thanh > end)))
    if out:
        raise invalid("MILESTONE_OUT_OF_RANGE", f"{out} mốc nằm ngoài khoảng thời gian mới của dự án")
    p.ngay_bat_dau, p.ngay_ket_thuc_du_kien = start, end
    if "muc_tieu" in data:
        p.muc_tieu = data["muc_tieu"]
    if data.get("ngan_sach_gio") is not None:
        p.ngan_sach_gio = D(data["ngan_sach_gio"])
    p.version += 1
    audit(db, actor.ma_nd, "PROJECT_GOALS_SET", "du_an", p.ma_du_an, ",".join(data))
    return p


def open_tasks(db, ma_da) -> int:
    return db.scalar(select(func.count()).select_from(Task).where(Task.ma_du_an == ma_da, Task.trang_thai.in_(OPEN_TASK)))


def change_status(db, actor, p: DuAn, target: PS) -> DuAn:
    if target == PS.CLOSED:
        raise invalid("USE_CLOSE_ENDPOINT", "Dùng POST /projects/{id}/close để đóng dự án")
    if target not in TRANSITIONS[p.trang_thai]:
        raise conflict("INVALID_STATUS_TRANSITION", f"Không thể chuyển {p.trang_thai.value} -> {target.value}")
    if target == PS.COMPLETED and open_tasks(db, p.ma_du_an):
        raise conflict("OPEN_TASKS_REMAIN", "Còn công việc chưa hoàn thành")
    old = p.trang_thai
    p.trang_thai = target
    p.version += 1
    audit(db, actor.ma_nd, "PROJECT_STATUS_CHANGED", "du_an", p.ma_du_an, f"{old.value}->{target.value}")
    return p


def close_project(db, actor, p: DuAn, force: bool, note: str | None) -> DuAn:
    if p.trang_thai == PS.CLOSED:
        raise conflict("ALREADY_CLOSED", "Dự án đã đóng")
    n = open_tasks(db, p.ma_du_an)
    if n and not force:
        raise conflict("OPEN_TASKS_REMAIN", f"Còn {n} công việc chưa hoàn thành (dùng force=true để hủy)")
    if n:
        for t in db.scalars(select(Task).where(Task.ma_du_an == p.ma_du_an, Task.trang_thai.in_(OPEN_TASK))):
            t.trang_thai = TS.CANCELLED; t.version += 1
            for pc in db.scalars(select(PhanCong).where(PhanCong.ma_cv == t.ma_cv,
                                                          PhanCong.trang_thai_phan_cong == TrangThaiPhanCong.ASSIGNED)):
                pc.trang_thai_phan_cong = TrangThaiPhanCong.CANCELLED
    p.trang_thai, p.ngay_dong = PS.CLOSED, today()
    p.version += 1
    audit(db, actor.ma_nd, "PROJECT_CLOSED", "du_an", p.ma_du_an, note or ("force" if force else None))
    return p


# ---- 1.4 thành viên ----
def member_out(db, m: ThanhVienDuAn) -> dict:
    u = db.get(NguoiDung, m.ma_nguoi_dung)
    return dict(ma_du_an=m.ma_du_an, ma_nguoi_dung=m.ma_nguoi_dung, ho_ten=u.ho_ten, email=u.email,
                vai_tro=db.get(VaiTro, m.ma_vai_tro).code, ngay_tham_gia=m.ngay_tham_gia, ngay_roi=m.ngay_roi,
                trang_thai=m.trang_thai)


def add_member(db, actor, p: DuAn, d) -> ThanhVienDuAn:
    ensure_writable(p)
    if d.vai_tro == ProjRole.PM:
        raise invalid("INVALID_PROJECT_ROLE", "Vai trò PM chỉ dành cho quản lý dự án")
    u = db.get(NguoiDung, d.ma_nguoi_dung)
    if not u:
        raise invalid("USER_NOT_FOUND", "Người dùng không tồn tại")
    if u.trang_thai.value != "ACTIVE":
        raise invalid("USER_INACTIVE", "Người dùng không ở trạng thái ACTIVE")
    m = db.get(ThanhVienDuAn, (p.ma_du_an, u.ma_nd))
    if m and m.trang_thai == TrangThaiThanhVien.ACTIVE:
        raise conflict("ALREADY_MEMBER", "Người dùng đã là thành viên dự án")
    rid = role_id(db, d.vai_tro)
    if m:
        m.trang_thai, m.ngay_roi, m.ma_vai_tro, m.ngay_tham_gia = TrangThaiThanhVien.ACTIVE, None, rid, today()
    else:
        m = ThanhVienDuAn(ma_du_an=p.ma_du_an, ma_nguoi_dung=u.ma_nd, ma_vai_tro=rid, ngay_tham_gia=today()); db.add(m)
    audit(db, actor.ma_nd, "MEMBER_ADDED", "du_an", p.ma_du_an, f"user={u.ma_nd},role={d.vai_tro.value}")
    notify(db, u.ma_nd, "ADDED_TO_PROJECT", f"Bạn được thêm vào dự án {p.ten_du_an}")
    db.flush()
    return m


def change_member_role(db, actor, p, ma_nd, role: ProjRole):
    ensure_writable(p)
    m = db.get(ThanhVienDuAn, (p.ma_du_an, ma_nd))
    if not m or m.trang_thai != TrangThaiThanhVien.ACTIVE:
        raise invalid("NOT_PROJECT_MEMBER", "Người dùng không phải thành viên đang hoạt động")
    if ma_nd == p.ma_quan_ly or role == ProjRole.PM:
        raise conflict("CANNOT_CHANGE_MANAGER_ROLE", "Không thể đổi vai trò của quản lý dự án")
    m.ma_vai_tro = role_id(db, role)
    audit(db, actor.ma_nd, "MEMBER_ROLE_CHANGED", "du_an", p.ma_du_an, f"user={ma_nd},role={role.value}")
    return m


def remove_member(db, actor, p, ma_nd):
    ensure_writable(p)
    m = db.get(ThanhVienDuAn, (p.ma_du_an, ma_nd))
    if not m or m.trang_thai != TrangThaiThanhVien.ACTIVE:
        raise invalid("NOT_PROJECT_MEMBER", "Người dùng không phải thành viên đang hoạt động")
    if ma_nd == p.ma_quan_ly:
        raise conflict("CANNOT_REMOVE_MANAGER", "Không thể xóa quản lý dự án khỏi dự án")
    n = db.scalar(select(func.count()).select_from(PhanCong).join(Task, Task.ma_cv == PhanCong.ma_cv).where(
        Task.ma_du_an == p.ma_du_an, PhanCong.ma_nd == ma_nd, PhanCong.trang_thai_phan_cong == TrangThaiPhanCong.ASSIGNED,
        Task.trang_thai.in_(OPEN_TASK)))
    if n:
        raise conflict("MEMBER_HAS_OPEN_TASKS", f"Thành viên còn {n} công việc đang thực hiện, hãy phân công lại trước")
    m.trang_thai, m.ngay_roi = TrangThaiThanhVien.LEFT, today()
    audit(db, actor.ma_nd, "MEMBER_REMOVED", "du_an", p.ma_du_an, f"user={ma_nd}")


# ---- 1.5 mốc ----
def _check_ms_date(p: DuAn, d: date):
    if not (p.ngay_bat_dau <= d <= p.ngay_ket_thuc_du_kien):
        raise invalid("MILESTONE_OUT_OF_RANGE", "Hạn mốc phải nằm trong thời gian dự án")


def create_milestone(db, actor, p, d) -> MocDuAn:
    ensure_writable(p); _check_ms_date(p, d.han_hoan_thanh)
    if db.scalar(select(MocDuAn.ma_moc).where(MocDuAn.ma_du_an == p.ma_du_an, func.lower(MocDuAn.ten_moc) == d.ten_moc.lower())):
        raise conflict("DUPLICATE_MILESTONE", "Tên mốc đã tồn tại trong dự án")
    m = MocDuAn(ma_du_an=p.ma_du_an, ten_moc=d.ten_moc, han_hoan_thanh=d.han_hoan_thanh); db.add(m); db.flush()
    audit(db, actor.ma_nd, "MILESTONE_CREATED", "moc_du_an", m.ma_moc, m.ten_moc)
    return m


def update_milestone(db, actor, p, m: MocDuAn, d) -> MocDuAn:
    ensure_writable(p)
    data = d.model_dump(exclude_unset=True)
    if data.get("han_hoan_thanh"):
        _check_ms_date(p, data["han_hoan_thanh"]); m.han_hoan_thanh = data["han_hoan_thanh"]
    if data.get("ten_moc"):
        m.ten_moc = data["ten_moc"]
    if data.get("trang_thai"):
        if data["trang_thai"] == TrangThaiMoc.ACHIEVED:
            n = db.scalar(select(func.count()).select_from(Task).where(Task.ma_moc == m.ma_moc, Task.trang_thai.in_(OPEN_TASK)))
            if n:
                raise conflict("MILESTONE_HAS_OPEN_TASKS", f"Còn {n} công việc của mốc chưa hoàn thành")
        m.trang_thai = data["trang_thai"]
    audit(db, actor.ma_nd, "MILESTONE_UPDATED", "moc_du_an", m.ma_moc, ",".join(data))
    return m


def delete_milestone(db, actor, p, m: MocDuAn):
    ensure_writable(p)
    if db.scalar(select(func.count()).select_from(Task).where(Task.ma_moc == m.ma_moc)):
        raise conflict("MILESTONE_HAS_TASKS", "Mốc đang được gán cho công việc, không thể xóa")
    db.delete(m)
    audit(db, actor.ma_nd, "MILESTONE_DELETED", "moc_du_an", m.ma_moc)


def overview(db, p: DuAn) -> dict:
    tasks = db.execute(select(Task.trang_thai, func.count()).where(Task.ma_du_an == p.ma_du_an).group_by(Task.trang_thai)).all()
    by = {s.value: n for s, n in tasks}
    total = sum(v for k, v in by.items() if k != "CANCELLED")
    done = by.get("DONE", 0)
    hours = db.scalar(select(func.coalesce(func.sum(NhatKyGioLam.so_gio), 0)).join(Task, Task.ma_cv == NhatKyGioLam.ma_cv)
                      .where(Task.ma_du_an == p.ma_du_an))
    ms = db.execute(select(MocDuAn.trang_thai, func.count()).where(MocDuAn.ma_du_an == p.ma_du_an).group_by(MocDuAn.trang_thai)).all()
    overdue = db.scalar(select(func.count()).select_from(Task).where(Task.ma_du_an == p.ma_du_an, Task.trang_thai.in_(OPEN_TASK),
                                                                      Task.han_hoan_thanh < today()))
    members = db.scalar(select(func.count()).select_from(ThanhVienDuAn).where(
        ThanhVienDuAn.ma_du_an == p.ma_du_an, ThanhVienDuAn.trang_thai == TrangThaiThanhVien.ACTIVE))
    budget = float(p.ngan_sach_gio)
    return {"ma_du_an": p.ma_du_an, "ten_du_an": p.ten_du_an, "trang_thai": p.trang_thai.value,
            "task_theo_trang_thai": by, "tong_task": total, "task_hoan_thanh": done,
            "ty_le_hoan_thanh": round(done / total * 100, 1) if total else 0.0, "task_tre_han": overdue,
            "so_thanh_vien": members, "gio_thuc_te": float(hours), "ngan_sach_gio": budget,
            "ty_le_su_dung_ngan_sach_gio": round(float(hours) / budget * 100, 1) if budget else None,
            "moc_theo_trang_thai": {s.value: n for s, n in ms},
            "so_ngay_con_lai": (p.ngay_ket_thuc_du_kien - today()).days}
