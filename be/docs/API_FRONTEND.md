# Tài liệu API cho Frontend

> File này sinh từ `docs/API_FRONTEND.tpl.md` bằng `python -m tools.gen_docs` (catalog, mã lỗi, ma trận quyền tự cập nhật theo code).

Swagger UI: `GET /docs` · Schema: `docs/openapi.json` (sinh client TS: `npx openapi-typescript docs/openapi.json -o api.d.ts`).
Base URL: `/api/v1`. Tổng **109 thao tác**, danh mục ở mục 11.

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

| HTTP | `error.code` |
|---|---|
| 401 | `BAD_CREDENTIALS`, `TOKEN_INVALID`, `TOKEN_REVOKED` |
| 403 | `ACCOUNT_DISABLED`, `ACCOUNT_LOCKED`, `MANAGER_ONLY`, `NOT_ASSIGNEE`, `NOT_OWNER`, `NOT_VIOLATOR`, `SELF_APPROVAL`, `SELF_CONCLUDE`, `SELF_REVIEW`, `TRANSITION_REQUIRES_LEAD` |
| 404 | `EPIC_NOT_FOUND`, `EVALUATION_NOT_FOUND`, `MILESTONE_NOT_FOUND`, `NOTIFICATION_NOT_FOUND`, `PROJECT_NOT_FOUND`, `SUBTASK_NOT_FOUND`, `TASK_NOT_FOUND`, `USER_NOT_FOUND`, `VIOLATION_NOT_FOUND` |
| 409 | `ALREADY_ASSIGNED`, `ALREADY_CLOSED`, `ALREADY_MEMBER`, `BASELINE_LOCKED`, `CANNOT_CHANGE_MANAGER_ROLE`, `CANNOT_DISABLE_SELF`, `CANNOT_REMOVE_MANAGER`, `CRITERION_IN_USE`, `DUPLICATE_MILESTONE`, `DUPLICATE_PROJECT_NAME`, `DUPLICATE_VIOLATION`, `EMAIL_EXISTS`, `EPIC_HAS_TASKS`, `EVALUATION_LOCKED`, `EXPLANATION_DEADLINE_PASSED`, `INVALID_EVALUATION_STATE`, `INVALID_STATUS_TRANSITION`, `INVALID_VIOLATION_STATE`, `MEMBER_HAS_OPEN_TASKS`, `MILESTONE_HAS_OPEN_TASKS`, `MILESTONE_HAS_TASKS`, `NO_CONFIG`, `OPEN_TASKS_REMAIN`, `PASSWORD_UNCHANGED`, `PENDING_EVALUATIONS`, `PERIOD_CLOSED`, `PERIOD_NOT_EDITABLE`, `PERIOD_NOT_OPEN`, `PERIOD_OVERLAP`, `PROJECT_CLOSED`, `RULE_IN_USE`, `TASK_LOCKED`, `TASK_NOT_ASSIGNABLE`, `TASK_NOT_ASSIGNED`, `TASK_NOT_DELETABLE`, `TASK_NOT_IN_PROGRESS`, `TASK_NOT_IN_REVIEW`, `TIMESHEET_LOCKED`, `TIMESHEET_OVERLAP`, `VERSION_CONFLICT` |
| 413 | `FILE_TOO_LARGE` |
| 422 | `ASSIGNEE_MUST_BE_EMPLOYEE`, `COMMENT_REQUIRED`, `CRITERION_NOT_FOUND`, `CRITERION_NOT_IN_PERIOD`, `CRITERION_NOT_MANUAL`, `DUPLICATE_CRITERION`, `DURATION_TOO_LONG`, `EMPTY_FILE`, `FILE_TYPE_NOT_ALLOWED`, `FUTURE_TIME`, `INVALID_DATE_RANGE`, `INVALID_EPIC`, `INVALID_MANAGER`, `INVALID_MILESTONE`, `INVALID_PERIOD`, `INVALID_PROJECT_ROLE`, `INVALID_ROLE`, `INVALID_TIME_RANGE`, `MILESTONE_OUT_OF_RANGE`, `MISSING_PROJECT`, `NOT_ASSIGNED`, `NOT_PROJECT_MEMBER`, `RULE_NOT_ACTIVE`, `RULE_NOT_FOUND`, `SELF_VIOLATION`, `UNKNOWN_DATASET`, `USER_INACTIVE`, `USER_NOT_IN_PERIOD`, `USE_CLOSE_ENDPOINT`, `USE_REVIEW_ENDPOINT`, `VALIDATION_ERROR`, `VIOLATOR_MUST_BE_EMPLOYEE`, `WEIGHT_SUM_INVALID` |

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
| Quyền | ADMIN | DIRECTOR | MANAGER | EMPLOYEE | PM | TEAM_LEAD | MEMBER |
|---|---|---|---|---|---|---|---|
| `user.manage` — Quản lý người dùng | ✔ |  |  |  |  |  |  |
| `project.create` — Khởi tạo dự án | ✔ | ✔ |  |  |  |  |  |
| `project.read_all` — Xem mọi dự án | ✔ | ✔ |  |  |  |  |  |
| `project.close` — Đóng dự án | ✔ | ✔ |  |  |  |  |  |
| `report.portfolio` — Báo cáo portfolio đa dự án | ✔ | ✔ |  |  |  |  |  |
| `audit.read` — Xem nhật ký hệ thống | ✔ | ✔ |  |  |  |  |  |
| `alert.run` — Chạy quét cảnh báo | ✔ |  |  |  |  |  |  |
| `kpi.criteria.manage` — Quản lý tiêu chí KPI | ✔ |  | ✔ |  |  |  |  |
| `violation.rule.manage` — Quản lý quy định vi phạm | ✔ |  | ✔ |  |  |  |  |
| `project.read` — Xem dự án | ✔ |  |  |  | ✔ | ✔ | ✔ |
| `project.update` — Cập nhật dự án | ✔ |  |  |  | ✔ |  |  |
| `member.manage` — Quản lý thành viên | ✔ |  |  |  | ✔ |  |  |
| `milestone.manage` — Quản lý mốc | ✔ |  |  |  | ✔ |  |  |
| `task.create` — Tạo công việc | ✔ |  |  |  | ✔ | ✔ |  |
| `task.update` — Sửa công việc | ✔ |  |  |  | ✔ | ✔ |  |
| `task.assign` — Phân công | ✔ |  |  |  | ✔ | ✔ |  |
| `task.review` — Xét duyệt công việc | ✔ |  |  |  | ✔ | ✔ |  |
| `task.transition` — Cập nhật trạng thái công việc | ✔ |  |  |  | ✔ | ✔ | ✔ |
| `timesheet.log` — Ghi giờ làm | ✔ |  |  |  | ✔ | ✔ | ✔ |
| `kpi.period.manage` — Quản lý kỳ KPI | ✔ |  |  |  | ✔ |  |  |
| `kpi.approve` — Phê duyệt KPI | ✔ |  |  |  | ✔ |  |  |
| `violation.create` — Lập vi phạm | ✔ |  |  |  | ✔ | ✔ |  |
| `violation.conclude` — Kết luận vi phạm | ✔ |  |  |  | ✔ |  |  |
| `report.project` — Báo cáo dự án | ✔ |  |  |  | ✔ |  |  |
| `progress.manage` — Quản lý baseline/tiến độ | ✔ |  |  |  | ✔ |  |  |
| `report.export` — Xuất báo cáo (DFD 6.5: chỉ Quản lý dự án) | ✔ |  |  |  | ✔ |  |  |

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
#### 1. Quản lý dự án

