# Đối chiếu thiết kế ↔ code ↔ test

> Đã rà lại toàn bộ 8 sơ đồ (DFD mức 0, 6 DFD mức 1, ERD). Bộ test đối chiếu (`tests/test_design_conformance.py`) kiểm **chặt**:
> mỗi bảng ERD phải có đúng khóa chính, đủ khóa ngoại theo từng đường nối, cột `[rỗng]` cho phép NULL, **và không được có cột nào ngoài ERD
> trừ khi khai báo trong `EXTRA`**. Muốn thêm cột/bảng ngoài thiết kế buộc phải sửa file đó ⇒ không thể lệch âm thầm.

## 1. Kho dữ liệu DFD → bảng
| Kho | Bảng |
|---|---|
| D1 Hồ sơ dự án | `du_an`, `thanh_vien_du_an`, `moc_du_an`, `epic`, `ke_hoach_goc` (đường cơ sở), `nhat_ky_he_thong` (log truy vết), `chi_so_du_an` |
| D2 Hồ sơ công việc | `task`, `sub_task`, `tep_dinh_kem`, `phan_cong`, `xet_duyet_cong_viec` |
| D3 Nhật ký giờ làm | `nhat_ky_gio_lam` |
| D4 Hồ sơ KPI | `tieu_chi_kpi`, `ky_kpi`, `cau_hinh_kpi`, `danh_gia_kpi`, `chi_tiet_kpi` |
| D5 Hồ sơ vi phạm | `quy_dinh_vi_pham`, `vi_pham`, `giai_trinh` |
| (ngoài DFD) | `nguoi_dung`, `quan_ly`, `nhan_vien`, `vai_tro`, `quyen`, `vai_tro_quyen`, `thong_bao` |

## 2. ERD: đã sửa sau lần rà soát này
| # | Lỗi trước đó | Sửa |
|---|---|---|
| 1 | `phan_cong` dùng khóa thay thế `ma_pc` | **Khóa ghép (MaCV, MaND)** đúng ERD; giao lại = kích hoạt lại bản ghi |
| 2 | `danh_gia_kpi` dùng `ma_dg` | **Khóa ghép (Mã kỳ, Mã người dùng)**; API đổi thành `/kpi/periods/{ma_ky}/evaluations/{ma_nd}/…` |
| 3 | `giai_trinh` UNIQUE theo `ma_vp` (thành 1–1) | **N–1** như ERD: nộp được nhiều đơn bổ sung trước khi kết luận |
| 4 | Thiếu quan hệ DỰ ÁN 1–N NHẬT KÝ HỆ THỐNG ("Phát sinh") | Thêm `nhat_ky_he_thong.ma_du_an` (tự suy ra từ đối tượng); lọc `GET /audit-logs?ma_da=` |
| 5 | `chi_tiet_kpi` thiếu FK tới CẤU HÌNH KPI ("Áp dụng") và ĐÁNH GIÁ KPI ("Gồm") | Thêm 2 **FK ghép** |
| 6 | Cột FK trỏ `nguoi_dung` thay vì `nhan_vien`/`quan_ly` | `phan_cong.ma_nd`, `nhat_ky_gio_lam.ma_nd`, `vi_pham.ma_nd` → **nhan_vien**; `vi_pham.ma_nguoi_xu_ly`, `danh_gia_kpi.ma_nguoi_duyet` → **quan_ly** (kèm kiểm tra ở service, mã lỗi `*_MUST_BE_EMPLOYEE`, `MANAGER_ONLY`) |

## 3. ⚠ Chỗ chính thiết kế tự mâu thuẫn – **cần team quyết, tôi không tự chọn thay**
| # | ERD nói | DFD nói | Hiện code làm |
|---|---|---|---|
| D1 | `ma_nguoi_giao` (PHÂN CÔNG), `ma_nguoi_duyet` (XÉT DUYỆT), `ma_nguoi_lap` (VI PHẠM) là **QUẢN LÝ** | 2.3 / 2.6 / 5.1: **Trưởng nhóm** giao việc, duyệt việc, gửi thông báo phạt | FK trỏ `nguoi_dung` (cho cả hai). **Cách thống nhất:** (a) coi Trưởng nhóm là người dùng loại `QUAN_LY` ⇒ đổi 3 FK sang `quan_ly` (nhưng khi đó TL không nhận việc/ghi giờ được vì ERD chỉ cho NHÂN VIÊN), hoặc (b) sửa ERD cho 3 quan hệ này nối NGƯỜI DÙNG |
| D2 | — | DFD mức 0 và mức 1 module 5 **không cân**: mức 0 vẽ "Danh sách chờ giải trình"/"Biên bản lỗi, Lệnh xử phạt" ở nhánh **Trưởng nhóm**, "Thông báo phạt, Cảnh báo"/"Đơn giải trình" ở nhánh **Thành viên**; mức 1 thì TL → 5.1 "Thông báo phạt", 5.1 → Thành viên "Danh sách chờ giải trình" | Code theo **mức 1** (chi tiết hơn) và gửi biên bản kết luận cho cả Thành viên lẫn người lập (TL) để thỏa cả hai |
| D3 | ĐÁNH GIÁ KPI **không có** cột điểm | 4.2→4.3 có "Bảng điểm tạm tính", 4.3→D4 "Bản ghi KPI mới" | Thêm `diem_goc, diem_tru, diem_tong, nhan_xet` (EXTRA có khai báo) |
| D4 | Không có quan hệ nhân viên ↔ quản lý trực tiếp | "Quản lý" nhập hiệu suất thô & duyệt KPI (4.0) nhưng không nói là ai | Thêm `nhan_vien.ma_quan_ly` (quản lý trực tiếp) – là **giả định của tôi**, xem §5 |

