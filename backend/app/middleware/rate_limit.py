"""In-memory sliding-window rate limits for auth, uploads, and AI enqueue."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

API_PREFIX = "/api/v1"

# bucket_name -> client_key -> timestamps
_HITS: dict[str, dict[str, deque[float]]] = defaultdict(lambda: defaultdict(deque))
_LOCK = Lock()


def reset_rate_limit_state() -> None:
    """Clear in-memory counters (tests)."""
    with _LOCK:
        _HITS.clear()


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def match_rate_limit_bucket(method: str, path: str) -> tuple[str, int] | None:
    """
    Return (bucket_name, limit_per_minute) for rate-limited routes.

    Only mutating methods are limited — reads stay open.
    """
    if method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None

    p = path.rstrip("/") or "/"

    auth_paths = {
        f"{API_PREFIX}/auth/login",
        f"{API_PREFIX}/auth/register",
        f"{API_PREFIX}/auth/forgot-password",
        f"{API_PREFIX}/auth/reset-password",
        f"{API_PREFIX}/auth/refresh",
    }
    if p in auth_paths:
        return "auth", settings.RATE_LIMIT_AUTH_PER_MINUTE

    if p == f"{API_PREFIX}/brds/upload":
        return "upload", settings.RATE_LIMIT_UPLOAD_PER_MINUTE

    ai_suffixes = (
        "/features/extract",
        "/sub-features/generate",
        "/stories/generate",
        "/points/estimate",
        "/test-cases/generate",
        "/sub-features/generate-all",
        "/stories/generate-all",
        "/points/estimate-all",
        "/test-cases/generate-all",
        "/reparse",
    )
    if p.endswith("/retry") and "/operations/" in p:
        return "ai", settings.RATE_LIMIT_AI_PER_MINUTE
    if any(p.endswith(suffix) for suffix in ai_suffixes):
        return "ai", settings.RATE_LIMIT_AI_PER_MINUTE

    return None


def _allow(bucket: str, client: str, limit: int, window_seconds: int = 60) -> bool:
    now = time.monotonic()
    cutoff = now - window_seconds
    with _LOCK:
        q = _HITS[bucket][client]
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        matched = match_rate_limit_bucket(request.method, request.url.path)
        if matched is None:
            return await call_next(request)

        bucket, limit = matched
        if limit <= 0:
            return await call_next(request)

        client = _client_key(request)
        if not _allow(bucket, client, limit):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        f"Rate limit exceeded for {bucket} requests "
                        f"({limit}/minute). Try again shortly."
                    )
                },
                headers={"Retry-After": "60"},
            )
        return await call_next(request)