| Method | Path | Mô tả |
|---|---|---|
| `POST` | `/projects` | 1.1 Tạo dự án (Lệnh khởi tạo DA) |
| `GET` | `/projects` | Danh sách dự án của tôi (hoặc tất cả nếu có project.read_all) |
| `GET` | `/projects/{ma_da}` |  |
| `PATCH` | `/projects/{ma_da}` | 1.2 Cập nhật thông tin dự án |
| `PUT` | `/projects/{ma_da}/goals` | 1.3 Thiết lập mục tiêu & thời gian dự án |
| `PATCH` | `/projects/{ma_da}/status` | 1.5 Cập nhật trạng thái dự án |
| `POST` | `/projects/{ma_da}/close` | 1.6 Đóng dự án (Yêu cầu đóng DA từ Ban giám đốc) |
| `GET` | `/projects/{ma_da}/my-permissions` | Quyền của tôi trong dự án (để ẩn/hiện nút trên UI) |
| `GET` | `/projects/{ma_da}/overview` | 1.5 Báo cáo trạng thái tổng quan |
| `GET` | `/projects/{ma_da}/members` |  |
| `POST` | `/projects/{ma_da}/members` | 1.4 Thêm thành viên & phân quyền |
| `PATCH` | `/projects/{ma_da}/members/{ma_nd}` | 1.4 Đổi vai trò thành viên |
| `DELETE` | `/projects/{ma_da}/members/{ma_nd}` | 1.4 Xóa thành viên khỏi dự án |
| `GET` | `/projects/{ma_da}/milestones` |  |
| `POST` | `/projects/{ma_da}/milestones` | 1.5 Thiết lập mốc |
| `PATCH` | `/projects/{ma_da}/milestones/{ma_moc}` |  |
| `DELETE` | `/projects/{ma_da}/milestones/{ma_moc}` |  |

