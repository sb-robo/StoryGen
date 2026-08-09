"""Startup reclaim for orphaned in-process async operations."""

from __future__ import annotations

import logging

from app.db.session import async_session_local
from app.repositories.operation_repository import OperationRepository

logger = logging.getLogger(__name__)

ORPHAN_REASON = (
    "Server restarted while this job was still pending/running. "
    "Retry the operation if needed."
)


async def reclaim_orphaned_operations() -> int:
    """Fail stuck pending/running ops left behind by BackgroundTasks."""
    async with async_session_local() as session:
        repo = OperationRepository(session)
        count = await repo.fail_orphaned_in_flight(reason=ORPHAN_REASON)
        await session.commit()
        return count
