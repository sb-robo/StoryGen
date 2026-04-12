from app.db.session import async_session_local
from asyncio import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_local() as session:
        try:
            yield session
            await session.commit()
        finally:
            await session.rollback()
            raise
