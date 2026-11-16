from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.errors import install_handlers
from app.routers import auth, kpi, progress, projects, reports, tasks, users, violations
from app.seed import seed

API = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev/test: tự tạo bảng. Production: dùng `alembic upgrade head` (bỏ create_all).
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db); db.commit()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan,
                  description="Backend Quản lý dự án & KPI. Lỗi trả về dạng {error:{code,message,details}}.")
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","), allow_methods=["*"], allow_headers=["*"])
    install_handlers(app)
    for r in (auth, users, projects, tasks, progress, violations, kpi, reports):
        app.include_router(r.router, prefix=API)

    @app.get("/health", tags=["Ops"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()
