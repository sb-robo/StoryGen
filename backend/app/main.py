import logging
from logging import getLogger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import apply_huggingface_token, apply_openai_settings, settings

# Configure the root logger before importing routers/services so that every
# `logging.getLogger(__name__)` call in the app (node execution, LLM calls,
# background tasks, RAG retrieval, etc.) actually produces output.
# Uvicorn only configures its own "uvicorn"/"uvicorn.access" loggers by
# default; without this, app-level logger.info()/logger.debug() calls are
# silently dropped and only uvicorn's request access logs are visible.
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    if not settings.DEBUG
    else logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
# Quiet noisy third-party libraries unless we explicitly want DEBUG everywhere.
if not settings.DEBUG:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

from app.api.v1 import api  # noqa: E402 (import after logging setup)
from app.db.session import async_session_local  # noqa: E402

logger = getLogger(__name__)
ROUTE_PREFIX = "/api/v1"
app = FastAPI(title="StoryGen API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.router, prefix=ROUTE_PREFIX)


@app.get("/health", tags=["Health"], summary="Liveness / readiness check")
async def health():
    """Returns API status and a lightweight database ping."""
    db_ok = False
    db_error = None
    try:
        async with async_session_local() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception as exc:
        db_error = str(exc)
        logger.warning("Health check DB ping failed: %s", exc)

    payload = {
        "status": "ok" if db_ok else "degraded",
        "api": "ok",
        "database": "ok" if db_ok else "error",
    }
    if db_error and settings.DEBUG:
        payload["database_error"] = db_error

    return JSONResponse(
        status_code=200 if db_ok else 503,
        content=payload,
    )


@app.on_event("startup")
async def startup_event():
    apply_huggingface_token()
    apply_openai_settings()
    logger.info("Starting Up Application")
    if settings.openai_is_configured:
        logger.info("OpenAI configured: model=%s", settings.openai_model)
    else:
        logger.warning(
            "OPENAI_API_KEY is not set; AI pipeline stages will return 503 until configured."
        )
    if settings.HF_TOKEN:
        logger.info("HF_TOKEN configured for Hugging Face Hub downloads")
    else:
        logger.warning(
            "HF_TOKEN is not set; Docling model downloads may hit anonymous rate limits"
        )
    if settings.auth_disabled:
        logger.warning(
            "AUTH_DISABLED=true (DEBUG mode): Bearer auth is bypassed. "
            "Do not use this in production."
        )
