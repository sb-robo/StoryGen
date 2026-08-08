"""Unit tests for ExportService CSV formatting and validation gates."""

import csv
import io
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.db.models.brd_document import BrdDocument
from app.db.models.brd_feature import BrdFeature
from app.db.models.brd_story import BrdStory
from app.db.models.brd_sub_feature import BrdSubFeature
from app.db.models.brd_test_case import BrdTestCase
from app.repositories.story_repository import encode_acceptance_criteria
from app.services.export.service import CSV_COLUMNS, ExportRow, ExportService


def _service() -> ExportService:
    service = ExportService.__new__(ExportService)
    service.db = MagicMock()
    service.brd_repo = MagicMock()
    return service


def _brd(**overrides) -> BrdDocument:
    brd = MagicMock(spec=BrdDocument)
    brd.id = 1
    brd.name = "Payments BRD"
    for key, value in overrides.items():
        setattr(brd, key, value)
    return brd


def _feature(**overrides) -> BrdFeature:
    feature = MagicMock(spec=BrdFeature)
    feature.id = 10
    feature.title = "Auth"
    for key, value in overrides.items():
        setattr(feature, key, value)
    return feature


def _sub_feature(**overrides) -> BrdSubFeature:
    sub = MagicMock(spec=BrdSubFeature)
    sub.id = 20
    sub.title = "Login"
    for key, value in overrides.items():
        setattr(sub, key, value)
    return sub


def _story(**overrides) -> BrdStory:
    story = MagicMock(spec=BrdStory)
    story.id = 30
    story.title = "As a user I can log in"
    story.description = "Login with email/password"
    story.acceptance_criteria = encode_acceptance_criteria(
        ["Valid credentials succeed", "Invalid credentials fail"]
    )
    story.story_points = 5
    story.points_status = "approved"
    for key, value in overrides.items():
        setattr(story, key, value)
    return story


def _test_case(**overrides) -> BrdTestCase:
    tc = MagicMock(spec=BrdTestCase)
    tc.id = 40
    tc.title = "Happy path login"
    tc.steps = "1. Open login\n2. Submit valid credentials"
    tc.expected_result = "User lands on dashboard"
    tc.test_type = "happy_path"
    for key, value in overrides.items():
        setattr(tc, key, value)
    return tc


@pytest.mark.asyncio
async def test_export_csv_includes_story_and_test_case_columns():
    service = _service()
    service.brd_repo.get_by_id_for_user = AsyncMock(return_value=_brd())
    service._load_approved_rows = AsyncMock(
        return_value=[
            ExportRow(
                feature=_feature(),
                sub_feature=_sub_feature(),
                story=_story(),
                test_case=_test_case(),
            )
        ]
    )

    result = await service.export_brd(user_id=1, brd_id=1, format="csv")

    assert result.media_type.startswith("text/csv")
    assert result.filename == "payments-brd-export.csv"
    text = result.content.decode("utf-8-sig")
    lines = text.strip().split("\n")
    assert lines[0] == ",".join(CSV_COLUMNS)
    assert "As a user I can log in" in lines[1]
    assert "Happy path login" in lines[1]
    assert "Valid credentials succeed | Invalid credentials fail" in lines[1]
    assert ",5," in lines[1] or ",5\n" in text or lines[1].split(",")[9] == "5"


@pytest.mark.asyncio
async def test_export_csv_keeps_story_row_when_no_approved_test_cases():
    service = _service()
    service.brd_repo.get_by_id_for_user = AsyncMock(return_value=_brd())
    service._load_approved_rows = AsyncMock(
        return_value=[
            ExportRow(
                feature=_feature(),
                sub_feature=_sub_feature(),
                story=_story(),
                test_case=None,
            )
        ]
    )

    result = await service.export_brd(user_id=1, brd_id=1, format="csv")
    text = result.content.decode("utf-8-sig")
    data_row = text.strip().split("\n")[1]
    assert "As a user I can log in" in data_row
    # trailing empty test-case columns still present
    assert data_row.count(",") == len(CSV_COLUMNS) - 1


@pytest.mark.asyncio
async def test_export_rejects_missing_brd():
    service = _service()
    service.brd_repo.get_by_id_for_user = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        await service.export_brd(user_id=1, brd_id=99, format="csv")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_export_rejects_when_no_approved_stories():
    service = _service()
    service.brd_repo.get_by_id_for_user = AsyncMock(return_value=_brd())
    service._load_approved_rows = AsyncMock(return_value=[])

    with pytest.raises(HTTPException) as exc:
        await service.export_brd(user_id=1, brd_id=1, format="csv")
    assert exc.value.status_code == 409
    assert "No approved stories" in exc.value.detail


@pytest.mark.asyncio
async def test_export_jira_csv_one_row_per_story():
    service = _service()
    service.brd_repo.get_by_id_for_user = AsyncMock(return_value=_brd())
    service._load_approved_rows = AsyncMock(
        return_value=[
            ExportRow(
                feature=_feature(),
                sub_feature=_sub_feature(),
                story=_story(),
                test_case=_test_case(),
            ),
            ExportRow(
                feature=_feature(),
                sub_feature=_sub_feature(),
                story=_story(),
                test_case=_test_case(id=41, title="Invalid login"),
            ),
        ]
    )

    result = await service.export_brd(user_id=1, brd_id=1, format="jira")

    assert result.filename == "payments-brd-jira-import.csv"
    text = result.content.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    assert len(rows) == 1  # one Jira Story per approved story
    assert rows[0]["Summary"] == "As a user I can log in"
    assert rows[0]["Issue Type"] == "Story"
    assert "Happy path login" in rows[0]["Description"]
    assert "Invalid login" in rows[0]["Description"]
