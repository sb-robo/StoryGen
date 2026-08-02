from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_admin, get_current_user, get_user_service
from app.db.models.user import User
from app.schemas.user_schema import AdminUserUpdateRequest, UserListResponse, UserResponse, UserUpdateRequest
from app.services.user_service import UserService

router = APIRouter()


@router.get("/me", response_model=UserResponse, summary="Get my profile")
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update my profile",
    description="Update your display name and/or email. Requires a valid access token.",
)
async def update_me(
    data: UserUpdateRequest = Body(
        openapi_examples={
            "update_name": {
                "summary": "Change display name",
                "value": {"name": "Suraj Biswas"},
            },
            "update_email": {
                "summary": "Change email",
                "value": {"email": "suraj.new@example.com"},
            },
        }
    ),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    return await user_service.update_me(current_user, data)


@router.get(
    "",
    response_model=UserListResponse,
    summary="List all users",
    description="Admin only. Paginated list of registered users.",
)
async def list_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
    _: User = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service),
) -> UserListResponse:
    return await user_service.list_users(skip=skip, limit=limit)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Available to the user themselves or an admin.",
)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to view this user",
        )
    return await user_service.get_user(user_id)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Admin update user",
    description=(
        "Admin only. Partial update — send only the fields you want to change. "
        "Cannot deactivate yourself or remove your own admin access."
    ),
)
async def admin_update_user(
    user_id: int,
    data: AdminUserUpdateRequest = Body(
        openapi_examples={
            "rename_user": {
                "summary": "Rename user",
                "value": {"name": "Jane Doe"},
            },
            "deactivate_user": {
                "summary": "Deactivate account",
                "value": {"is_active": False},
            },
            "promote_to_admin": {
                "summary": "Grant admin access",
                "value": {"is_admin": True, "is_active": True},
            },
        }
    ),
    current_admin: User = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    return await user_service.admin_update_user(user_id, data, current_admin)
