from fastapi import FastAPI
from app.api.v1 import api
from logging import getLogger
# import asyncio

logger = getLogger(__name__)
ROUTE_PREFIX = "/api/v1"
app = FastAPI()


app.include_router(api.router, prefix=ROUTE_PREFIX)


@app.on_event("startup")
async def startup_event():
    logger.info("Starting Up Application")
