"""Shared helpers for AI pipeline services."""

from fastapi import HTTPException, status

from app.db.models.async_operation import AsyncOperation, OperationStatus
from app.repositories.operation_repository import OperationRepository
from app.schemas.operation_schema import OperationResponse
from app.utils.operation_progress import format_operation_progress


def operation_response(operation: AsyncOperation) -> OperationResponse:
    return OperationResponse(
        operation_id=operation.id,
        operation_type=operation.operation_type,
        status=operation.status,
        resource_type=operation.resource_type,
        resource_id=operation.resource_id,
        error_message=operation.error_message,
        progress=format_operation_progress(status=operation.status, latest_log=None),
        created_at=operation.created_at,
        updated_at=operation.updated_at,
        completed_at=operation.completed_at,
    )


async def ensure_operation_not_running(
    operation_repo: OperationRepository,
    *,
    user_id: int,
    operation_type: str,
    resource_type: str,
    resource_id: int,
    conflict_message: str,
) -> None:
    for op_status in (OperationStatus.RUNNING.value, OperationStatus.PENDING.value):
        ops = await operation_repo.list_for_user(
            user_id,
            offset=0,
            limit=1,
            operation_type=operation_type,
            resource_type=resource_type,
            resource_id=resource_id,
            status=op_status,
        )
        if ops:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=conflict_message,
            )
