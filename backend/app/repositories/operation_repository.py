from datetime import datetime, timezone

from sqlalchemy import Select, delete, func, select
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

    def _filtered_query(
        self,
        user_id: int,
        *,
        status: str | None = None,
        operation_type: str | None = None,
        resource_type: str | None = None,
        resource_id: int | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> Select:
        query = select(AsyncOperation).where(AsyncOperation.user_id == user_id)
        if status:
            query = query.where(AsyncOperation.status == status)
        if operation_type:
            query = query.where(AsyncOperation.operation_type == operation_type)
        if resource_type:
            query = query.where(AsyncOperation.resource_type == resource_type)
        if resource_id is not None:
            query = query.where(AsyncOperation.resource_id == resource_id)
        if created_from is not None:
            query = query.where(AsyncOperation.created_at >= created_from)
        if created_to is not None:
            query = query.where(AsyncOperation.created_at <= created_to)
        return query

    async def list_for_user(
        self,
        user_id: int,
        *,
        offset: int,
        limit: int,
        status: str | None = None,
        operation_type: str | None = None,
        resource_type: str | None = None,
        resource_id: int | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[AsyncOperation]:
        query = self._filtered_query(
            user_id,
            status=status,
            operation_type=operation_type,
            resource_type=resource_type,
            resource_id=resource_id,
            created_from=created_from,
            created_to=created_to,
        )

        sort_column = {
            "created_at": AsyncOperation.created_at,
            "updated_at": AsyncOperation.updated_at,
            "completed_at": AsyncOperation.completed_at,
        }.get(sort_by, AsyncOperation.created_at)

        order_expr = sort_column.asc() if sort_order == "asc" else sort_column.desc()
        # Keep NULLs last for completed_at ascending/descending in a predictable way.
        if sort_by == "completed_at":
            order_expr = order_expr.nulls_last()

        result = await self.db.execute(
            query.order_by(order_expr, AsyncOperation.id.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def count_for_user(
        self,
        user_id: int,
        *,
        status: str | None = None,
        operation_type: str | None = None,
        resource_type: str | None = None,
        resource_id: int | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> int:
        base = self._filtered_query(
            user_id,
            status=status,
            operation_type=operation_type,
            resource_type=resource_type,
            resource_id=resource_id,
            created_from=created_from,
            created_to=created_to,
        )
        result = await self.db.execute(
            select(func.count()).select_from(base.subquery())
        )
        return result.scalar_one()

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

    async def delete_for_resource(
        self, user_id: int, resource_type: str, resource_id: int
    ) -> None:
        """Drop operation history tied to a resource that is being deleted."""
        await self.db.execute(
            delete(AsyncOperation).where(
                AsyncOperation.user_id == user_id,
                AsyncOperation.resource_type == resource_type,
                AsyncOperation.resource_id == resource_id,
            )
        )
        await self.db.flush()
