from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.user import User
from app.repositories.auth_repository import AuthRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.schemas.auth_schema import (
    ForgotPasswordResponse,
    LoginResponse,
    PasswordResetConfirmRequest,
    UserLoginRequest,
    UserPasswordChangeRequest,
    UserRegisterRequest,
)
from app.schemas.user_schema import UserResponse
from app.utils.jwt_handler import create_access_token, create_refresh_token, decode_token
from app.utils.password_handler import hash_password, verify_password
from app.utils.token_hash import hash_token


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AuthRepository(db)
        self.refresh_repo = RefreshTokenRepository(db)
        self.reset_repo = PasswordResetRepository(db)

    async def _should_be_admin(self, email: str) -> bool:
        admin_count = await self.repo.count_admins()
        if admin_count == 0:
            return True
        if settings.FIRST_ADMIN_EMAIL and email == settings.FIRST_ADMIN_EMAIL.strip().lower():
            return True
        return False

    async def _issue_tokens(self, user: User) -> LoginResponse:
        refresh_token = create_refresh_token(user.id)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.refresh_repo.create(user.id, hash_token(refresh_token), expires_at)

        return LoginResponse(
            access_token=create_access_token(user.id),
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user),
        )

    async def register(self, data: UserRegisterRequest) -> LoginResponse:
        existing_user = await self.repo.get_user_by_email(data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        is_admin = await self._should_be_admin(data.email)
        hashed_password = hash_password(data.password)
        user = await self.repo.create_user(data, hashed_password, is_admin=is_admin)
        await self.db.flush()
        await self.db.refresh(user)
        return await self._issue_tokens(user)

    async def login(self, data: UserLoginRequest) -> LoginResponse:
        user = await self.repo.get_user_by_email(data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user",
            )

        return await self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> LoginResponse:
        user_id = decode_token(refresh_token, token_type="refresh")
        session = await self.refresh_repo.get_valid_by_hash(hash_token(refresh_token))
        if not session or session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        user = await self.repo.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        await self.refresh_repo.revoke_by_hash(hash_token(refresh_token))
        return await self._issue_tokens(user)

    async def logout(self, refresh_token: str) -> dict:
        await self.refresh_repo.revoke_by_hash(hash_token(refresh_token))
        return {"message": "Logged out successfully"}

    async def logout_all(self, user: User) -> dict:
        await self.refresh_repo.revoke_all_for_user(user.id)
        return {"message": "Logged out from all devices"}

    async def forgot_password(self, email: str) -> ForgotPasswordResponse:
        message = "If that email exists, a reset link has been sent"
        user = await self.repo.get_user_by_email(email)
        if not user:
            return ForgotPasswordResponse(message=message)

        raw_token = self.reset_repo.generate_token()
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES
        )
        await self.reset_repo.create(user.id, hash_token(raw_token), expires_at)

        return ForgotPasswordResponse(
            message=message,
            reset_token=raw_token if settings.DEBUG else None,
        )

    async def reset_password(self, data: PasswordResetConfirmRequest) -> dict:
        reset_token = await self.reset_repo.get_valid_by_hash(hash_token(data.token))
        if not reset_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        user = await self.repo.get_user_by_id(reset_token.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        hashed_password = hash_password(data.password)
        await self.repo.update_password(user, hashed_password)
        await self.reset_repo.mark_used(hash_token(data.token))
        await self.refresh_repo.revoke_all_for_user(user.id)
        return {"message": "Password reset successfully. Please log in."}

    async def change_password(self, data: UserPasswordChangeRequest, user: User) -> dict:
        if not verify_password(data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        hashed_password = hash_password(data.password)
        await self.repo.update_password(user, hashed_password)
        await self.refresh_repo.revoke_all_for_user(user.id)
        return {"message": "Password changed successfully. Please log in again."}
