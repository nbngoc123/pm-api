"""Dữ liệu khởi tạo: quyền, vai trò (hệ thống + dự án), ma trận vai trò–quyền, tiêu chí KPI, quy định vi phạm, admin."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import LoaiNguoiDung, NguonDuLieuKPI, PhamVi, ProjRole, SysRole
from app.models import (NguoiDung, NhanVien, QuanLy, Quyen, QuyDinhViPham, TieuChiKPI, VaiTro, VaiTroQuyen)
from app.security import hash_password

PERMISSIONS = {
    # cấp hệ thống
    "user.manage": "Quản lý người dùng", "project.create": "Khởi tạo dự án", "project.read_all": "Xem mọi dự án",
    "project.close": "Đóng dự án", "report.portfolio": "Báo cáo portfolio đa dự án", "audit.read": "Xem nhật ký hệ thống",
    "alert.run": "Chạy quét cảnh báo", "kpi.criteria.manage": "Quản lý tiêu chí KPI",
    "violation.rule.manage": "Quản lý quy định vi phạm",
    # cấp dự án
    "project.read": "Xem dự án", "project.update": "Cập nhật dự án", "member.manage": "Quản lý thành viên",
    "milestone.manage": "Quản lý mốc", "task.create": "Tạo công việc", "task.update": "Sửa công việc",
    "task.assign": "Phân công", "task.review": "Xét duyệt công việc", "task.transition": "Cập nhật trạng thái công việc",
    "timesheet.log": "Ghi giờ làm", "kpi.period.manage": "Quản lý kỳ KPI", "kpi.approve": "Phê duyệt KPI",
    "violation.create": "Lập vi phạm", "violation.conclude": "Kết luận vi phạm", "report.project": "Báo cáo dự án",
    "progress.manage": "Quản lý baseline/tiến độ", "report.export": "Xuất báo cáo (DFD 6.5: chỉ Quản lý dự án)",
}
SYSTEM_PERMS = {"user.manage", "project.create", "project.read_all", "project.close", "report.portfolio", "audit.read",
                "alert.run", "kpi.criteria.manage", "violation.rule.manage"}
_PM = {"project.read", "project.update", "member.manage", "milestone.manage", "task.create", "task.update", "task.assign",
       "task.review", "task.transition", "timesheet.log", "kpi.period.manage", "kpi.approve", "violation.create",
       "violation.conclude", "report.project", "report.export", "progress.manage"}
_TL = {"project.read", "task.create", "task.update", "task.assign", "task.review", "task.transition", "timesheet.log",
       "violation.create"}      # DFD: báo cáo EVM/xuất file chỉ đến Quản lý dự án, không đến Trưởng nhóm
_MEM = {"project.read", "task.transition", "timesheet.log"}

ROLES = {
    SysRole.ADMIN: ("Quản trị hệ thống", PhamVi.SYSTEM, set(PERMISSIONS)),
    SysRole.DIRECTOR: ("Ban giám đốc", PhamVi.SYSTEM, {"project.create", "project.read_all", "project.close",
                                                        "report.portfolio", "audit.read"}),
    SysRole.MANAGER: ("Quản lý", PhamVi.SYSTEM, {"kpi.criteria.manage", "violation.rule.manage"}),
    SysRole.EMPLOYEE: ("Nhân viên", PhamVi.SYSTEM, set()),
    ProjRole.PM: ("Quản lý dự án", PhamVi.PROJECT, _PM),
    ProjRole.TEAM_LEAD: ("Trưởng nhóm", PhamVi.PROJECT, _TL),
    ProjRole.MEMBER: ("Thành viên", PhamVi.PROJECT, _MEM),
}
DEFAULT_CRITERIA = [
    ("Hoàn thành công việc", "Tỷ lệ task DONE / task được giao trong kỳ", "%", NguonDuLieuKPI.TASK_COMPLETION),
    ("Đúng hạn", "Tỷ lệ task hoàn thành không trễ deadline", "%", NguonDuLieuKPI.ON_TIME_RATE),
    ("Sử dụng giờ", "Giờ thực tế / giờ dự kiến", "%", NguonDuLieuKPI.HOURS_UTILIZATION),
    ("Đánh giá của quản lý", "Hiệu suất thô do quản lý chấm (0-100)", "điểm", NguonDuLieuKPI.MANUAL),
]


def seed(db: Session) -> None:
    perms = {p.code: p for p in db.scalars(select(Quyen))}
    for code, name in PERMISSIONS.items():
        if code not in perms:
            perms[code] = Quyen(code=code, ten_quyen=name); db.add(perms[code])
    db.flush()
    roles = {r.code: r for r in db.scalars(select(VaiTro))}
    for code, (name, scope, pset) in ROLES.items():
        r = roles.get(code.value)
        if not r:
            r = roles[code.value] = VaiTro(code=code.value, ten_vai_tro=name, pham_vi=scope); db.add(r); db.flush()
        have = {x.ma_quyen for x in db.scalars(select(VaiTroQuyen).where(VaiTroQuyen.ma_vai_tro == r.ma_vai_tro))}
        for pc in pset:
            if perms[pc].ma_quyen not in have:
                db.add(VaiTroQuyen(ma_vai_tro=r.ma_vai_tro, ma_quyen=perms[pc].ma_quyen))
    if not db.scalar(select(TieuChiKPI).limit(1)):
        for n, d, u, s in DEFAULT_CRITERIA:
            db.add(TieuChiKPI(ten_tieu_chi=n, mo_ta_cach_tinh=d, don_vi=u, nguon_du_lieu=s))
    if not db.scalar(select(QuyDinhViPham).limit(1)):
        for n, pts in [("Trễ deadline", 5), ("Lỗi chất lượng nghiêm trọng", 10), ("Không cập nhật giờ làm", 2)]:
            db.add(QuyDinhViPham(ten_quy_dinh=n, diem_tru=pts, tu_ngay=date(2020, 1, 1)))
    if not db.scalar(select(NguoiDung).where(NguoiDung.email == settings.bootstrap_admin_email)):
        u = NguoiDung(email=settings.bootstrap_admin_email, ho_ten="System Admin", loai=LoaiNguoiDung.QUAN_LY,
                      mat_khau_hash=hash_password(settings.bootstrap_admin_password),
                      ma_vai_tro_he_thong=roles[SysRole.ADMIN.value].ma_vai_tro)
        db.add(u); db.flush(); db.add(QuanLy(ma_nd=u.ma_nd))
    db.flush()
