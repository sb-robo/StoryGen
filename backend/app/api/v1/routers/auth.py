from fastapi import APIRouter, Body, Depends, Query, status

from app.core.dependencies import get_auth_service, get_current_admin, get_current_user, get_user_service
from app.db.models.user import User
from app.schemas.auth_schema import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginResponse,
    MessageResponse,
    PasswordResetConfirmRequest,
    RefreshTokenRequest,
    UserLoginRequest,
    UserPasswordChangeRequest,
    UserRegisterRequest,
)
from app.schemas.user_schema import AdminUserUpdateRequest, UserListResponse, UserResponse, UserUpdateRequest
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter()


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    return await auth_service.register(data)


@router.post("/login", response_model=LoginResponse)
async def login(
    data: UserLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    return await auth_service.login(data)


@router.post("/refresh", response_model=LoginResponse)
async def refresh_tokens(
    data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    return await auth_service.refresh(data.refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    return await auth_service.logout(data.refresh_token)


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    return await auth_service.logout_all(current_user)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> ForgotPasswordResponse:
    return await auth_service.forgot_password(data.email)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    data: PasswordResetConfirmRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    return await auth_service.reset_password(data)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    data: UserPasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    return await auth_service.change_password(data, current_user)
