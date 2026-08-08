"""Log each API request with method, path, status, and duration."""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

_SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class RequestTrackerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path in _SKIP_PATHS:
            return await call_next(request)

        request_id = uuid.uuid4().hex[:8]
        started = time.perf_counter()
        display_path = path
        if request.url.query:
            display_path = f"{path}?{request.url.query}"

        logger.info("%s %s", request.method, display_path)
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "%s %s %s (%sms)",
                request.method,
                path,
                500,
                elapsed_ms,
            )
            raise

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "%s %s %s (%sms)",
            request.method,
            path,
            response.status_code,
            elapsed_ms,
        )
        response.headers["X-Request-Id"] = request_id
        return response
