from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.schemas.auth_schema import UserRegisterRequest


class AuthRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(
        self, user: UserRegisterRequest, hashed_password: str, *, is_admin: bool = False
    ) -> User:
        db_user = User(
            name=user.name,
            email=user.email,
            hashed_password=hashed_password,
            is_admin=is_admin,
        )
        self.db.add(db_user)
        return db_user

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_password(self, user: User, hashed_password: str) -> User:
        user.hashed_password = hashed_password
        self.db.add(user)
        return user

    async def count_admins(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(User).where(User.is_admin.is_(True))
        )
        return result.scalar_one()
