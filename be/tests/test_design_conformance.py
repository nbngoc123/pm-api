"""Đối chiếu CHẶT với thiết kế.
ERD: mỗi bảng phải có (a) đủ thuộc tính, (b) đúng khóa chính, (c) đủ khóa ngoại theo từng đường nối, (d) cột [rỗng] cho phép NULL,
     (e) KHÔNG có cột nào ngoài ERD trừ khi được khai báo trong EXTRA (danh sách mở rộng có chủ đích).
DFD: mỗi process có endpoint tương ứng."""
import pytest

import app.models  # noqa
from app.database import Base
from app.main import API, create_app

T = Base.metadata.tables

# bảng: (thuộc tính ERD [gồm cột sinh ra từ quan hệ], khóa chính, [(cột FK..., bảng cha)], cột [rỗng], EXTRA có chủ đích)
ERD = {
    "du_an": (["ma_du_an", "ten_du_an", "muc_tieu", "ngay_bat_dau", "ngay_ket_thuc_du_kien", "ngan_sach_gio", "trang_thai", "ngay_dong", "ma_quan_ly"],
              ["ma_du_an"], [(("ma_quan_ly",), "quan_ly")], ["ngay_dong"], ["version", "created_by", "created_at"]),
    "thanh_vien_du_an": (["ma_du_an", "ma_nguoi_dung", "ma_vai_tro", "ngay_tham_gia", "ngay_roi", "trang_thai"], ["ma_du_an", "ma_nguoi_dung"],
                         [(("ma_du_an",), "du_an"), (("ma_nguoi_dung",), "nguoi_dung"), (("ma_vai_tro",), "vai_tro")], ["ngay_roi"], []),
    "moc_du_an": (["ma_moc", "ten_moc", "ma_du_an", "han_hoan_thanh", "trang_thai"], ["ma_moc"], [(("ma_du_an",), "du_an")], [], []),
    "epic": (["ma_epic", "ten_epic", "mo_ta", "trang_thai", "ma_du_an"], ["ma_epic"], [(("ma_du_an",), "du_an")], [], []),
    "task": (["ma_cv", "ten_cv", "mo_ta", "trang_thai", "ty_le_hoan_thanh", "ngay_bat_dau_du_kien", "han_hoan_thanh", "ma_nguoi_tao", "ma_moc", "ma_du_an", "ma_epic"],
             ["ma_cv"], [(("ma_moc",), "moc_du_an"), (("ma_epic",), "epic"), (("ma_nguoi_tao",), "nguoi_dung"), (("ma_du_an",), "du_an")], [],
             ["uu_tien", "gio_du_kien", "hoan_thanh_luc", "created_at", "updated_at", "version"]),
    "sub_task": (["ma_subtask", "ten_subtask", "mo_ta", "trang_thai", "ma_cv"], ["ma_subtask"], [(("ma_cv",), "task")], [], []),
    "ke_hoach_goc": (["ma_cv", "ngay_bat_dau_goc", "ngay_ket_thuc_goc", "gio_du_kien_goc", "chi_phi_ke_hoach_goc"], ["ma_cv"], [(("ma_cv",), "task")], [], ["khoa_luc"]),
    "tep_dinh_kem": (["ma_tep", "thoi_diem_tai", "duong_dan", "ma_cv", "ma_nguoi_tai", "ten_tep"], ["ma_tep"],
                     [(("ma_cv",), "task"), (("ma_nguoi_tai",), "nguoi_dung")], [], ["kich_thuoc"]),
    "phan_cong": (["ma_cv", "ma_nd", "trang_thai_phan_cong", "ngay_giao", "gio_du_kien", "ma_nguoi_giao"], ["ma_cv", "ma_nd"],
                  [(("ma_cv",), "task"), (("ma_nd",), "nhan_vien"),
                   (("ma_nguoi_giao",), "nguoi_dung")],            # ⚠ ERD: quan_ly, DFD 2.3: Trưởng nhóm ⇒ xem TRACEABILITY §3 (D1)
                  [], []),
    "nhat_ky_gio_lam": (["ma_nk", "ma_cv", "ma_nd", "bat_dau", "ket_thuc", "noi_dung", "chi_phi_thuc_te"], ["ma_nk"],
                        [(("ma_cv",), "task"), (("ma_nd",), "nhan_vien")], [], ["so_gio"]),
    "xet_duyet_cong_viec": (["ma_duyet", "ma_cv", "ma_nguoi_duyet", "ket_qua", "nhan_xet", "thoi_diem_duyet"], ["ma_duyet"],
                            [(("ma_cv",), "task"), (("ma_nguoi_duyet",), "nguoi_dung")], [], []),   # ⚠ ERD: quan_ly, DFD 2.6: Trưởng nhóm (D1)
    "nguoi_dung": (["ma_nd", "email", "ho_ten", "ma_vai_tro_he_thong", "trang_thai"], ["ma_nd"], [(("ma_vai_tro_he_thong",), "vai_tro")], [],
                   ["mat_khau_hash", "loai", "token_version", "so_lan_dang_nhap_sai", "khoa_den", "created_at"]),
    "quan_ly": (["ma_nd"], ["ma_nd"], [(("ma_nd",), "nguoi_dung")], [], []),
    "nhan_vien": (["ma_nd"], ["ma_nd"], [(("ma_nd",), "nguoi_dung")], [], ["ma_quan_ly", "don_gia_gio"]),
    "vai_tro": (["ma_vai_tro", "ten_vai_tro", "pham_vi"], ["ma_vai_tro"], [], [], ["code"]),
    "quyen": (["ma_quyen", "ten_quyen", "mo_ta"], ["ma_quyen"], [], [], ["code"]),
    "vai_tro_quyen": (["ma_vai_tro", "ma_quyen"], ["ma_vai_tro", "ma_quyen"], [(("ma_vai_tro",), "vai_tro"), (("ma_quyen",), "quyen")], [], []),
    "nhat_ky_he_thong": (["ma_log", "ma_nguoi_thuc_hien", "thoi_diem", "loai_su_kien", "noi_dung", "ma_du_an"], ["ma_log"],
                         [(("ma_nguoi_thuc_hien",), "nguoi_dung"), (("ma_du_an",), "du_an")], [], ["doi_tuong", "ma_doi_tuong"]),
    "quy_dinh_vi_pham": (["ma_qd", "ten_quy_dinh", "tu_ngay", "den_ngay", "diem_tru"], ["ma_qd"], [], ["den_ngay"], []),
    "vi_pham": (["ma_vp", "ma_cv", "ma_nd", "ma_nguoi_lap", "ma_qd", "noi_dung", "trang_thai", "thoi_diem", "ngay_xu_ly", "ket_luan", "ma_nguoi_xu_ly", "ma_ky_ap_dung"],
                ["ma_vp"], [(("ma_cv",), "task"), (("ma_qd",), "quy_dinh_vi_pham"), (("ma_nd",), "nhan_vien"), (("ma_nguoi_xu_ly",), "quan_ly"),
                            (("ma_ky_ap_dung",), "ky_kpi"),
                            (("ma_nguoi_lap",), "nguoi_dung")],      # ⚠ ERD: quan_ly, DFD 5.1: Trưởng nhóm (D1)
                ["ngay_xu_ly", "ket_luan", "ma_nguoi_xu_ly", "ma_ky_ap_dung"], ["han_giai_trinh"]),
    "giai_trinh": (["ma_gt", "ma_vp", "noi_dung", "thoi_diem_gui", "duong_dan_bang_chung"], ["ma_gt"], [(("ma_vp",), "vi_pham")], ["duong_dan_bang_chung"], []),
    "tieu_chi_kpi": (["ma_tieu_chi", "ten_tieu_chi", "mo_ta_cach_tinh", "don_vi"], ["ma_tieu_chi"], [], [], ["nguon_du_lieu"]),
    "cau_hinh_kpi": (["ma_tieu_chi", "ma_ky", "trong_so", "chi_tieu"], ["ma_ky", "ma_tieu_chi"], [(("ma_tieu_chi",), "tieu_chi_kpi"), (("ma_ky",), "ky_kpi")], [], []),
    "ky_kpi": (["ma_ky", "ma_du_an", "ten_ky", "tu_ngay", "den_ngay", "trang_thai"], ["ma_ky"], [(("ma_du_an",), "du_an")], [], []),
    "chi_tiet_kpi": (["ma_nguoi_dung", "ma_ky", "ma_tieu_chi", "gia_tri_xac_nhan", "ghi_chu"], ["ma_nguoi_dung", "ma_ky", "ma_tieu_chi"],
                     [(("ma_ky", "ma_tieu_chi"), "cau_hinh_kpi"), (("ma_ky", "ma_nguoi_dung"), "danh_gia_kpi")], [], ["gia_tri_tu_dong", "gia_tri_thu_cong"]),
    "danh_gia_kpi": (["ma_ky", "ma_nguoi_dung", "ma_nguoi_duyet", "ngay_duyet", "ngay_xac_nhan", "trang_thai"], ["ma_ky", "ma_nguoi_dung"],
                     [(("ma_ky",), "ky_kpi"), (("ma_nguoi_dung",), "nguoi_dung"), (("ma_nguoi_duyet",), "quan_ly")], ["ma_nguoi_duyet", "ngay_duyet", "ngay_xac_nhan"],
                     ["diem_goc", "diem_tru", "diem_tong", "nhan_xet"]),
}
EXTENSION_TABLES = {"thong_bao", "chi_so_du_an"}       # DFD 3.2 / 3.3 cần nhưng ERD không có