## 4. DFD → API (từng luồng)
| Process | Luồng dữ liệu (nhãn trên sơ đồ) → hiện thực |
|---|---|
| 1.1 | "Lệnh khởi tạo DA" `POST /projects` (quyền `project.create` = BGĐ) · "Dữ liệu dự án mới" ghi D1 |
| 1.2 / 1.3 | "Thông tin DA hiện tại/đã cập nhật" `PATCH /projects/{id}` · "Hoạch định mục tiêu" `PUT /goals` |
| 1.4 | "Danh sách nhân sự", "Quyền quản trị hệ thống" `/members` + `/my-permissions` |
| 1.5 | "Báo cáo trạng thái tổng quan" → BGĐ `GET /overview` (BGĐ có `project.read_all`) · `/milestones`, `PATCH /status` |
| 1.6 | "Yêu cầu đóng DA" `POST /close` (chỉ BGĐ/ADMIN) |
| 2.1 / 2.2 / 2.4 | "Bản ghi work item", "Thông tin task mới/hiện tại", "Mức độ ưu tiên thời hạn" `/tasks`, `/tasks/prioritized` |
| 2.3 | "Bản giao việc, mức độ ưu tiên" `POST /assignments` · "Thông tin ràng buộc phân quyền" = phải là thành viên dự án · **"Cảnh báo vượt ngân sách giờ" → trả `warnings[]` *và* thông báo cho Quản lý dự án** |
| 2.5 | "Bản cập nhật trạng thái, file đính kèm" `/transition`, `/progress`, `/attachments` |
| 2.6 | "Task cần duyệt", "Danh sách task cần duyệt" `GET /reviews/pending` + thông báo cho TL/PM · "Kết quả duyệt" `POST /review` |
| 2.7 | "Bản ghi timesheet", "Tổng giờ làm tích lũy" `POST /timesheets` (trả `tong_gio_tich_luy_*`) |
| 3.1 | "Dữ liệu trạng thái Work Item / giờ làm thực / kế hoạch gốc" → `GET /progress/evm`, `/burndown` · **"Tham số tính toán tiến độ" = `as_of`, `co_so=chi_phi|gio`** · báo cáo chỉ đến QLDA |
| 3.2 | "Nhắc nhở Deadline cá nhân" → Thành viên · **"Cảnh báo trễ hạn cục bộ" → Trưởng nhóm** (dự án chưa có TL thì dự phòng gửi PM) |
| 3.3 | "Lệnh sự kiện hệ thống" → `nhat_ky_he_thong` · "Bản ghi chỉ số DA" → `chi_so_du_an` |
| 4.1 | "Tiêu chí, Chỉ tiêu", "Khung tiêu chí" `/kpi/criteria`, `PUT /config` |
| 4.2 | "Hiệu suất thô" `PUT /manual-inputs` · "Khối lượng hoàn thành / Dữ liệu tiến độ CV / điểm trừ" `POST /calculate` · **"Lịch sử KPI cũ" → `diem_ky_truoc` trong bảng điểm** |
| 4.3 | "Bảng điểm tạm tính/cá nhân", "Xác nhận kết quả" `confirm` · phê duyệt `approve|reject` → "Bản ghi KPI mới" |
| 5.1 | "Thông báo phạt", "Dữ liệu tham chiếu task lỗi", "Quy định xử phạt" `POST /violations` · "Danh sách chờ giải trình" `/notify`, `/me/violations/pending` |
| 5.2 | "Đơn giải trình, Bằng chứng" `/explanations` (nhiều đơn) · "Biên bản lỗi, Lệnh xử phạt" `/conclude` → thông báo |
| 5.3 | "Kết luận xử lý vi phạm" → `ma_ky_ap_dung` · "Bản ghi sự cố, lỗi mới" → D5 |
| 6.1 | **"Tham số lọc cá nhân"** `GET /dashboard/me?ma_da&tu_ngay&den_ngay` · **"Tham số lọc báo cáo tổng"** `GET /reports/portfolio?…` |
| 6.2–6.4 | `services/reports.py` · "Dashboard cá nhân" `/dashboard/me` · "Báo cáo Portfolio" → BGĐ `/reports/portfolio` |
| 6.5 | "Yêu cầu trích xuất dữ liệu" `GET /exports` – **chỉ Quản lý dự án** (quyền `report.export`) |

