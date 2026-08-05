import os
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
    AUTH_DISABLED: bool = False
    DEV_USER_EMAIL: str | None = None
    BRD_STORAGE_DIR: str = str(BACKEND_DIR / "storage" / "brds")
    MAX_UPLOAD_SIZE_MB: int = 20
    HF_TOKEN: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def auth_disabled(self) -> bool:
        """Auth bypass is only honored when DEBUG is also enabled."""
        return self.AUTH_DISABLED and self.DEBUG

    @property
    def brd_storage_path(self) -> Path:
        if not self.BRD_STORAGE_DIR.strip():
            return BACKEND_DIR / "storage" / "brds"
        return Path(self.BRD_STORAGE_DIR)

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


settings = Settings()


def apply_huggingface_token() -> None:
    """
    Export HF_TOKEN so huggingface_hub / transformers / Docling authenticate.

    pydantic-settings reads .env into Settings but does not put values in os.environ,
    which those libraries require.
    """
    token = (settings.HF_TOKEN or "").strip()
    if not token:
        return
    os.environ["HF_TOKEN"] = token
    os.environ["HUGGING_FACE_HUB_TOKEN"] = token


apply_huggingface_token()