@pytest.mark.parametrize("table", sorted(ERD))
def test_erd_entity_strict(table):
    cols_erd, pk, fks, nullable, extra = ERD[table]
    t = T[table]
    cols = {c.name for c in t.columns}
    assert set(cols_erd) <= cols, f"{table} thiếu thuộc tính ERD: {set(cols_erd) - cols}"
    assert not cols - set(cols_erd) - set(extra), f"{table} có cột ngoài ERD chưa khai báo: {cols - set(cols_erd) - set(extra)}"
    assert [c.name for c in t.primary_key.columns] == pk, f"{table} sai khóa chính"
    have = {(tuple(c.parent.name for c in f.elements), f.elements[0].column.table.name) for f in t.foreign_key_constraints}
    assert not set(fks) - have, f"{table} thiếu khóa ngoại: {set(fks) - have}"
    for c in nullable:
        assert t.c[c].nullable, f"{table}.{c} là [rỗng] trong ERD nên phải cho phép NULL"
    for c in t.columns:                                   # bản số 1–N: cột FK đơn không được UNIQUE (trừ PK = quan hệ 1–1)
        if c.foreign_keys and not c.primary_key:
            assert not c.unique, f"{table}.{c.name} UNIQUE làm sai bản số N"


def test_only_declared_extension_tables_exist():
    assert set(T) - set(ERD) == EXTENSION_TABLES


