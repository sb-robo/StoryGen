from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import (
    AdminUserUpdateRequest,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
)


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)

    async def get_user(self, user_id: int) -> UserResponse:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return UserResponse.model_validate(user)

    async def list_users(self, skip: int = 0, limit: int = 20) -> UserListResponse:
        users = await self.repo.get_all(skip=skip, limit=limit)
        total = await self.repo.count_all()
        return UserListResponse(
            items=[UserResponse.model_validate(user) for user in users],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def update_me(self, user: User, data: UserUpdateRequest) -> UserResponse:
        if data.email is not None and data.email != user.email:
            existing = await self.repo.get_by_email(data.email)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered",
                )
            user.email = data.email

        if data.name is not None:
            user.name = data.name

        await self.repo.update(user)
        await self.db.refresh(user)
        return UserResponse.model_validate(user)

    async def admin_update_user(
        self, user_id: int, data: AdminUserUpdateRequest, current_admin: User
    ) -> UserResponse:
        if current_admin.id == user_id:
            if data.is_active is False:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You cannot deactivate your own account",
                )
            if data.is_admin is False:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You cannot remove your own admin access",
                )

        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if data.name is not None:
            user.name = data.name
        if data.is_active is not None:
            user.is_active = data.is_active
        if data.is_admin is not None:
            user.is_admin = data.is_admin

        await self.repo.update(user)
        await self.db.refresh(user)
        return UserResponse.model_validate(user)
