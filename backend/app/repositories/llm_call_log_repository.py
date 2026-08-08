from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.llm_call_log import LlmCallLog


class LlmCallLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, log: LlmCallLog) -> LlmCallLog:
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log

    async def list_for_brd(
        self,
        brd_id: int,
        *,
        user_id: int | None = None,
        limit: int = 50,
    ) -> list[LlmCallLog]:
        query = (
            select(LlmCallLog)
            .where(LlmCallLog.brd_id == brd_id)
            .order_by(LlmCallLog.created_at.desc())
            .limit(limit)
        )
        if user_id is not None:
            query = query.where(LlmCallLog.user_id == user_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def latest_for_operation(self, operation_id: str) -> LlmCallLog | None:
        result = await self.db.execute(
            select(LlmCallLog)
            .where(LlmCallLog.operation_id == operation_id)
            .order_by(LlmCallLog.created_at.desc(), LlmCallLog.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def latest_for_operations(
        self, operation_ids: list[str]
    ) -> dict[str, LlmCallLog]:
        if not operation_ids:
            return {}
        # Fetch recent logs for these ops, keep newest per operation_id.
        result = await self.db.execute(
            select(LlmCallLog)
            .where(LlmCallLog.operation_id.in_(operation_ids))
            .order_by(LlmCallLog.created_at.desc(), LlmCallLog.id.desc())
        )
        out: dict[str, LlmCallLog] = {}
        for row in result.scalars().all():
            if row.operation_id and row.operation_id not in out:
                out[row.operation_id] = row
        return out

    async def summarize_for_brd(
        self,
        brd_id: int,
        *,
        user_id: int | None = None,
    ) -> dict:
        filters = [LlmCallLog.brd_id == brd_id]
        if user_id is not None:
            filters.append(LlmCallLog.user_id == user_id)

        totals = await self.db.execute(
            select(
                func.count(LlmCallLog.id),
                func.coalesce(func.sum(LlmCallLog.tokens_in), 0),
                func.coalesce(func.sum(LlmCallLog.tokens_out), 0),
                func.coalesce(func.sum(LlmCallLog.latency_ms), 0),
            ).where(*filters)
        )
        total_calls, tokens_in, tokens_out, latency_ms = totals.one()

        by_node_rows = await self.db.execute(
            select(
                LlmCallLog.node_name,
                func.count(LlmCallLog.id),
                func.coalesce(func.sum(LlmCallLog.tokens_in), 0),
                func.coalesce(func.sum(LlmCallLog.tokens_out), 0),
                func.coalesce(func.sum(LlmCallLog.latency_ms), 0),
            )
            .where(*filters)
            .group_by(LlmCallLog.node_name)
            .order_by(func.sum(LlmCallLog.tokens_in + LlmCallLog.tokens_out).desc())
        )

        by_node = []
        for node_name, calls, tin, tout, lat in by_node_rows.all():
            by_node.append(
                {
                    "node_name": node_name,
                    "calls": int(calls),
                    "tokens_in": int(tin),
                    "tokens_out": int(tout),
                    "latency_ms": int(lat),
                }
            )

        return {
            "total_calls": int(total_calls or 0),
            "total_tokens_in": int(tokens_in or 0),
            "total_tokens_out": int(tokens_out or 0),
            "total_latency_ms": int(latency_ms or 0),
            "by_node": by_node,
        }
