# PM-KPI Backend

Backend + CSDL cho hệ thống **Quản lý dự án & KPI** (thiết kế DFD mức 0/1 + ERD của nhóm).
Python 3.12 · FastAPI · SQLAlchemy 2 · PostgreSQL 16 · Alembic · JWT. **109 thao tác API, 28 bảng, 600 test.**

## Chạy nhanh
```bash
# Dev (SQLite, không cần cài DB)
pip install -r requirements-dev.txt
uvicorn app.main:app --reload          # http://localhost:8000/docs   (admin@company.local / Admin@12345)

# Test (600 test, ~80s)
pytest

# Production-like (PostgreSQL + migrate + cron cảnh báo)
cp .env.example .env   # sửa JWT_SECRET, mật khẩu admin
docker compose up --build
```

## Cấu trúc
```
app/
  main.py  config.py  database.py  security.py  deps.py  errors.py  enums.py  seed.py  cli.py
  models/     identity.py (người dùng, vai trò, quyền) · work.py (dự án, task, giờ làm…) · quality.py (vi phạm, KPI, log)
  schemas/    Pydantic request/response theo từng module
  services/   NGHIỆP VỤ nằm ở đây (access, projects, tasks, progress, violations, kpi, reports, users, common)
  routers/    HTTP mỏng: auth, users, projects, tasks, progress, violations, kpi, reports
alembic/      migration (0001 = toàn bộ schema)       db/schema.sql  DDL PostgreSQL để DBA review
tests/        600 test (xem docs/TRACEABILITY.md)      docs/          tài liệu (xem bên dưới)
```
Quy ước: router chỉ xác thực + kiểm quyền + gọi service; mọi quy tắc nghiệp vụ nằm trong `services/`.
Tên bảng/cột/field JSON dùng **tiếng Việt snake_case đúng như ERD** để đối chiếu thiết kế trực tiếp; URL dùng tiếng Anh.

## Tài liệu
| File | Dành cho |
|---|---|
| `docs/API_FRONTEND.md` | **Frontend**: quy ước, auth, lỗi, enum, ma trận quyền→UI, luồng màn hình, danh mục endpoint |
| `docs/openapi.json` | Import Postman/Insomnia, sinh client TypeScript (`openapi-typescript`) |
| `docs/ARCHITECTURE.md` | Lý do chọn công nghệ, sizing 250 nhân viên, vận hành |
| `docs/TRACEABILITY.md` | Đối chiếu DFD/ERD ↔ code ↔ test, **các điểm khác/bổ sung so với thiết kế**, câu hỏi cần team chốt |

## Biến môi trường chính
`DATABASE_URL`, `JWT_SECRET` (bắt buộc đổi), `CORS_ORIGINS`, `UPLOAD_DIR`, `TZ_OFFSET_HOURS` (mặc định 7), `ALERT_DEADLINE_DAYS`, `EXPLANATION_DAYS`, `TIMESHEET_EDIT_DAYS`. Xem `app/config.py`.
