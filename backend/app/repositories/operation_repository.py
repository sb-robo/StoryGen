from datetime import datetime, timezone

from sqlalchemy import Select, delete, func, select, update
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
        *,
        user_id: int | None = None,
        status: str | None = None,
        operation_type: str | None = None,
        resource_type: str | None = None,
        resource_id: int | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_since: datetime | None = None,
        operation_ids: list[str] | None = None,
    ) -> Select:
        query = select(AsyncOperation)
        if user_id is not None:
            query = query.where(AsyncOperation.user_id == user_id)
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
        if updated_since is not None:
            query = query.where(AsyncOperation.updated_at > updated_since)
        if operation_ids:
            query = query.where(AsyncOperation.id.in_(operation_ids))
        return query

    async def list_operations(
        self,
        *,
        user_id: int | None = None,
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
            user_id=user_id,
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
        return await self.list_operations(
            user_id=user_id,
            offset=offset,
            limit=limit,
            status=status,
            operation_type=operation_type,
            resource_type=resource_type,
            resource_id=resource_id,
            created_from=created_from,
            created_to=created_to,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def count_operations(
        self,
        *,
        user_id: int | None = None,
        status: str | None = None,
        operation_type: str | None = None,
        resource_type: str | None = None,
        resource_id: int | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> int:
        base = self._filtered_query(
            user_id=user_id,
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
        return await self.count_operations(
            user_id=user_id,
            status=status,
            operation_type=operation_type,
            resource_type=resource_type,
            resource_id=resource_id,
            created_from=created_from,
            created_to=created_to,
        )

    async def list_updated_since(
        self,
        *,
        user_id: int,
        updated_since: datetime | None = None,
        resource_type: str | None = None,
        resource_id: int | None = None,
        operation_ids: list[str] | None = None,
        limit: int = 100,
    ) -> list[AsyncOperation]:
        query = self._filtered_query(
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            updated_since=updated_since,
            operation_ids=operation_ids,
        )
        result = await self.db.execute(
            query.order_by(AsyncOperation.updated_at.asc(), AsyncOperation.id.asc()).limit(
                limit
            )
        )
        return list(result.scalars().all())

    async def mark_running(self, operation: AsyncOperation) -> AsyncOperation:
        if operation.status == OperationStatus.CANCELLED.value:
            return operation
        operation.status = OperationStatus.RUNNING.value
        operation.error_message = None
        return await self.update(operation)

    async def mark_succeeded(self, operation: AsyncOperation) -> AsyncOperation:
        if operation.status == OperationStatus.CANCELLED.value:
            return operation
        operation.status = OperationStatus.SUCCEEDED.value
        operation.error_message = None
        operation.completed_at = datetime.now(timezone.utc)
        return await self.update(operation)

    async def mark_failed(
        self, operation: AsyncOperation, error_message: str
    ) -> AsyncOperation:
        if operation.status == OperationStatus.CANCELLED.value:
            return operation
        operation.status = OperationStatus.FAILED.value
        operation.error_message = error_message
        operation.completed_at = datetime.now(timezone.utc)
        return await self.update(operation)

    async def mark_cancelled(
        self, operation: AsyncOperation, *, reason: str | None = None
    ) -> AsyncOperation:
        operation.status = OperationStatus.CANCELLED.value
        operation.error_message = reason or "Cancelled by user"
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

    async def fail_orphaned_in_flight(self, *, reason: str) -> int:
        """
        Mark pending/running ops as failed after a process restart.

        In-process BackgroundTasks do not survive restarts; reclaiming stuck
        rows keeps the ops UI honest until a durable worker exists.
        """
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            update(AsyncOperation)
            .where(
                AsyncOperation.status.in_(
                    [
                        OperationStatus.PENDING.value,
                        OperationStatus.RUNNING.value,
                    ]
                )
            )
            .values(
                status=OperationStatus.FAILED.value,
                error_message=reason,
                completed_at=now,
                updated_at=now,
            )
        )
        await self.db.flush()
        return int(result.rowcount or 0)
