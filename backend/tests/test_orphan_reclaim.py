from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.operation_repository import OperationRepository
from app.services.operations.startup import ORPHAN_REASON, reclaim_orphaned_operations


@pytest.mark.asyncio
async def test_fail_orphaned_in_flight_updates_pending_and_running():
    db = MagicMock()
    result = MagicMock()
    result.rowcount = 3
    db.execute = AsyncMock(return_value=result)
    db.flush = AsyncMock()

    repo = OperationRepository(db)
    count = await repo.fail_orphaned_in_flight(reason=ORPHAN_REASON)

    assert count == 3
    db.execute.assert_awaited_once()
    db.flush.assert_awaited_once()
    sql = str(db.execute.await_args.args[0]).lower()
    assert "pending" in sql or "running" in sql or "async_operations" in sql


@pytest.mark.asyncio
async def test_reclaim_orphaned_operations_commits(monkeypatch):
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    session.commit = AsyncMock()

    repo = MagicMock()
    repo.fail_orphaned_in_flight = AsyncMock(return_value=2)

    monkeypatch.setattr(
        "app.services.operations.startup.async_session_local",
        MagicMock(return_value=session),
    )
    monkeypatch.setattr(
        "app.services.operations.startup.OperationRepository",
        lambda db: repo,
    )

    count = await reclaim_orphaned_operations()
    assert count == 2
    repo.fail_orphaned_in_flight.assert_awaited_once_with(reason=ORPHAN_REASON)
    session.commit.assert_awaited_once()
