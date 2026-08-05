from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from logging import getLogger

from app.api.v1 import api
from app.core.config import apply_huggingface_token, settings

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


@app.on_event("startup")
async def startup_event():
    apply_huggingface_token()
    logger.info("Starting Up Application")
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
