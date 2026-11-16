from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, require_sys
from app.enums import TrangThaiDuAn, TrangThaiThanhVien
from app.errors import not_found
from app.models import DuAn, MocDuAn, NguoiDung, ThanhVienDuAn
from app.schemas.common import Msg, Page
from app.schemas.project import *
from app.services import projects as svc
from app.services.access import require_project_perm, system_perms
from app.services.common import paginate

router = APIRouter(prefix="/projects", tags=["1. Quản lý dự án"])


@router.post("", response_model=ProjectOut, status_code=201, summary="1.1 Tạo dự án (Lệnh khởi tạo DA)")
def create_project(body: ProjectCreate, user=Depends(require_sys("project.create")), db: Session = Depends(get_db)):
    return svc.create_project(db, user, body)


@router.get("", response_model=Page[ProjectOut], summary="Danh sách dự án của tôi (hoặc tất cả nếu có project.read_all)")
def list_projects(q: str | None = None, trang_thai: TrangThaiDuAn | None = None,
                  page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
                  user: NguoiDung = Depends(current_user), db: Session = Depends(get_db)):
    st = select(DuAn).order_by(DuAn.ma_du_an.desc())
    if "project.read_all" not in system_perms(db, user):
        st = st.join(ThanhVienDuAn, ThanhVienDuAn.ma_du_an == DuAn.ma_du_an).where(
            ThanhVienDuAn.ma_nguoi_dung == user.ma_nd, ThanhVienDuAn.trang_thai == TrangThaiThanhVien.ACTIVE)
    if q:
        st = st.where(DuAn.ten_du_an.ilike(f"%{q}%"))
    if trang_thai:
        st = st.where(DuAn.trang_thai == trang_thai)
    return paginate(db, st, page, size)


@router.get("/{ma_da}", response_model=ProjectOut)
def get_project(ma_da: int, user=Depends(current_user), db: Session = Depends(get_db)):
    return require_project_perm(db, user, ma_da, "project.read")


@router.patch("/{ma_da}", response_model=ProjectOut, summary="1.2 Cập nhật thông tin dự án")
def update_info(ma_da: int, body: ProjectInfoUpdate, user=Depends(current_user), db: Session = Depends(get_db)):
    return svc.update_info(db, user, require_project_perm(db, user, ma_da, "project.update"), body)


@router.put("/{ma_da}/goals", response_model=ProjectOut, summary="1.3 Thiết lập mục tiêu & thời gian dự án")
def update_goals(ma_da: int, body: ProjectGoalsUpdate, user=Depends(current_user), db: Session = Depends(get_db)):
    return svc.update_goals(db, user, require_project_perm(db, user, ma_da, "project.update"), body)


@router.patch("/{ma_da}/status", response_model=ProjectOut, summary="1.5 Cập nhật trạng thái dự án")
def change_status(ma_da: int, body: StatusIn, user=Depends(current_user), db: Session = Depends(get_db)):
    return svc.change_status(db, user, require_project_perm(db, user, ma_da, "project.update"), body.trang_thai)


@router.post("/{ma_da}/close", response_model=ProjectOut, summary="1.6 Đóng dự án (Yêu cầu đóng DA từ Ban giám đốc)")
def close_project(ma_da: int, body: CloseIn | None = None, user=Depends(current_user), db: Session = Depends(get_db)):
    p = require_project_perm(db, user, ma_da, "project.close")
    body = body or CloseIn()
    return svc.close_project(db, user, p, body.force, body.ghi_chu)


@router.get("/{ma_da}/my-permissions", summary="Quyền của tôi trong dự án (để ẩn/hiện nút trên UI)")
def my_permissions(ma_da: int, user=Depends(current_user), db: Session = Depends(get_db)):
    from app.services.access import project_perms, project_role_code
    require_project_perm(db, user, ma_da, "project.read")
    return {"vai_tro": project_role_code(db, ma_da, user.ma_nd), "permissions": sorted(project_perms(db, user, ma_da))}


