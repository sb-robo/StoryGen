from app.db.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.auth_schema import UserRegisterRequest


class AuthRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, user: UserRegisterRequest, hashed_password: str) -> User:
        db_user = User(name=user.name, email=user.email, hashed_password=hashed_password)
        self.db.add(db_user)
        return db_user

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_password(self, user: User, hashed_password: str) -> User | None:
        user.hashed_password = hashed_password
        self.db.add(user)
        return user
