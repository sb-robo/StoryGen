from logging import getLogger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import api
from app.core.config import apply_huggingface_token, apply_openai_settings, settings
from app.db.session import async_session_local

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
