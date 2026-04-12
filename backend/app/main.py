from fastapi import FastAPI
from app.api.v1 import users
from logging import getLogger
# import asyncio

logger = getLogger(__name__)
ROUTE_PREFIX = "/api/v1"

app = FastAPI()


app.include_router(users.router, prefix=f"{ROUTE_PREFIX}/user", tags=["User"])


@app.on_event("startup")
async def startup_event():
    logger.info("Starting Up Application")
