from app.services.email_service import _build_reset_message


def test_build_reset_message_contains_frontend_link(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "FRONTEND_BASE_URL", "http://app.test")
    monkeypatch.setattr(config.settings, "PASSWORD_RESET_EXPIRE_MINUTES", 15)
    monkeypatch.setattr(config.settings, "SMTP_FROM", "noreply@test.local")

    msg = _build_reset_message(to_email="user@example.com", reset_token="abc123")
    assert msg["To"] == "user@example.com"
    assert msg["From"] == "noreply@test.local"
    body = msg.get_body(preferencelist=("plain",)).get_content()
    assert "http://app.test/reset-password?token=abc123" in body
    assert "15 minutes" in body
