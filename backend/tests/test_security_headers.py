from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


def test_health_includes_security_headers():
    with patch("app.main.async_session_local") as session_local:
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        session.execute = AsyncMock()
        session_local.return_value = session

        with patch("app.main.reclaim_orphaned_operations", new=AsyncMock(return_value=0)):
            with TestClient(app) as client:
                response = client.get("/health")

    assert response.status_code in {200, 503}
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
