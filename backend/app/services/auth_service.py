from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.repositories.auth_repository import AuthRepository
from app.schemas.auth_schema import (
    UserLoginRequest,
    UserPasswordChangeRequest,
    UserPasswordResetRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.utils.password_handler import hash_password, verify_password


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AuthRepository(db)

    async def register(self, data: UserRegisterRequest) -> UserResponse:
        existing_user = await self.repo.get_user_by_email(data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )

        hashed_password = hash_password(data.password)
        user = await self.repo.create_user(data, hashed_password)
        await self.db.commit()
        await self.db.refresh(user)
        return UserResponse.model_validate(user)

    async def login(self, data: UserLoginRequest) -> UserResponse:
        user = await self.repo.get_user_by_email(data.email)
        if not user or verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials"
            )

        return UserResponse.model_validate(user)

    async def change_password(self, data: UserPasswordChangeRequest, user: User) -> dict:
        if not verify_password(data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credentials"
            )

        hashed_password = hash_password(data.password)
        await self.repo.update_password(user, hashed_password)
        await self.db.commit()
        return {"messgae": "Password changed successfully"}

    async def reset_password(self, data: UserPasswordResetRequest, user: User) -> dict:
        pass