#### 2. Quản lý công việc

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/projects/{ma_da}/epics` |  |
| `POST` | `/projects/{ma_da}/epics` |  |
| `DELETE` | `/projects/{ma_da}/epics/{ma_epic}` |  |
| `POST` | `/projects/{ma_da}/tasks` | 2.1 Tạo công việc |
| `GET` | `/projects/{ma_da}/tasks` |  |
| `GET` | `/projects/{ma_da}/tasks/prioritized` | 2.4 Danh sách ưu tiên & thời hạn |
| `GET` | `/projects/{ma_da}/reviews/pending` | 2.6 Danh sách task cần duyệt |
| `GET` | `/tasks/{ma_cv}` |  |
| `PATCH` | `/tasks/{ma_cv}` | 2.2/2.4 Cập nhật công việc, ưu tiên, thời hạn |
| `DELETE` | `/tasks/{ma_cv}` |  |
| `POST` | `/tasks/{ma_cv}/transition` | 2.5 Theo dõi trạng thái công việc |
| `POST` | `/tasks/{ma_cv}/progress` | 2.5 Cập nhật % hoàn thành |
| `GET` | `/tasks/{ma_cv}/assignments` |  |
| `POST` | `/tasks/{ma_cv}/assignments` | 2.3 Phân công công việc |
| `DELETE` | `/tasks/{ma_cv}/assignments/{ma_nd}` |  |
| `POST` | `/tasks/{ma_cv}/review` | 2.6 Xét duyệt công việc |
| `GET` | `/tasks/{ma_cv}/reviews` |  |
| `GET` | `/tasks/{ma_cv}/subtasks` |  |
| `POST` | `/tasks/{ma_cv}/subtasks` |  |
| `PATCH` | `/tasks/{ma_cv}/subtasks/{ma_sub}` |  |
| `DELETE` | `/tasks/{ma_cv}/subtasks/{ma_sub}` |  |
| `POST` | `/tasks/{ma_cv}/attachments` | 2.5 Đính kèm tệp |
| `GET` | `/tasks/{ma_cv}/attachments` |  |
| `GET` | `/attachments/{ma_tep}/download` |  |
| `DELETE` | `/attachments/{ma_tep}` |  |
| `POST` | `/tasks/{ma_cv}/timesheets` | 2.7 Ghi nhận thời gian làm việc |
| `GET` | `/tasks/{ma_cv}/timesheets` |  |
| `GET` | `/me/timesheets` |  |
| `GET` | `/me/timesheets/summary` | Tổng giờ làm tích lũy |
| `GET` | `/projects/{ma_da}/timesheets` |  |
| `PATCH` | `/timesheets/{ma_nk}` |  |
| `DELETE` | `/timesheets/{ma_nk}` |  |

#### 3. Theo dõi tiến độ

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/projects/{ma_da}/progress/evm` | 3.1 Chỉ số EVM (PV/EV/AC/SPI/CPI/EAC) |
| `GET` | `/projects/{ma_da}/progress/burndown` | 3.1 Biểu đồ Burn-down |
| `PUT` | `/tasks/{ma_cv}/baseline` | Thiết lập kế hoạch gốc của task |
| `GET` | `/projects/{ma_da}/baseline` |  |
| `POST` | `/projects/{ma_da}/baseline/lock` | Khóa kế hoạch gốc (tự tạo baseline cho task chưa có) |
| `POST` | `/projects/{ma_da}/progress/snapshots` | 3.3 Lưu bản ghi chỉ số DA |
| `GET` | `/projects/{ma_da}/progress/snapshots` |  |
| `POST` | `/alerts/scan` | 3.2 Quét & sinh cảnh báo (cron gọi hằng ngày) |
| `GET` | `/me/notifications` |  |
| `POST` | `/notifications/{ma_tb}/read` |  |
| `POST` | `/me/notifications/read-all` |  |
| `GET` | `/audit-logs` | 3.3 Nhật ký truy vết thay đổi |

