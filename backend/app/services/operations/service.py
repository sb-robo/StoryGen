from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.async_operation import AsyncOperation, OperationStatus, OperationType
from app.db.models.user import User
from app.repositories.llm_call_log_repository import LlmCallLogRepository
from app.repositories.operation_repository import OperationRepository
from app.schemas.feature_schema import FeatureExtractionResultResponse
from app.schemas.operation_schema import (
    OperationListResponse,
    OperationResponse,
    OperationResultResponse,
)
from app.schemas.story_schema import (
    StoryGenerationResultResponse,
    StoryPointsResultResponse,
)
from app.schemas.sub_feature_schema import SubFeatureGenerationResultResponse
from app.schemas.test_case_schema import TestCaseGenerationResultResponse
from app.services.ai.feature_service import FeatureService
from app.services.ai.story_points_service import StoryPointsService
from app.services.ai.story_service import StoryService
from app.services.ai.sub_feature_service import SubFeatureService
from app.services.ai.test_case_service import TestCaseService
from app.services.brd.service import BrdService
from app.utils.operation_progress import format_operation_progress
from app.utils.operation_urls import operation_status_url


class OperationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = OperationRepository(db)
        self.llm_log_repo = LlmCallLogRepository(db)
        self.brd_service = BrdService(db)
        self.feature_service = FeatureService(db)
        self.sub_feature_service = SubFeatureService(db)
        self.story_service = StoryService(db)
        self.story_points_service = StoryPointsService(db)
        self.test_case_service = TestCaseService(db)

    def _to_response(
        self,
        operation: AsyncOperation,
        *,
        include_user_id: bool = False,
        progress: str | None = None,
    ) -> OperationResponse:
        return OperationResponse(
            operation_id=operation.id,
            operation_type=operation.operation_type,
            status=operation.status,
            user_id=operation.user_id if include_user_id else None,
            resource_type=operation.resource_type,
            resource_id=operation.resource_id,
            error_message=operation.error_message,
            progress=progress
            if progress is not None
            else format_operation_progress(status=operation.status, latest_log=None),
            created_at=operation.created_at,
            updated_at=operation.updated_at,
            completed_at=operation.completed_at,
        )

    async def _progress_for(self, operation: AsyncOperation) -> str:
        latest = None
        if operation.status == OperationStatus.RUNNING.value:
            latest = await self.llm_log_repo.latest_for_operation(operation.id)
        return format_operation_progress(status=operation.status, latest_log=latest)

    async def list_operations_admin(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status_filter: str | None = None,
        operation_type: str | None = None,
        resource_type: str | None = None,
        resource_id: int | None = None,
        user_id: int | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> OperationListResponse:
        """Admin list across all users (optional filter by owning user_id)."""
        if created_from and created_to and created_from > created_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="created_from must be earlier than or equal to created_to",
            )

        offset = (page - 1) * page_size
        filters = {
            "status": status_filter,
            "operation_type": operation_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "created_from": created_from,
            "created_to": created_to,
        }
        items = await self.repo.list_operations(
            user_id=user_id,
            offset=offset,
            limit=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            **filters,
        )
        total = await self.repo.count_operations(user_id=user_id, **filters)
        return OperationListResponse.build(
            items=[self._to_response(item, include_user_id=True) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            status=status_filter,
            operation_type=operation_type,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def _get_owned_operation(
        self,
        user_id: int,
        operation_id: str,
        *,
        allowed_types: set[str] | None = None,
    ) -> AsyncOperation:
        operation = await self.repo.get_by_id_for_user(operation_id, user_id)
        if not operation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation not found",
            )
        if allowed_types is not None and operation.operation_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation not found",
            )
        return operation

    async def get_status(
        self,
        user_id: int,
        operation_id: str,
        *,
        allowed_types: set[str] | None = None,
    ) -> OperationResponse:
        operation = await self._get_owned_operation(
            user_id, operation_id, allowed_types=allowed_types
        )
        progress = await self._progress_for(operation)
        return self._to_response(operation, progress=progress)

    async def get_result(
        self,
        user_id: int,
        operation_id: str,
        *,
        allowed_types: set[str] | None = None,
        include_text: bool = True,
    ) -> OperationResultResponse:
        operation = await self._get_owned_operation(
            user_id, operation_id, allowed_types=allowed_types
        )

        if operation.status in {
            OperationStatus.PENDING.value,
            OperationStatus.RUNNING.value,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Operation is still in progress",
                    "operation_id": operation.id,
                    "status": operation.status,
                    "status_url": operation_status_url(
                        operation.id, operation.operation_type
                    ),
                },
            )

        if operation.status == OperationStatus.FAILED.value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Operation failed",
                    "operation_id": operation.id,
                    "status": operation.status,
                    "error_message": operation.error_message,
                },
            )

        if operation.status == OperationStatus.CANCELLED.value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Operation was cancelled",
                    "operation_id": operation.id,
                    "status": operation.status,
                    "error_message": operation.error_message,
                },
            )

        if operation.resource_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation has no result resource",
            )

        if operation.operation_type == OperationType.FEATURE_EXTRACTION.value:
            extraction_result: FeatureExtractionResultResponse = (
                await self.feature_service.get_extraction_result(
                    user_id, operation_id
                )
            )
            return OperationResultResponse(
                operation_id=operation.id,
                status=operation.status,
                resource_type=operation.resource_type,
                resource_id=operation.resource_id,
                result=extraction_result.model_dump(mode="json"),
            )

        if operation.operation_type == OperationType.SUB_FEATURE_GENERATION.value:
            sub_feature_result: SubFeatureGenerationResultResponse = (
                await self.sub_feature_service.get_generation_result(
                    user_id, operation_id
                )
            )
            return OperationResultResponse(
                operation_id=operation.id,
                status=operation.status,
                resource_type=operation.resource_type,
                resource_id=operation.resource_id,
                result=sub_feature_result.model_dump(mode="json"),
            )

        if operation.operation_type == OperationType.STORY_GENERATION.value:
            story_result: StoryGenerationResultResponse = (
                await self.story_service.get_generation_result(
                    user_id, operation_id
                )
            )
            return OperationResultResponse(
                operation_id=operation.id,
                status=operation.status,
                resource_type=operation.resource_type,
                resource_id=operation.resource_id,
                result=story_result.model_dump(mode="json"),
            )

        if operation.operation_type == OperationType.STORY_POINT_ESTIMATION.value:
            points_result: StoryPointsResultResponse = (
                await self.story_points_service.get_estimation_result(
                    user_id, operation_id
                )
            )
            return OperationResultResponse(
                operation_id=operation.id,
                status=operation.status,
                resource_type=operation.resource_type,
                resource_id=operation.resource_id,
                result=points_result.model_dump(mode="json"),
            )

        if operation.operation_type == OperationType.TEST_CASE_GENERATION.value:
            test_case_result: TestCaseGenerationResultResponse = (
                await self.test_case_service.get_generation_result(
                    user_id, operation_id
                )
            )
            return OperationResultResponse(
                operation_id=operation.id,
                status=operation.status,
                resource_type=operation.resource_type,
                resource_id=operation.resource_id,
                result=test_case_result.model_dump(mode="json"),
            )

        if operation.resource_type != "brd":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation has no result resource",
            )

        brd_detail = await self.brd_service.get_brd(
            user_id,
            operation.resource_id,
            include_text=include_text,
        )
        return OperationResultResponse(
            operation_id=operation.id,
            status=operation.status,
            resource_type=operation.resource_type,
            resource_id=operation.resource_id,
            result=brd_detail.model_dump(mode="json"),
        )

    async def _resolve_operation_for_actor(
        self, user: User, operation_id: str
    ) -> AsyncOperation:
        """Owners see their ops; admins can act on any operation."""
        if user.is_admin:
            operation = await self.repo.get_by_id(operation_id)
            if not operation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Operation not found",
                )
            return operation
        return await self._get_owned_operation(user.id, operation_id)

    async def cancel_operation(
        self, user: User, operation_id: str
    ) -> OperationResponse:
        operation = await self._resolve_operation_for_actor(user, operation_id)
        if operation.status not in {
            OperationStatus.PENDING.value,
            OperationStatus.RUNNING.value,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending or running operations can be cancelled.",
            )
        operation = await self.repo.mark_cancelled(operation)
        await self.db.commit()
        return self._to_response(operation, include_user_id=user.is_admin)

    async def retry_operation(
        self, user: User, operation_id: str
    ) -> OperationResponse:
        """
        Enqueue a fresh operation for the same type/resource as a failed/cancelled one.
        Caller must schedule the matching background task.
        Retries run as the original owner (admins may retry other users' ops).
        """
        operation = await self._resolve_operation_for_actor(user, operation_id)
        if operation.status not in {
            OperationStatus.FAILED.value,
            OperationStatus.CANCELLED.value,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only failed or cancelled operations can be retried.",
            )
        if operation.resource_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Operation has no resource to retry against.",
            )

        owner_id = operation.user_id
        op_type = operation.operation_type
        resource_id = operation.resource_id

        if op_type == OperationType.FEATURE_EXTRACTION.value:
            return await self.feature_service.enqueue_extraction(owner_id, resource_id)
        if op_type == OperationType.SUB_FEATURE_GENERATION.value:
            return await self.sub_feature_service.enqueue_generation(
                owner_id, resource_id
            )
        if op_type == OperationType.STORY_GENERATION.value:
            return await self.story_service.enqueue_generation(owner_id, resource_id)
        if op_type == OperationType.STORY_POINT_ESTIMATION.value:
            return await self.story_points_service.enqueue_estimation(
                owner_id, resource_id
            )
        if op_type == OperationType.TEST_CASE_GENERATION.value:
            return await self.test_case_service.enqueue_generation(
                owner_id, resource_id
            )
        if op_type in {
            OperationType.BRD_UPLOAD.value,
            OperationType.BRD_REPARSE.value,
        }:
            return await self.brd_service.enqueue_reparse(owner_id, resource_id)

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Retry is not supported for operation type '{op_type}'.",
        )
