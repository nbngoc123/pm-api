# Tài liệu API cho Frontend

> File này sinh từ `docs/API_FRONTEND.tpl.md` bằng `python -m tools.gen_docs` (catalog, mã lỗi, ma trận quyền tự cập nhật theo code).

Swagger UI: `GET /docs` · Schema: `docs/openapi.json` (sinh client TS: `npx openapi-typescript docs/openapi.json -o api.d.ts`).
Base URL: `/api/v1`. Tổng **{{N_OPS}} thao tác**, danh mục ở mục 11.

## 1. Quy ước chung
- **Tên field JSON = tên cột ERD, tiếng Việt snake_case** (`ma_du_an`, `ten_cv`, `han_hoan_thanh`…). URL tiếng Anh.
- **Ngày** (`date`): `YYYY-MM-DD`, là *ngày nghiệp vụ theo giờ VN (UTC+7)*.
- **Thời điểm** (`datetime`): server **lưu và trả UTC, không có hậu tố `Z`** (vd `2026-11-15T03:00:00`). Frontend phải coi là UTC khi hiển thị (`new Date(s + "Z")`).
  Khi **gửi** có thể kèm offset (`+07:00`/`Z`) — server tự quy về UTC.
- **Số tiền/giờ**: trả về dạng number, không phải chuỗi.
- **Phân trang**: `?page=1&size=20` (size ≤100, một vài endpoint ≤200) → `{ "items": [], "total": 0, "page": 1, "size": 20 }`.
- **Khóa lạc quan**: `du_an` và `task` có `version`. Gửi kèm `version` khi `PATCH`/`PUT`; sai → `409 VERSION_CONFLICT` ⇒ báo "dữ liệu đã bị người khác sửa", tải lại.
- **CORS**: server cấu hình `CORS_ORIGINS`.

## 2. Xác thực
1. `POST /auth/login {email,password}` → `{access_token, refresh_token, user}`.
2. Gửi `Authorization: Bearer <access_token>` (hết hạn sau 30′).
3. Gặp `401 TOKEN_INVALID` → gọi `POST /auth/refresh {refresh_token}` **một lần**, thử lại request; refresh thất bại → về trang đăng nhập.
4. `401 TOKEN_REVOKED`: đổi mật khẩu / bị khóa → bắt đăng nhập lại.
5. `403 ACCOUNT_LOCKED` (sai 5 lần, khóa 15′), `403 ACCOUNT_DISABLED`.
6. `GET /auth/me` → thông tin + `permissions` **cấp hệ thống**. Quyền **trong từng dự án**: `GET /projects/{id}/my-permissions` → `{vai_tro, permissions}`.
   **Dùng 2 endpoint này để ẩn/hiện nút**; server vẫn kiểm tra lại mọi thao tác.
- Email không phân biệt hoa/thường. Mật khẩu ≥8 ký tự, có chữ và số.
- Tải tệp (`/attachments/{id}/download`, `/exports`) cần header Authorization ⇒ dùng `fetch` → `blob()` rồi tạo link, không dùng `<a href>` trần.

## 3. Lỗi
Mọi lỗi: `{"error": {"code": "...", "message": "tiếng Việt", "details": null | [{"field","message"}]}}`.
Hiển thị `message`; **rẽ nhánh logic theo `code`**. `422 VALIDATION_ERROR` có `details[]` theo field để tô đỏ form.

- 401 chưa đăng nhập/token sai · 403 không đủ quyền · **404 cũng được trả khi bạn không thuộc dự án** (không lộ sự tồn tại).
- 409 xung đột trạng thái (sai luồng, trùng, version) · 422 dữ liệu sai/ràng buộc nghiệp vụ.

{{ERRORS}}

