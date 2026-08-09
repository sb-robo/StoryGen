import os
from pathlib import Path

from pydantic import field_validator
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
    FRONTEND_BASE_URL: str = "http://localhost:5173"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    AUTH_DISABLED: bool = False
    DEV_USER_EMAIL: str | None = None
    BRD_STORAGE_DIR: str = str(BACKEND_DIR / "storage" / "brds")
    MAX_UPLOAD_SIZE_MB: int = 20
    HF_TOKEN: str | None = None
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-5.4"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_EMBEDDING_DIMENSIONS: int = 1536
    RAG_SIMILAR_STORY_LIMIT: int = 5
    RAG_SIMILAR_CHUNK_LIMIT: int = 8
    RAG_FEATURE_CHUNK_LIMIT: int = 12
    RAG_FEATURE_RETRIEVAL_THRESHOLD: int = 12
    RAG_CROSS_BRD_FEATURE_LIMIT: int = 5
    RAG_CROSS_BRD_STORY_LIMIT: int = 5
    RAG_CROSS_BRD_MAX_DISTANCE: float = 0.35
    LLM_MAX_RETRIES: int = 3
    LLM_TIMEOUT_SECONDS: int = 120
    LLM_MAX_ITERATIONS: int = 2
    LLM_ENABLE_TEMPERATURE_CONTROL: bool = False
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_AUTH_PER_MINUTE: int = 20
    RATE_LIMIT_UPLOAD_PER_MINUTE: int = 10
    RATE_LIMIT_AI_PER_MINUTE: int = 30

    @field_validator(
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "OPENAI_EMBEDDING_MODEL",
        "HF_TOKEN",
        mode="before",
    )
    @classmethod
    def strip_quoted_env_string(cls, value: str | None) -> str | None:
        if value is None or not isinstance(value, str):
            return value
        cleaned = value.strip()
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'"}:
            cleaned = cleaned[1:-1].strip()
        return cleaned or None

    @property
    def openai_api_key(self) -> str:
        return (self.OPENAI_API_KEY or "").strip()

    @property
    def openai_model(self) -> str:
        return (self.OPENAI_MODEL or "gpt-5.4").strip()

    @property
    def openai_embedding_model(self) -> str:
        return (self.OPENAI_EMBEDDING_MODEL or "text-embedding-3-small").strip()

    @property
    def openai_is_configured(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def auth_disabled(self) -> bool:
        """Auth bypass is only honored when DEBUG is also enabled."""
        return self.AUTH_DISABLED and self.DEBUG

    @property
    def smtp_is_configured(self) -> bool:
        return bool((self.SMTP_HOST or "").strip())

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


def apply_openai_settings() -> None:
    """
    Export OpenAI settings to os.environ for SDK defaults and third-party tools.

    pydantic-settings reads .env into Settings but does not populate os.environ.
    """
    api_key = settings.openai_api_key
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    model = settings.openai_model
    if model:
        os.environ["OPENAI_MODEL"] = model


apply_huggingface_token()
apply_openai_settings()