@router.get("/{ma_da}/overview", summary="1.5 Báo cáo trạng thái tổng quan")
def overview(ma_da: int, user=Depends(current_user), db: Session = Depends(get_db)):
    return svc.overview(db, require_project_perm(db, user, ma_da, "project.read"))


# ---- 1.4 thành viên ----
@router.get("/{ma_da}/members", response_model=list[MemberOut])
def list_members(ma_da: int, include_left: bool = False, user=Depends(current_user), db: Session = Depends(get_db)):
    require_project_perm(db, user, ma_da, "project.read")
    st = select(ThanhVienDuAn).where(ThanhVienDuAn.ma_du_an == ma_da).order_by(ThanhVienDuAn.ma_nguoi_dung)
    if not include_left:
        st = st.where(ThanhVienDuAn.trang_thai == TrangThaiThanhVien.ACTIVE)
    return [svc.member_out(db, m) for m in db.scalars(st)]


@router.post("/{ma_da}/members", response_model=MemberOut, status_code=201, summary="1.4 Thêm thành viên & phân quyền")
def add_member(ma_da: int, body: MemberAdd, user=Depends(current_user), db: Session = Depends(get_db)):
    p = require_project_perm(db, user, ma_da, "member.manage")
    return svc.member_out(db, svc.add_member(db, user, p, body))


@router.patch("/{ma_da}/members/{ma_nd}", response_model=MemberOut, summary="1.4 Đổi vai trò thành viên")
def change_role(ma_da: int, ma_nd: int, body: MemberRoleUpdate, user=Depends(current_user), db: Session = Depends(get_db)):
    p = require_project_perm(db, user, ma_da, "member.manage")
    return svc.member_out(db, svc.change_member_role(db, user, p, ma_nd, body.vai_tro))


@router.delete("/{ma_da}/members/{ma_nd}", response_model=Msg, summary="1.4 Xóa thành viên khỏi dự án")
def remove_member(ma_da: int, ma_nd: int, user=Depends(current_user), db: Session = Depends(get_db)):
    svc.remove_member(db, user, require_project_perm(db, user, ma_da, "member.manage"), ma_nd)
    return Msg()


# ---- 1.5 mốc ----
def _ms(db, ma_da, ma_moc) -> MocDuAn:
    m = db.get(MocDuAn, ma_moc)
    if not m or m.ma_du_an != ma_da:
        raise not_found("MILESTONE_NOT_FOUND", "Mốc không tồn tại")
    return m


@router.get("/{ma_da}/milestones", response_model=list[MilestoneOut])
def list_milestones(ma_da: int, user=Depends(current_user), db: Session = Depends(get_db)):
    require_project_perm(db, user, ma_da, "project.read")
    return db.scalars(select(MocDuAn).where(MocDuAn.ma_du_an == ma_da).order_by(MocDuAn.han_hoan_thanh)).all()


@router.post("/{ma_da}/milestones", response_model=MilestoneOut, status_code=201, summary="1.5 Thiết lập mốc")
def create_milestone(ma_da: int, body: MilestoneIn, user=Depends(current_user), db: Session = Depends(get_db)):
    return svc.create_milestone(db, user, require_project_perm(db, user, ma_da, "milestone.manage"), body)


@router.patch("/{ma_da}/milestones/{ma_moc}", response_model=MilestoneOut)
def update_milestone(ma_da: int, ma_moc: int, body: MilestoneUpdate, user=Depends(current_user), db: Session = Depends(get_db)):
    p = require_project_perm(db, user, ma_da, "milestone.manage")
    return svc.update_milestone(db, user, p, _ms(db, ma_da, ma_moc), body)


@router.delete("/{ma_da}/milestones/{ma_moc}", response_model=Msg)
def delete_milestone(ma_da: int, ma_moc: int, user=Depends(current_user), db: Session = Depends(get_db)):
    p = require_project_perm(db, user, ma_da, "milestone.manage")
    svc.delete_milestone(db, user, p, _ms(db, ma_da, ma_moc))
    return Msg()
