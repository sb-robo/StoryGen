"""Health endpoint smoke tests."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


def test_health_ok_when_db_ping_succeeds():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=None)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    factory = MagicMock(return_value=session)

    with patch("app.main.async_session_local", factory):
        with TestClient(app) as client:
            response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["api"] == "ok"
    assert body["database"] == "ok"


def test_health_degraded_when_db_ping_fails():
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=RuntimeError("db down"))
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    factory = MagicMock(return_value=session)

    with patch("app.main.async_session_local", factory):
        with TestClient(app) as client:
            response = client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "error"