## 4. Enum (giá trị chuỗi chính xác)
| Nhóm | Giá trị |
|---|---|
| `du_an.trang_thai` | `PLANNING` → `ACTIVE` ⇄ `ON_HOLD`; `ACTIVE` → `COMPLETED`; đóng bằng `POST /close` → `CLOSED` |
| `task.trang_thai` | `TODO`, `IN_PROGRESS`, `IN_REVIEW`, `DONE`, `CANCELLED` |
| `task.uu_tien` | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `muc_do_khan` (server tính) | `OVERDUE`, `URGENT` (≤2 ngày), `SOON` (≤7), `NORMAL`, `NO_DEADLINE`, `null` nếu đã xong |
| `moc.trang_thai` | `PENDING`, `ACHIEVED`, `MISSED` |
| `phan_cong.trang_thai_phan_cong` | `ASSIGNED`, `COMPLETED`, `CANCELLED` |
| `vi_pham.trang_thai` | `DRAFT` → `PENDING_EXPLANATION` → `EXPLAINED` → `CONFIRMED` \| `DISMISSED` |
| `ky_kpi.trang_thai` | `DRAFT` → `OPEN` → `CLOSED` |
| `danh_gia_kpi.trang_thai` | `DRAFT` → `PROVISIONAL` → `MEMBER_CONFIRMED` → `APPROVED` (hoặc `REJECTED` → tính lại → `PROVISIONAL`) |
| `tieu_chi.nguon_du_lieu` | `TASK_COMPLETION`, `ON_TIME_RATE`, `HOURS_UTILIZATION`, `MANUAL` |
| Vai trò dự án | `PM` (tự gán cho quản lý dự án), `TEAM_LEAD`, `MEMBER` |
| Vai trò hệ thống | `ADMIN`, `DIRECTOR`, `MANAGER`, `EMPLOYEE` |

## 5. Luồng nghiệp vụ → hành động trên UI
**Công việc** (Kanban/danh sách): chỉ hiện nút theo trạng thái & quyền.
- `TODO` → "Bắt đầu" (người được giao; chưa có người được giao thì `409 TASK_NOT_ASSIGNED`): `POST /tasks/{id}/transition {trang_thai:"IN_PROGRESS"}`.
- `IN_PROGRESS` → cập nhật % (`POST /tasks/{id}/progress`), ghi giờ, "Gửi duyệt" (`transition IN_REVIEW`).
- `IN_REVIEW` → TL/PM "Duyệt/Từ chối": `POST /tasks/{id}/review {ket_qua, nhan_xet}` (từ chối **bắt buộc** `nhan_xet`). **Không thể chuyển DONE bằng `transition`** (422).
- `DONE` → TL/PM "Mở lại" (`transition IN_PROGRESS`). `CANCELLED` → TL/PM "Khôi phục" (`TODO`).
- Chỉ **nhân viên** (loại `NHAN_VIEN`) mới nhận việc / ghi giờ / bị lập vi phạm; người loại `QUAN_LY` (vd PM) thì không (`422 ASSIGNEE_MUST_BE_EMPLOYEE`, `VIOLATOR_MUST_BE_EMPLOYEE`).
- Phân công: `POST /tasks/{id}/assignments` trả `{phan_cong, warnings[]}` — **hiển thị `warnings`** (`OVER_HOURS_BUDGET`, `DEADLINE_PASSED`) dạng cảnh báo vàng, không chặn.
- "Việc cần ưu tiên": `GET /projects/{id}/tasks/prioritized`. "Chờ duyệt": `GET /projects/{id}/reviews/pending`.

**Chấm công**: `POST /tasks/{id}/timesheets {bat_dau, ket_thuc, noi_dung}` → trả `tong_gio_tich_luy_task/du_an`. Lỗi hay gặp: `TIMESHEET_OVERLAP`, `FUTURE_TIME`, `NOT_ASSIGNEE`. Sửa/xóa chỉ trong 7 ngày (`TIMESHEET_LOCKED`).

**Vi phạm**: TL/PM tạo (`DRAFT`) → "Gửi yêu cầu giải trình" (`/notify`, có `han_giai_trinh`) → nhân viên thấy ở `GET /me/violations/pending`, nộp `/explanations` (**được nộp nhiều đơn bổ sung** trước khi kết luận; `giai_trinh` là mảng) → PM/quản lý trực tiếp `/conclude {ket_luan:"CONFIRMED"|"DISMISSED", ghi_chu}`.

**KPI** (thứ tự thao tác của PM): tạo kỳ → `PUT /config` (tổng trọng số = 100, `422 WEIGHT_SUM_INVALID`) → `POST /open` → nhập `manual-inputs` cho tiêu chí `MANUAL` → `POST /calculate` (bảng điểm tạm tính) → nhân viên `confirm` → quản lý `approve|reject` (đường dẫn dạng `/kpi/periods/{ma_ky}/evaluations/{ma_nd}/...` vì ERD dùng khóa ghép (Mã kỳ, Mã người dùng); bảng điểm có `diem_ky_truoc` lấy từ lịch sử KPI) → khi mọi đánh giá `APPROVED` mới `close` được (`409 PENDING_EVALUATIONS`).
Nhân viên xem điểm: `GET /me/kpi`; chi tiết từng tiêu chí trong `chi_tiet[]` (`ty_le_dat` đã chặn ở 100). Điểm trừ vi phạm chỉ cập nhật ở lần `calculate` kế tiếp.