Quyền theo DFD (đã siết lại): EVM/Burn-down/giờ cả dự án/xuất file **chỉ QLDA**; Trưởng nhóm và BGĐ không có; BGĐ xem tổng quan + portfolio.

## 5. Quy tắc nghiệp vụ tôi tự quyết vì thiết kế không nêu – cần duyệt
1. **KPI**: điểm tiêu chí = min(giá trị/chỉ tiêu,1)×100; điểm gốc = bình quân gia quyền chỉ trên tiêu chí **có dữ liệu** (chuẩn hóa lại trọng số), không có dữ liệu ⇒ 0; điểm cuối = max(0, gốc − tổng điểm phạt đã xử). Nguồn: hoàn thành = DONE/được giao; đúng hạn = DONE trước/đúng hạn ÷ DONE; dùng giờ = giờ thực ÷ giờ dự kiến; phạm vi = task có hạn trong kỳ.
2. **EVM**: PV nội suy tuyến tính theo ngày; EV = chi phí gốc × %hoàn thành; AC = Σ giờ × đơn giá (mặc định 100.000đ/giờ). Sức khỏe: min(SPI,CPI) <0.8 RED, <0.95 AMBER.
3. **Luồng task**: TODO→IN_PROGRESS→IN_REVIEW→(duyệt)→DONE; từ chối bắt buộc nhận xét; không tự duyệt nếu là người được giao duy nhất.
4. **Vi phạm**: DRAFT→PENDING_EXPLANATION (hạn 3 ngày)→EXPLAINED→CONFIRMED/DISMISSED; quá hạn vẫn kết luận được.
5. **Ai duyệt KPI/kết luận vi phạm**: PM dự án **hoặc quản lý trực tiếp (`nhan_vien.ma_quan_ly`)** hoặc ADMIN, và phải là loại `QUAN_LY`; không tự duyệt chính mình.
6. Ghi giờ: chỉ task được giao cho mình, không trùng, không tương lai, ≤24h/bản ghi, sửa/xóa trong 7 ngày.
7. Dự án COMPLETED/CLOSED chỉ đọc (vi phạm & KPI vẫn xử lý được); người ngoài dự án nhận 404.
8. Cột/bảng mở rộng có chủ đích: xem `EXTRA` và `EXTENSION_TABLES` trong `tests/test_design_conformance.py` (`thong_bao`, `chi_so_du_an`, `version`, `token_version`, `don_gia_gio`, `uu_tien`, …).
9. **"Lệnh tác nghiệp, thông báo lỗi" (2.1 → Thành viên)**: hiểu là thông báo cho thành viên khi được giao việc (`TASK_ASSIGNED`); "thông báo lỗi" chưa có nghiệp vụ riêng.

## 6. Phân bổ 600 test
| File | # | Phủ |
|---|---|---|
| `test_design_conformance.py` | 55 | 26 bảng ERD (khóa, FK, [rỗng], cột lạ) + tập bảng mở rộng + 28 process DFD |
| `test_auth.py` | 41 | đăng nhập, khóa tạm, refresh, đổi mật khẩu, thu hồi token |
| `test_users.py` | 40 | quản trị người dùng, vai trò, ISA |
| `test_projects.py` | 75 | DFD 1.1–1.3, 1.5, 1.6 |
| `test_members_milestones.py` | 41 | DFD 1.4, 1.5 |
| `test_tasks.py` | 78 | DFD 2.1, 2.2, 2.4, 2.5 |
| `test_assign_review.py` | 41 | DFD 2.3, 2.6 |
| `test_timesheets.py` | 31 | DFD 2.7 |
| `test_progress.py` | 49 | DFD 3.1–3.3 |
| `test_violations.py` | 54 | DFD 5.1–5.3 |
| `test_kpi.py` | 68 | DFD 4.1–4.3 |
| `test_reports.py` | 27 | DFD 6.x |

Số liệu từng file chỉ để tham khảo; tổng đúng 600 (`pytest --collect-only`).
