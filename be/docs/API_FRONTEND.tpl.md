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

## 6. Màn hình gợi ý ↔ Endpoint & Vai trò sử dụng

Dưới đây là ma trận chi tiết các màn hình gợi ý cho đội ngũ Frontend, phân theo nhóm chức năng, vai trò và các endpoint tương ứng:

### 6.1. Nhóm Chung & Xác thực
| Màn hình | Route FE gợi ý | Vai trò | Chức năng chính | Endpoint Backend liên quan |
|---|---|---|---|---|
| **Đăng nhập** | `/login` | Tất cả | Đăng nhập bằng Email/Mật khẩu | `POST /auth/login` |
| **Đổi mật khẩu** | `/change-password` | Tất cả | Đổi mật khẩu cá nhân | `POST /auth/change-password` |
| **Thông tin cá nhân** | `/profile` | Tất cả | Xem thông tin tài khoản, quyền hạn hệ thống | `GET /auth/me` |
| **Dashboard cá nhân** | `/dashboard` | Tất cả | Xem công việc ưu tiên, cảnh báo deadline, thống kê giờ làm trong tuần | `GET /dashboard/me`<br>`GET /me/notifications`<br>`POST /notifications/{id}/read`<br>`POST /me/notifications/read-all` |

### 6.2. Nhóm Dự án & Công việc
| Màn hình | Route FE gợi ý | Vai trò | Chức năng chính | Endpoint Backend liên quan |
|---|---|---|---|---|
| **Danh sách Dự án** | `/projects` | Tất cả | Lọc theo trạng thái, tìm kiếm, khởi tạo dự án mới | `GET /projects`<br>`POST /projects` |
| **Tổng quan Dự án** | `/projects/:id` | Tất cả | Xem thông tin chung, chỉ số, cập nhật trạng thái/mục tiêu, đóng dự án | `GET /projects/{id}`<br>`PATCH /projects/{id}`<br>`PUT /projects/{id}/goals`<br>`PATCH /projects/{id}/status`<br>`POST /projects/{id}/close`<br>`GET /projects/{id}/overview`<br>`GET /projects/{id}/my-permissions` |
| **Thành viên & Cột mốc** | `/projects/:id/settings` | PM, Director | Quản lý thành viên, phân quyền vai trò (PM/Lead/Member), quản lý mốc (milestones) & nhóm việc (epics) | `GET /projects/{id}/members`<br>`POST /projects/{id}/members`<br>`PATCH /projects/{id}/members/{uid}`<br>`DELETE /projects/{id}/members/{uid}`<br>`GET /users/lookup`<br>`GET /projects/{id}/milestones`<br>`POST /projects/{id}/milestones`<br>`PATCH /projects/{id}/milestones/{mid}`<br>`DELETE /projects/{id}/milestones/{mid}`<br>`GET /projects/{id}/epics`<br>`POST /projects/{id}/epics`<br>`DELETE /projects/{id}/epics/{eid}` |
| **Bảng công việc (Kanban / List)** | `/projects/:id/tasks` | PM, Lead, Member | Xem công việc theo cột trạng thái, việc cần ưu tiên, việc chờ duyệt, lọc theo người nhận/hạn | `GET /projects/{id}/tasks`<br>`POST /projects/{id}/tasks`<br>`GET /projects/{id}/tasks/prioritized`<br>`GET /projects/{id}/reviews/pending` |
| **Chi tiết Công việc (Modal / Page)** | `/tasks/:id` | PM, Lead, Member | Chuyển trạng thái (`transition`), cập nhật % tiến độ, phân công nhân viên, tạo subtask, đính kèm tệp, duyệt việc (`review`) | `GET /tasks/{id}`<br>`PATCH /tasks/{id}`<br>`DELETE /tasks/{id}`<br>`POST /tasks/{id}/transition`<br>`POST /tasks/{id}/progress`<br>`GET /tasks/{id}/assignments`<br>`POST /tasks/{id}/assignments`<br>`DELETE /tasks/{id}/assignments/{uid}`<br>`GET /tasks/{id}/subtasks`<br>`POST /tasks/{id}/subtasks`<br>`PATCH /tasks/{id}/subtasks/{sid}`<br>`DELETE /tasks/{id}/subtasks/{sid}`<br>`GET /tasks/{id}/attachments`<br>`POST /tasks/{id}/attachments`<br>`GET /attachments/{aid}/download`<br>`DELETE /attachments/{aid}`<br>`GET /tasks/{id}/reviews`<br>`POST /tasks/{id}/review` |
| **Theo dõi Tiến độ & EVM** | `/projects/:id/progress` | PM, Director | Biểu đồ Burndown, phân tích chỉ số EVM (PV/EV/AC/SPI/CPI), thiết lập & khóa đường cơ sở (Baseline) | `GET /projects/{id}/progress/evm`<br>`GET /projects/{id}/progress/burndown`<br>`GET /projects/{id}/baseline`<br>`PUT /tasks/{id}/baseline`<br>`POST /projects/{id}/baseline/lock`<br>`GET /projects/{id}/progress/snapshots`<br>`POST /projects/{id}/progress/snapshots` |

