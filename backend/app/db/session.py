from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.ECHO_SQL)
async_session_local = async_sessionmaker(
    AsyncSession, autocommit=False, autoflush=False, bind=engine
)