#### 4. Quản lý KPI

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/kpi/criteria` |  |
| `POST` | `/kpi/criteria` | 4.1 Tạo tiêu chí KPI |
| `PATCH` | `/kpi/criteria/{ma_tc}` |  |
| `DELETE` | `/kpi/criteria/{ma_tc}` |  |
| `GET` | `/projects/{ma_da}/kpi/periods` |  |
| `POST` | `/projects/{ma_da}/kpi/periods` | 4.1 Tạo kỳ KPI |
| `GET` | `/kpi/periods/{ma_ky}` |  |
| `PUT` | `/kpi/periods/{ma_ky}/config` | 4.1 Cấu hình & phân bổ KPI (tiêu chí, trọng số, chỉ tiêu) |
| `GET` | `/kpi/periods/{ma_ky}/config` |  |
| `POST` | `/kpi/periods/{ma_ky}/open` | Mở kỳ: tạo bảng đánh giá cho thành viên |
| `POST` | `/kpi/periods/{ma_ky}/sync-members` | Bổ sung đánh giá cho thành viên mới |
| `PUT` | `/kpi/periods/{ma_ky}/manual-inputs` | 4.2 Nhập hiệu suất thô (tiêu chí MANUAL) – Quản lý |
| `POST` | `/kpi/periods/{ma_ky}/calculate` | 4.2 Thu thập & tính toán tự động → bảng điểm tạm tính |
| `POST` | `/kpi/periods/{ma_ky}/close` | Đóng kỳ KPI |
| `GET` | `/kpi/periods/{ma_ky}/evaluations` |  |
| `GET` | `/kpi/periods/{ma_ky}/evaluations/{ma_nd}` |  |
| `POST` | `/kpi/periods/{ma_ky}/evaluations/{ma_nd}/confirm` | 4.3 Thành viên xác nhận kết quả |
| `POST` | `/kpi/periods/{ma_ky}/evaluations/{ma_nd}/approve` | 4.3 Quản lý phê duyệt KPI |
| `POST` | `/kpi/periods/{ma_ky}/evaluations/{ma_nd}/reject` | 4.3 Quản lý từ chối (yêu cầu tính lại) |
| `GET` | `/me/kpi` | KPI của tôi (mọi kỳ) |
| `GET` | `/kpi/users/{ma_nd}/history` | Lịch sử KPI cũ của một người |

#### 5. Vi phạm & chất lượng

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/violation-rules` |  |
| `POST` | `/violation-rules` |  |
| `PATCH` | `/violation-rules/{ma_qd}` |  |
| `DELETE` | `/violation-rules/{ma_qd}` |  |
| `POST` | `/violations` | 5.1 Ghi nhận & phân loại vi phạm (hồ sơ dự thảo) |
| `GET` | `/violations` |  |
| `GET` | `/me/violations/pending` | 5.1 Danh sách chờ giải trình của tôi |
| `GET` | `/violations/{ma_vp}` |  |
| `POST` | `/violations/{ma_vp}/notify` | 5.1 Gửi thông báo & yêu cầu giải trình |
| `POST` | `/violations/{ma_vp}/explanations` | 5.2 Nộp đơn giải trình & bằng chứng |
| `POST` | `/violations/{ma_vp}/conclude` | 5.2 Kết luận xử lý vi phạm (Biên bản lỗi, Lệnh xử phạt) |

#### 6. Báo cáo & Dashboard

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/dashboard/me` | 6.3 Dashboard cá nhân |
| `GET` | `/reports/portfolio` | 6.4 Báo cáo portfolio đa dự án (Ban giám đốc) |
| `GET` | `/reports/projects/{ma_da}` | 6.2/6.4 Báo cáo tổng hợp một dự án |
| `GET` | `/exports` | 6.5 Xuất báo cáo (csv | xlsx) – chỉ Quản lý dự án (DFD: File báo cáo → Quản lý dự án) |

#### Auth

| Method | Path | Mô tả |
|---|---|---|
| `POST` | `/auth/login` |  |
| `POST` | `/auth/refresh` |  |
| `GET` | `/auth/me` |  |
| `POST` | `/auth/change-password` |  |

#### Ops

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/health` |  |

#### Users & Roles

| Method | Path | Mô tả |
|---|---|---|
| `POST` | `/users` |  |
| `GET` | `/users` |  |
| `GET` | `/users/lookup` |  |
| `GET` | `/users/{ma_nd}` |  |
| `PATCH` | `/users/{ma_nd}` |  |
| `POST` | `/users/{ma_nd}/reset-password` |  |
| `GET` | `/roles` |  |