# --- DFD: process -> (HTTP method, path) ---
DFD = {
    "1.1 Tạo dự án": ("POST", "/projects"),
    "1.2 Cập nhật dự án": ("PATCH", "/projects/{ma_da}"),
    "1.3 Thiết lập mục tiêu & thời gian": ("PUT", "/projects/{ma_da}/goals"),
    "1.4 Quản lý thành viên & phân quyền": ("POST", "/projects/{ma_da}/members"),
    "1.5 Thiết lập mốc & trạng thái": ("POST", "/projects/{ma_da}/milestones"),
    "1.5b Báo cáo trạng thái tổng quan": ("GET", "/projects/{ma_da}/overview"),
    "1.6 Đóng dự án": ("POST", "/projects/{ma_da}/close"),
    "2.1 Tạo công việc": ("POST", "/projects/{ma_da}/tasks"),
    "2.2 Cập nhật công việc": ("PATCH", "/tasks/{ma_cv}"),
    "2.3 Phân công": ("POST", "/tasks/{ma_cv}/assignments"),
    "2.4 Ưu tiên & thời hạn": ("GET", "/projects/{ma_da}/tasks/prioritized"),
    "2.5 Theo dõi trạng thái": ("POST", "/tasks/{ma_cv}/transition"),
    "2.6 Xét duyệt": ("POST", "/tasks/{ma_cv}/review"),
    "2.7 Ghi nhận thời gian": ("POST", "/tasks/{ma_cv}/timesheets"),
    "3.1 Giám sát & theo dõi (EVM)": ("GET", "/projects/{ma_da}/progress/evm"),
    "3.1b Burn-down": ("GET", "/projects/{ma_da}/progress/burndown"),
    "3.2 Cảnh báo rủi ro & tự động hóa": ("POST", "/alerts/scan"),
    "3.3 Lưu vết hệ thống": ("GET", "/audit-logs"),
    "4.1 Cấu hình & phân bổ KPI": ("PUT", "/kpi/periods/{ma_ky}/config"),
    "4.2 Thu thập & tính toán tự động": ("POST", "/kpi/periods/{ma_ky}/calculate"),
    "4.3 Đánh giá & phê duyệt KPI": ("POST", "/kpi/periods/{ma_ky}/evaluations/{ma_nd}/approve"),
    "4.3b Thành viên xác nhận kết quả": ("POST", "/kpi/periods/{ma_ky}/evaluations/{ma_nd}/confirm"),
    "5.1 Ghi nhận & phân loại vi phạm": ("POST", "/violations"),
    "5.2 Giải trình & xử lý khiếu nại": ("POST", "/violations/{ma_vp}/explanations"),
    "5.2b Kết luận xử lý": ("POST", "/violations/{ma_vp}/conclude"),
    "6.3 Dashboard cá nhân": ("GET", "/dashboard/me"),
    "6.4 Báo cáo portfolio": ("GET", "/reports/portfolio"),
    "6.5 Xuất báo cáo": ("GET", "/exports"),
}


@pytest.mark.parametrize("process", sorted(DFD))
def test_dfd_process_has_endpoint(process):
    method, path = DFD[process]
    paths = create_app().openapi()["paths"]
    assert API + path in paths and method.lower() in paths[API + path], f"{process} chưa có {method} {path}"
