from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "PM-KPI System"
    database_url: str = "sqlite:///./dev.db"
    jwt_secret: str = "change-me-in-production-please-32+chars"
    jwt_alg: str = "HS256"
    access_ttl_min: int = 30
    refresh_ttl_days: int = 7
    password_iterations: int = 390_000
    max_failed_logins: int = 5
    lock_minutes: int = 15
    upload_dir: str = "./uploads"
    max_upload_mb: int = 10
    allowed_upload_ext: str = "pdf,png,jpg,jpeg,docx,xlsx,pptx,txt,csv,zip"
    alert_deadline_days: int = 2          # nhắc deadline trước N ngày
    timesheet_edit_days: int = 7          # chỉ sửa/xóa giờ làm trong N ngày
    explanation_days: int = 3             # hạn giải trình vi phạm
    default_hourly_rate: float = 100_000  # VND/giờ khi chưa cấu hình
    tz_offset_hours: int = 7              # múi giờ nghiệp vụ (VN = UTC+7) cho "hôm nay"
    cors_origins: str = "*"
    bootstrap_admin_email: str = "admin@company.local"
    bootstrap_admin_password: str = "Admin@12345"


settings = Settings()
