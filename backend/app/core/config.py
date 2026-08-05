from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    DATABASE_URL: str
    ECHO_SQL: bool = False
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    FIRST_ADMIN_EMAIL: str | None = None
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    DEBUG: bool = False
    BRD_STORAGE_DIR: str = str(BACKEND_DIR / "storage" / "brds")
    MAX_UPLOAD_SIZE_MB: int = 20

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def brd_storage_path(self) -> Path:
        if not self.BRD_STORAGE_DIR.strip():
            return BACKEND_DIR / "storage" / "brds"
        return Path(self.BRD_STORAGE_DIR)

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


settings = Settings()
