from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.user import User
from app.db.session import async_session_local
from app.repositories.auth_repository import AuthRepository
from app.services.auth_service import AuthService
from app.services.brd import BrdService
from app.services.operations import OperationService
from app.services.user_service import UserService
from app.utils.jwt_handler import decode_token

# auto_error=False so AUTH_DISABLED can skip the Authorization header entirely.
bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_local() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)


def get_brd_service(db: AsyncSession = Depends(get_db)) -> BrdService:
    return BrdService(db)


def get_operation_service(db: AsyncSession = Depends(get_db)) -> OperationService:
    return OperationService(db)


async def _resolve_dev_user(db: AsyncSession) -> User:
    """Pick the local-dev identity when AUTH_DISABLED=true."""
    repo = AuthRepository(db)
    email = (settings.DEV_USER_EMAIL or settings.FIRST_ADMIN_EMAIL or "").strip().lower()
    if email:
        user = await repo.get_user_by_email(email)
        if user and user.is_active:
            return user
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"AUTH_DISABLED is on but no active user found for "
                f"DEV_USER_EMAIL/FIRST_ADMIN_EMAIL={email!r}. Register that user first."
            ),
        )

    user = await repo.get_first_active_user()
    if user:
        return user
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="AUTH_DISABLED is on but no users exist. Register a user first.",
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if settings.auth_disabled:
        return await _resolve_dev_user(db)

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = decode_token(credentials.credentials, token_type="access")
    user = await AuthRepository(db).get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return user


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
