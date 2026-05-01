from app.db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.user_schema import U


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
