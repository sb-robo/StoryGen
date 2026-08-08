import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.dependencies import get_current_admin, get_current_user, get_operation_service
from app.db.models.user import User
from app.db.session import async_session_local
from app.repositories.operation_repository import OperationRepository
from app.schemas.operation_schema import (
    OperationListResponse,
    OperationSortBy,
    OperationSortOrder,
    OperationStatusValue,
    OperationTypeValue,
)
from app.services.operations import OperationService
from app.utils.operation_urls import operation_result_url, operation_status_url

router = APIRouter()


@router.get(
    "",
    response_model=OperationListResponse,
    summary="List async operations (admin)",
    description=(
        "Admin-only paginated list of async operations across all users. "
        "Optionally filter by owning `user_id`, status, type, resource, and created date range."
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
    user_id: int | None = Query(
        default=None,
        ge=1,
        description="Filter by owning user id",
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
    _: User = Depends(get_current_admin),
    operation_service: OperationService = Depends(get_operation_service),
) -> OperationListResponse:
    return await operation_service.list_operations_admin(
        page=page,
        page_size=page_size,
        status_filter=status_filter.value if status_filter else None,
        operation_type=operation_type.value if operation_type else None,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        created_from=created_from,
        created_to=created_to,
        sort_by=sort_by.value,
        sort_order=sort_order.value,
    )


def _sse_pack(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.get(
    "/stream",
    summary="Stream operation status updates (SSE)",
    description=(
        "Server-Sent Events stream of the current user's operation updates. "
        "Optional filters: `resource_type`, `resource_id`, or comma-separated `operation_ids`. "
        "Use `fetch` with Authorization (native EventSource cannot send Bearer tokens). "
        "Falls back gracefully — clients may keep HTTP polling."
    ),
)
async def stream_operations(
    resource_type: str | None = Query(default=None, min_length=1, max_length=64),
    resource_id: int | None = Query(default=None, ge=1),
    operation_ids: str | None = Query(
        default=None,
        description="Comma-separated operation ids to watch",
    ),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    parsed_ids: list[str] | None = None
    if operation_ids:
        parsed_ids = [part.strip() for part in operation_ids.split(",") if part.strip()]
    user_id = current_user.id

    def _payload(op) -> dict:
        return {
            "operation_id": op.id,
            "operation_type": op.operation_type,
            "status": op.status,
            "resource_type": op.resource_type,
            "resource_id": op.resource_id,
            "error_message": op.error_message,
            "updated_at": op.updated_at,
            "done": op.status in {"succeeded", "failed"},
            "status_url": operation_status_url(op.id, op.operation_type),
            "result_url": operation_result_url(op.id, op.operation_type),
        }

    async def event_generator():
        cursor = datetime.now(timezone.utc)
        async with async_session_local() as session:
            repo = OperationRepository(session)
            snapshot = await repo.list_for_user(
                user_id,
                offset=0,
                limit=50,
                resource_type=resource_type,
                resource_id=resource_id,
            )
            if parsed_ids:
                id_set = set(parsed_ids)
                snapshot = [op for op in snapshot if op.id in id_set]
            for op in snapshot:
                yield _sse_pack("operation", _payload(op))
                if op.updated_at and op.updated_at > cursor:
                    cursor = op.updated_at

        yield _sse_pack("ready", {"ok": True})

        idle_ticks = 0
        while True:
            async with async_session_local() as session:
                repo = OperationRepository(session)
                updated = await repo.list_updated_since(
                    user_id=user_id,
                    updated_since=cursor,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    operation_ids=parsed_ids,
                    limit=50,
                )
            if updated:
                idle_ticks = 0
                for op in updated:
                    yield _sse_pack("operation", _payload(op))
                    if op.updated_at and op.updated_at > cursor:
                        cursor = op.updated_at
            else:
                idle_ticks += 1
                yield ": keepalive\n\n"
                if idle_ticks >= 150:  # ~5 minutes at 2s
                    yield _sse_pack("timeout", {"message": "stream idle timeout"})
                    break
            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
