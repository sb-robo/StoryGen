"""Lightweight SMTP email helpers (stdlib only — no extra deps)."""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage
from urllib.parse import quote

from app.core.config import settings
from app.utils.process_tracker import track, track_error


def _build_reset_message(*, to_email: str, reset_token: str) -> EmailMessage:
    base = (settings.FRONTEND_BASE_URL or "http://localhost:5173").rstrip("/")
    link = f"{base}/reset-password?token={quote(reset_token)}"
    minutes = settings.PASSWORD_RESET_EXPIRE_MINUTES

    text = (
        "Reset your StoryGen password\n\n"
        f"Use this link within {minutes} minutes:\n{link}\n\n"
        "If you did not request this, you can ignore this email.\n"
    )
    html = (
        "<p>Reset your StoryGen password</p>"
        f"<p><a href=\"{link}\">Choose a new password</a> "
        f"(link expires in {minutes} minutes).</p>"
        "<p>If you did not request this, you can ignore this email.</p>"
    )

    msg = EmailMessage()
    msg["Subject"] = "Reset your StoryGen password"
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USERNAME or "noreply@storygen.local"
    msg["To"] = to_email
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    return msg


def _send_smtp_sync(msg: EmailMessage) -> None:
    host = settings.SMTP_HOST
    if not host:
        raise RuntimeError("SMTP_HOST is not configured")

    port = settings.SMTP_PORT
    username = settings.SMTP_USERNAME
    password = settings.SMTP_PASSWORD
    use_tls = settings.SMTP_USE_TLS
    use_ssl = settings.SMTP_USE_SSL

    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=30) as server:
            if username:
                server.login(username, password or "")
            server.send_message(msg)
        return

    with smtplib.SMTP(host, port, timeout=30) as server:
        server.ehlo()
        if use_tls:
            server.starttls()
            server.ehlo()
        if username:
            server.login(username, password or "")
        server.send_message(msg)


async def send_password_reset_email(*, to_email: str, reset_token: str) -> bool:
    """
    Send a password-reset email when SMTP is configured.

    Returns True if an email was sent. When SMTP is not configured, returns False
    (callers may still expose the token under DEBUG).
    """
    if not settings.smtp_is_configured:
        if settings.DEBUG:
            base = (settings.FRONTEND_BASE_URL or "http://localhost:5173").rstrip("/")
            link = f"{base}/reset-password?token={quote(reset_token)}"
            track(
                "SMTP not configured; reset link logged in dev",
                to=to_email,
                link=link,
            )
        return False

    msg = _build_reset_message(to_email=to_email, reset_token=reset_token)
    try:
        await asyncio.to_thread(_send_smtp_sync, msg)
        track("sent password reset email", to=to_email)
        return True
    except Exception as exc:
        track_error("failed to send password reset email", exc=exc, to=to_email)
        raise
