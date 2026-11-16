# Kiến trúc & lựa chọn công nghệ

## Quy mô và hệ quả
~250 nhân viên ⇒ vài chục người dùng đồng thời, vài chục request/giây ở đỉnh, dữ liệu vài triệu dòng sau nhiều năm
(chủ yếu `nhat_ky_gio_lam`, `nhat_ky_he_thong`, `thong_bao`). Đây là quy mô **một máy chủ + một PostgreSQL** xử lý thoải mái.
Vì vậy chọn **modular monolith**, không microservices/message queue/cache phân tán — chúng thêm chi phí vận hành mà không có lợi ích ở quy mô này.

| Quyết định | Lý do | Khi nào xem lại |
|---|---|---|
| **FastAPI + Pydantic v2** | Validate đầu vào chặt, tự sinh OpenAPI cho frontend, hiệu năng tốt | — |
| **SQLAlchemy 2 + Alembic** | ORM trưởng thành, migration có version, test được trên SQLite | — |
| **PostgreSQL 16** | Giao dịch ACID cho nghiệp vụ tiền/giờ/KPI, `NUMERIC` chính xác, index tốt | — |
| **JWT access 30′ + refresh 7 ngày**, `token_version` | Stateless; đổi mật khẩu/khóa tài khoản thu hồi mọi token tức thì | Cần SSO → thêm OIDC (Azure AD/Google) |
| **RBAC 2 tầng** (vai trò hệ thống ∪ vai trò dự án) | Đúng ERD: `nguoi_dung.ma_vai_tro_he_thong` + `thanh_vien_du_an.ma_vai_tro` + `vai_tro_quyen` | — |
| **Optimistic locking** (`version`) trên dự án & task | Hai người sửa cùng lúc → 409 thay vì ghi đè âm thầm | — |
| **Tệp lưu đĩa** (`UPLOAD_DIR`, volume) | Đủ cho 1 node | Nhiều node → S3/MinIO (chỉ sửa `save_attachment`) |
| **Cron nội bộ** (`app.cli scan-alerts`) | Cảnh báo idempotent (dedupe_key) nên chạy lặp an toàn | Cần realtime → thêm WebSocket/SSE |

## Sizing tham chiếu (suy luận, **chưa load-test**)
- API: `gunicorn -w 4` (Dockerfile) trên 2 vCPU/4 GB. Pool DB 10+20.
- PostgreSQL: 2 vCPU/4 GB, SSD. Bật backup hằng ngày + WAL archiving.
- Điểm nóng cần theo dõi: `GET /reports/portfolio` (N dự án × vài truy vấn; nếu >200 dự án hãy cache 60s hoặc đọc từ `chi_so_du_an`),
  `POST /kpi/periods/{id}/calculate` (O(thành viên × tiêu chí) truy vấn; chạy vài giây với 250 người, nên chạy ngoài giờ cao điểm).
- Index đã có: `task(ma_du_an, trang_thai)`, `nhat_ky_gio_lam(ma_nd, bat_dau)`, FK chính, `nhat_ky_he_thong(thoi_diem, loai_su_kien)`.
- Khi `nhat_ky_he_thong` > ~10 triệu dòng: partition theo tháng hoặc archive.

## Lớp & luồng một request
`router` (HTTP, DI) → `deps.current_user` (JWT) → `services.access.require_project_perm` (RBAC; non-member nhận **404** để không lộ sự tồn tại dự án)
→ `services.*` (quy tắc nghiệp vụ, ghi `audit`/`notify`) → commit 1 transaction/request (`get_db`).

## Bảo mật đã làm
Mật khẩu PBKDF2-SHA256 (390k vòng) · khóa tạm 15′ sau 5 lần sai · token revoke theo `token_version` · validate loại tệp/kích thước/tên tệp (chống path traversal) ·
chống CSV/Excel formula injection khi xuất · phân quyền kiểm ở service (không chỉ ở UI) · không lộ tồn tại tài nguyên cho người ngoài dự án.
**Chưa làm (cần bổ sung trước production):** rate-limit ở nginx/WAF, HTTPS (đặt sau reverse proxy), quét virus tệp upload, 2FA, đưa `JWT_SECRET` vào secret manager.
