from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user, get_operation_service
from app.db.models.user import User
from app.schemas.operation_schema import (
    OperationListResponse,
    OperationResponse,
    OperationSortBy,
    OperationSortOrder,
    OperationStatusValue,
    OperationTypeValue,
)
from app.services.operations import OperationService

router = APIRouter()


@router.get(
    "",
    response_model=OperationListResponse,
    summary="List my async operations",
    description=(
        "Paginated list of async operations for the current user. "
        "Supports filters by status, type, resource, and created date range."
    ),
)
async def list_operations(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: OperationStatusValue | None = Query(
        default=None,
        alias="status",
        description="Filter by operation status",
    ),
    operation_type: OperationTypeValue | None = Query(
        default=None,
        description="Filter by operation type",
    ),
    resource_type: str | None = Query(
        default=None,
        min_length=1,
        max_length=64,
        description="Filter by resource type (e.g. brd)",
    ),
    resource_id: int | None = Query(
        default=None,
        ge=1,
        description="Filter by linked resource id (e.g. BRD id)",
    ),
    created_from: datetime | None = Query(
        default=None,
        description="Include operations created at/after this timestamp (ISO 8601)",
    ),
    created_to: datetime | None = Query(
        default=None,
        description="Include operations created at/before this timestamp (ISO 8601)",
    ),
    sort_by: OperationSortBy = Query(
        default=OperationSortBy.CREATED_AT,
        description="Sort field",
    ),
    sort_order: OperationSortOrder = Query(
        default=OperationSortOrder.DESC,
        description="Sort direction",
    ),
    current_user: User = Depends(get_current_user),
    operation_service: OperationService = Depends(get_operation_service),
) -> OperationListResponse:
    return await operation_service.list_operations(
        current_user.id,
        page=page,
        page_size=page_size,
        status_filter=status_filter.value if status_filter else None,
        operation_type=operation_type.value if operation_type else None,
        resource_type=resource_type,
        resource_id=resource_id,
        created_from=created_from,
        created_to=created_to,
        sort_by=sort_by.value,
        sort_order=sort_order.value,
    )


@router.get(
    "/{operation_id}",
    response_model=OperationResponse,
    summary="Get operation by id",
    description="Returns a single async operation owned by the current user.",
)
async def get_operation(
    operation_id: str,
    current_user: User = Depends(get_current_user),
    operation_service: OperationService = Depends(get_operation_service),
) -> OperationResponse:
    return await operation_service.get_status(current_user.id, operation_id)
