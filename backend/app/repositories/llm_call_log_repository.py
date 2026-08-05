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
