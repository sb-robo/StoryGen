from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.async_operation import AsyncOperation, OperationStatus
from app.repositories.operation_repository import OperationRepository
from app.schemas.brd_schema import BrdDetailResponse
from app.schemas.operation_schema import OperationResponse, OperationResultResponse
from app.services.brd.service import BrdService


class OperationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = OperationRepository(db)
        self.brd_service = BrdService(db)

    def _to_response(self, operation: AsyncOperation) -> OperationResponse:
        return OperationResponse(
            operation_id=operation.id,
            operation_type=operation.operation_type,
            status=operation.status,
            resource_type=operation.resource_type,
            resource_id=operation.resource_id,
            error_message=operation.error_message,
            created_at=operation.created_at,
            updated_at=operation.updated_at,
            completed_at=operation.completed_at,
        )

    async def get_status(self, user_id: int, operation_id: str) -> OperationResponse:
        operation = await self.repo.get_by_id_for_user(operation_id, user_id)
        if not operation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation not found",
            )
        return self._to_response(operation)

    async def get_result(
        self, user_id: int, operation_id: str, *, include_text: bool = True
    ) -> OperationResultResponse:
        operation = await self.repo.get_by_id_for_user(operation_id, user_id)
        if not operation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation not found",
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
                    "status_url": f"/api/v1/brds/status/{operation.id}",
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

        if operation.resource_type != "brd" or operation.resource_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation has no result resource",
            )

        brd_detail: BrdDetailResponse = await self.brd_service.get_brd(
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
