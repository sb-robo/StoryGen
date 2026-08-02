from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from logging import getLogger

from app.api.v1 import api
from app.core.config import settings

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
    logger.info("Starting Up Application")
