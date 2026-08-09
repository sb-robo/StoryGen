"""Service-level tests for clarifying-question approve gate and reopen."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.repositories.feature_repository import (
    encode_clarifying_answers,
    encode_clarifying_questions,
)
from app.services.ai.feature_service import FeatureService


NOW = datetime.now(timezone.utc)


def _feature(**overrides):
    fields = dict(
        id=1,
        brd_id=10,
        user_id=1,
        status="pending_review",
        clarifying_questions=encode_clarifying_questions(["Q1?", "Q2?"]),
        clarifying_answers=encode_clarifying_answers([]),
        reviewed_by=None,
        reviewed_at=None,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


@pytest.fixture
def service():
    svc = FeatureService(db=MagicMock())
    svc._get_owned_feature = AsyncMock()
    svc.repo = MagicMock()
    svc.repo.update = AsyncMock(side_effect=lambda feature: feature)
    svc._index_approved_feature = AsyncMock()
    return svc


@pytest.mark.asyncio
async def test_approve_blocks_when_clarifying_unanswered(service):
    service._get_owned_feature.return_value = _feature()

    with pytest.raises(HTTPException) as exc:
        await service.approve_feature(1, 1)

    assert exc.value.status_code == 409
    assert "clarifying" in str(exc.value.detail).lower()
    service.repo.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_approve_allows_when_all_clarifying_answered(service):
    service._get_owned_feature.return_value = _feature(
        clarifying_answers=encode_clarifying_answers(
            [
                {"question": "Q1?", "answer": "A1"},
                {"question": "Q2?", "answer": "A2"},
            ]
        )
    )

    result = await service.approve_feature(1, 1)

    assert result.status == "approved"
    service.repo.update.assert_awaited_once()
    service._index_approved_feature.assert_awaited_once()


@pytest.mark.asyncio
async def test_reopen_rejected_feature(service):
    service._get_owned_feature.return_value = _feature(
        status="rejected",
        reviewed_by=1,
        reviewed_at=NOW,
    )

    result = await service.reopen_feature(1, 1)

    assert result.status == "pending_review"
    assert result.reviewed_by is None
    assert result.reviewed_at is None