**Dashboard** `GET /dashboard/me` · **Ban giám đốc** `GET /reports/portfolio` (`suc_khoe`: `GREEN|AMBER|RED|GREY`) · **Báo cáo dự án** `GET /reports/projects/{id}` · **Biểu đồ** `/progress/burndown` (`diem[]`: `ly_tuong`, `thuc_te`; `thuc_te=null` cho ngày tương lai) và `/progress/evm`.
**Xuất file** (chỉ Quản lý dự án – DFD 6.5): `GET /exports?ma_da=&dataset=tasks|timesheets|violations|kpi&format=csv|xlsx`.
**Tham số lọc** (DFD 6.1): `GET /dashboard/me?ma_da=&tu_ngay=&den_ngay=` (cá nhân); `GET /reports/portfolio?trang_thai=&ma_quan_ly=&tu_ngay=&den_ngay=&suc_khoe=` (Ban giám đốc); `GET /progress/evm?co_so=chi_phi|gio&as_of=` (tham số tính tiến độ của QLDA).
**Thông báo** (polling 30–60s là đủ): `GET /me/notifications?chua_doc=true`, `POST /notifications/{id}/read`.
**Tìm người thêm vào dự án**: `GET /users/lookup?q=` (≥2 ký tự, mọi user đăng nhập đều gọi được).

## 6. Màn hình gợi ý ↔ endpoint
| Màn | Endpoint |
|---|---|
| Đăng nhập / hồ sơ | `/auth/login`, `/auth/me`, `/auth/change-password` |
| Danh sách dự án | `GET /projects?q=&trang_thai=` |
| Tổng quan dự án | `GET /projects/{id}/overview`, `/my-permissions`, `/milestones`, `/members` |
| Bảng công việc | `GET /projects/{id}/tasks?trang_thai=&ma_nd=&uu_tien=&q=&tre_han=` |
| Chi tiết task | `GET /tasks/{id}`, `/assignments`, `/subtasks`, `/attachments`, `/reviews`, `/timesheets` |
| Giờ làm của tôi | `GET /me/timesheets`, `/me/timesheets/summary` |
| Tiến độ (PM) | `/progress/evm`, `/progress/burndown`, `/baseline`, `POST /baseline/lock` |
| Vi phạm | `GET /violations?ma_da=`, `/me/violations/pending` |
| KPI | `GET /projects/{id}/kpi/periods`, `/kpi/periods/{id}/evaluations`, `/me/kpi`, `/kpi/users/{id}/history` |
| Quản trị | `/users`, `/roles`, `/violation-rules`, `/kpi/criteria`, `/audit-logs` |

## 7. Ma trận quyền (lấy từ seed)
{{MATRIX}}

Trưởng nhóm **không** có quyền xem EVM/báo cáo/xuất file; Ban giám đốc chỉ xem tổng quan dự án + portfolio (đúng luồng DFD).

Quyền hiệu lực trong dự án = quyền vai trò hệ thống ∪ quyền vai trò dự án. Ngoại lệ theo **quan hệ**: quản lý trực tiếp của nhân viên (`nhan_vien.ma_quan_ly`) cũng được duyệt KPI / kết luận vi phạm của nhân viên đó dù không thuộc dự án; không ai tự duyệt chính mình.

## 8. Mẹo triển khai
- Ẩn nút theo `permissions`, nhưng **luôn xử lý 403/409/422** (trạng thái có thể đã đổi).
- Sau thao tác đổi trạng thái task, dùng object trả về (`TaskOut` đầy đủ, có `version` mới) để cập nhật thẻ.
- `assignees` trong `TaskOut` là mảng `ma_nd`; tra tên từ `/projects/{id}/members` (cache theo dự án).
- Upload: `multipart/form-data`, field `file`; chấp nhận `pdf,png,jpg,jpeg,docx,xlsx,pptx,txt,csv,zip`, ≤10MB (`422 FILE_TYPE_NOT_ALLOWED`, `413 FILE_TOO_LARGE`).

## 9. Chưa có (hỏi backend nếu cần)
Realtime (WebSocket), SSO, tìm kiếm toàn cục, bình luận task, bộ lọc lưu sẵn, quên mật khẩu qua email.

## 10. Môi trường dev
`uvicorn app.main:app --reload` (SQLite) · tài khoản `admin@company.local` / `Admin@12345` · tạo user mẫu qua `POST /users`.

## 11. Danh mục endpoint (tự sinh từ OpenAPI)
{{CATALOG}}
