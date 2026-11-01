import logging
from contextlib import asynccontextmanager
from logging import getLogger

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import apply_huggingface_token, apply_openai_settings, settings

# Configure app logging. Third-party HTTP/OpenAI libraries stay quiet so
# terminals show StoryGen process flow, not raw request payloads.
_log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(
    level=_log_level,
    format="%(asctime)s %(levelname)s %(name)s --> %(message)s",
    datefmt="%H:%M:%S",
)
for _noisy in ("httpx", "httpcore", "openai", "urllib3", "uvicorn.access"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

from app.api.v1 import api  # noqa: E402 (import after logging setup)
from app.db.session import async_session_local  # noqa: E402
from app.middleware.rate_limit import RateLimitMiddleware  # noqa: E402
from app.middleware.request_tracker import RequestTrackerMiddleware  # noqa: E402
from app.middleware.security_headers import SecurityHeadersMiddleware  # noqa: E402
from app.services.operations.startup import reclaim_orphaned_operations  # noqa: E402
from app.utils.process_tracker import track_error  # noqa: E402

logger = getLogger(__name__)
ROUTE_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    if settings.RATE_LIMIT_ENABLED:
        logger.info(
            "Rate limits enabled: auth=%s/min upload=%s/min ai=%s/min",
            settings.RATE_LIMIT_AUTH_PER_MINUTE,
            settings.RATE_LIMIT_UPLOAD_PER_MINUTE,
            settings.RATE_LIMIT_AI_PER_MINUTE,
        )
    try:
        orphaned = await reclaim_orphaned_operations()
        if orphaned:
            logger.warning(
                "Reclaimed %s orphaned async operation(s) left pending/running after restart",
                orphaned,
            )
    except Exception as exc:
        logger.warning("Orphan operation reclaim skipped: %s", exc)

    yield


app = FastAPI(title="StoryGen API", version="0.1.0", lifespan=lifespan)

# Starlette applies middleware in reverse add order (last added = outermost).
app.add_middleware(RequestTrackerMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.router, prefix=ROUTE_PREFIX)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc
    track_error(
        f"unhandled error on {request.method} {request.url.path}",
        exc=exc,
    )
    detail = str(exc) if settings.DEBUG else "Internal server error"
    return JSONResponse(status_code=500, content={"detail": detail})


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

