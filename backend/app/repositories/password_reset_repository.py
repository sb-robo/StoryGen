import secrets
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.password_reset_token import PasswordResetToken


class PasswordResetRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(32)

    async def create(self, user_id: int, token_hash: str, expires_at: datetime) -> PasswordResetToken:
        await self.db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None))
            .values(used_at=datetime.now(timezone.utc))
        )
        reset_token = PasswordResetToken(
            user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self.db.add(reset_token)
        return reset_token

    async def get_valid_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > now,
            )
        )
        return result.scalar_one_or_none()

    async def mark_used(self, token_hash: str) -> None:
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.token_hash == token_hash)
            .values(used_at=now)
        )
