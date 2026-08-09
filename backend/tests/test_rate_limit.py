from unittest.mock import MagicMock

import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.middleware.rate_limit import (
    RateLimitMiddleware,
    match_rate_limit_bucket,
    reset_rate_limit_state,
)


def test_match_auth_login():
    assert match_rate_limit_bucket("POST", "/api/v1/auth/login")[0] == "auth"


def test_match_upload():
    assert match_rate_limit_bucket("POST", "/api/v1/brds/upload")[0] == "upload"


def test_match_ai_extract_and_retry():
    assert (
        match_rate_limit_bucket("POST", "/api/v1/brds/12/features/extract")[0] == "ai"
    )
    assert match_rate_limit_bucket("POST", "/api/v1/operations/abc/retry")[0] == "ai"


def test_match_skips_gets_and_unlisted():
    assert match_rate_limit_bucket("GET", "/api/v1/auth/login") is None
    assert match_rate_limit_bucket("POST", "/api/v1/brds/1/pipeline") is None


def _login_request() -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/auth/login",
        "raw_path": b"/api/v1/auth/login",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_middleware_returns_429_when_over_limit(monkeypatch):
    reset_rate_limit_state()
    monkeypatch.setattr("app.middleware.rate_limit.settings.RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(
        "app.middleware.rate_limit.settings.RATE_LIMIT_AUTH_PER_MINUTE", 2
    )

    middleware = RateLimitMiddleware(app=MagicMock())
    allowed = 0

    async def ok(_request):
        nonlocal allowed
        allowed += 1
        return Response(status_code=200)

    assert (await middleware.dispatch(_login_request(), ok)).status_code == 200
    assert (await middleware.dispatch(_login_request(), ok)).status_code == 200
    blocked = await middleware.dispatch(_login_request(), ok)
    assert blocked.status_code == 429
    assert blocked.headers.get("Retry-After") == "60"
    assert allowed == 2