### 6.3. Nhóm Chấm công & Vi phạm
| Màn hình | Route FE gợi ý | Vai trò | Chức năng chính | Endpoint Backend liên quan |
|---|---|---|---|---|
| **Chấm công của tôi (Timesheet)** | `/timesheets` | Member | Xem lịch sử ghi giờ, tổng giờ tích lũy, thêm/sửa/xóa log giờ làm | `GET /me/timesheets`<br>`GET /me/timesheets/summary`<br>`POST /tasks/{id}/timesheets`<br>`PATCH /timesheets/{id}`<br>`DELETE /timesheets/{id}` |
| **Tổng hợp Chấm công dự án** | `/projects/:id/timesheets` | PM, Lead | Xem nhật ký giờ làm của các thành viên trong dự án | `GET /projects/{id}/timesheets` |
| **Vi phạm & Giải trình của tôi** | `/me/violations` | Member | Xem các biên bản vi phạm được thông báo, nộp đơn giải trình & đính kèm tài liệu | `GET /me/violations/pending`<br>`GET /violations/{id}`<br>`POST /violations/{id}/explanations` |
| **Quản lý Vi phạm dự án** | `/projects/:id/violations` | PM, Lead, Manager | Lập biên bản vi phạm (`DRAFT`), gửi thông báo giải trình (`/notify`), xem xét giải trình và ra quyết định kết luận (`/conclude`) | `GET /violations`<br>`POST /violations`<br>`GET /violations/{id}`<br>`POST /violations/{id}/notify`<br>`POST /violations/{id}/conclude` |

### 6.4. Nhóm Đánh giá KPI & Báo cáo
| Màn hình | Route FE gợi ý | Vai trò | Chức năng chính | Endpoint Backend liên quan |
|---|---|---|---|---|
| **KPI của tôi** | `/me/kpi` | Member | Xem bảng điểm đánh giá cá nhân qua các kỳ, xác nhận điểm KPI | `GET /me/kpi`<br>`GET /kpi/periods/{id}/evaluations/{uid}`<br>`POST /kpi/periods/{id}/evaluations/{uid}/confirm` |
| **Quản lý Kỳ KPI dự án** | `/projects/:id/kpi` | PM, Manager | Tạo kỳ đánh giá, phân bổ trọng số & chỉ tiêu, mở kỳ, nhập điểm tiêu chí MANUAL, chạy tính điểm tự động (`calculate`), phê duyệt/từ chối đánh giá, đóng kỳ | `GET /projects/{id}/kpi/periods`<br>`POST /projects/{id}/kpi/periods`<br>`GET /kpi/periods/{id}`<br>`GET /kpi/periods/{id}/config`<br>`PUT /kpi/periods/{id}/config`<br>`POST /kpi/periods/{id}/open`<br>`POST /kpi/periods/{id}/sync-members`<br>`PUT /kpi/periods/{id}/manual-inputs`<br>`POST /kpi/periods/{id}/calculate`<br>`GET /kpi/periods/{id}/evaluations`<br>`GET /kpi/periods/{id}/evaluations/{uid}`<br>`POST /kpi/periods/{id}/evaluations/{uid}/approve`<br>`POST /kpi/periods/{id}/evaluations/{uid}/reject`<br>`POST /kpi/periods/{id}/close`<br>`GET /kpi/users/{uid}/history` |
| **Báo cáo Dự án & Portfolio** | `/reports` | Director, PM | Báo cáo chi tiết một dự án, báo cáo tổng thể Portfolio (đánh giá sức khỏe GREEN/AMBER/RED/GREY), xuất file CSV/Excel | `GET /reports/projects/{id}`<br>`GET /reports/portfolio`<br>`GET /exports` |

### 6.5. Nhóm Quản trị Hệ thống (Admin Only)
| Màn hình | Route FE gợi ý | Vai trò | Chức năng chính | Endpoint Backend liên quan |
|---|---|---|---|---|
| **Quản lý Tài khoản (Users)** | `/admin/users` | Admin | Danh sách nhân sự, tạo người dùng mới, sửa thông tin, đặt đơn giá giờ, phân quản lý trực tiếp, khóa/mở khóa tài khoản, reset mật khẩu | `GET /users`<br>`POST /users`<br>`GET /users/{id}`<br>`PATCH /users/{id}`<br>`POST /users/{id}/reset-password`<br>`GET /roles` |
| **Quy định Vi phạm** | `/admin/violation-rules` | Admin, Manager | Thiết lập danh mục quy chế vi phạm của tổ chức, mức trừ điểm KPI mặc định, kích hoạt/hủy quy định | `GET /violation-rules`<br>`POST /violation-rules`<br>`PATCH /violation-rules/{id}`<br>`DELETE /violation-rules/{id}` |
| **Danh mục Tiêu chí KPI** | `/admin/kpi-criteria` | Admin, Manager | Định nghĩa bộ tiêu chí KPI chuẩn (nguồn tự động từ task/on-time/hours hoặc manual) | `GET /kpi/criteria`<br>`POST /kpi/criteria`<br>`PATCH /kpi/criteria/{id}`<br>`DELETE /kpi/criteria/{id}` |
| **Nhật ký Truy vết (Audit Logs)** | `/admin/audit-logs` | Admin, Director | Xem lịch sử các thao tác thay đổi dữ liệu, thời điểm và đối tượng tác động | `GET /audit-logs` |
| **Vận hành & Cảnh báo (Ops)** | `/admin/ops` | Admin | Kích hoạt quét cảnh báo deadline thủ công, kiểm tra tình trạng kết nối | `POST /alerts/scan`<br>`GET /health` |

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
