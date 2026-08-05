from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.async_operation import AsyncOperation, OperationStatus


class OperationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, operation: AsyncOperation) -> AsyncOperation:
        self.db.add(operation)
        await self.db.flush()
        await self.db.refresh(operation)
        return operation

    async def get_by_id(self, operation_id: str) -> AsyncOperation | None:
        result = await self.db.execute(
            select(AsyncOperation).where(AsyncOperation.id == operation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_user(
        self, operation_id: str, user_id: int
    ) -> AsyncOperation | None:
        result = await self.db.execute(
            select(AsyncOperation).where(
                AsyncOperation.id == operation_id,
                AsyncOperation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def mark_running(self, operation: AsyncOperation) -> AsyncOperation:
        operation.status = OperationStatus.RUNNING.value
        operation.error_message = None
        return await self.update(operation)

    async def mark_succeeded(self, operation: AsyncOperation) -> AsyncOperation:
        operation.status = OperationStatus.SUCCEEDED.value
        operation.error_message = None
        operation.completed_at = datetime.now(timezone.utc)
        return await self.update(operation)

    async def mark_failed(
        self, operation: AsyncOperation, error_message: str
    ) -> AsyncOperation:
        operation.status = OperationStatus.FAILED.value
        operation.error_message = error_message
        operation.completed_at = datetime.now(timezone.utc)
        return await self.update(operation)

    async def update(self, operation: AsyncOperation) -> AsyncOperation:
        self.db.add(operation)
        await self.db.flush()
        await self.db.refresh(operation)
        return operation
