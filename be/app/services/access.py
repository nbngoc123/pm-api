"""RBAC 2 tầng: quyền hệ thống (vai_tro_he_thong) ∪ quyền dự án (thanh_vien_du_an.ma_vai_tro)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import TrangThaiThanhVien
from app.errors import forbidden, not_found
from app.models import DuAn, NguoiDung, Quyen, Task, ThanhVienDuAn, VaiTro, VaiTroQuyen


def role_perms(db: Session, ma_vai_tro: int) -> set[str]:
    return set(db.scalars(select(Quyen.code).join(VaiTroQuyen, VaiTroQuyen.ma_quyen == Quyen.ma_quyen)
                          .where(VaiTroQuyen.ma_vai_tro == ma_vai_tro)))


def system_perms(db: Session, user: NguoiDung) -> set[str]:
    return role_perms(db, user.ma_vai_tro_he_thong)


def system_role_code(db: Session, user: NguoiDung) -> str:
    return db.get(VaiTro, user.ma_vai_tro_he_thong).code


def membership(db: Session, ma_da: int, ma_nd: int, active_only=True) -> ThanhVienDuAn | None:
    m = db.get(ThanhVienDuAn, (ma_da, ma_nd))
    if m and active_only and m.trang_thai != TrangThaiThanhVien.ACTIVE:
        return None
    return m


def project_perms(db: Session, user: NguoiDung, ma_da: int) -> set[str]:
    perms = system_perms(db, user)
    m = membership(db, ma_da, user.ma_nd)
    if m:
        perms |= role_perms(db, m.ma_vai_tro)
    if "project.read_all" in perms:
        perms.add("project.read")
    return perms


def project_role_code(db: Session, ma_da: int, ma_nd: int) -> str | None:
    m = membership(db, ma_da, ma_nd)
    return db.get(VaiTro, m.ma_vai_tro).code if m else None


def require_project_perm(db: Session, user: NguoiDung, ma_da: int, perm: str) -> DuAn:
    p = db.get(DuAn, ma_da)
    if not p:
        raise not_found("PROJECT_NOT_FOUND", "Dự án không tồn tại")
    perms = project_perms(db, user, ma_da)
    if "project.read" not in perms:           # không phải thành viên -> che giấu sự tồn tại
        raise not_found("PROJECT_NOT_FOUND", "Dự án không tồn tại")
    if perm not in perms:
        raise forbidden()
    return p


def require_task_perm(db: Session, user: NguoiDung, ma_cv: int, perm: str) -> tuple[Task, DuAn]:
    t = db.get(Task, ma_cv)
    if not t:
        raise not_found("TASK_NOT_FOUND", "Công việc không tồn tại")
    return t, require_project_perm(db, user, t.ma_du_an, perm)


def is_direct_manager(db: Session, manager_id: int, employee_id: int) -> bool:
    from app.models import NhanVien
    nv = db.get(NhanVien, employee_id)
    return bool(nv and nv.ma_quan_ly == manager_id)
