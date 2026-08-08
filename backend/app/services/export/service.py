from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.brd_document import BrdDocument
from app.db.models.brd_feature import BrdFeature
from app.db.models.brd_story import BrdStory, StoryReviewStatus
from app.db.models.brd_sub_feature import BrdSubFeature
from app.db.models.brd_test_case import BrdTestCase, TestCaseStatus
from app.repositories.brd_repository import BrdRepository
from app.services.export.base import ExportFile, ExportFormat, ExportRow
from app.services.export.csv_exporter import CSV_COLUMNS
from app.services.export.factory import ExportFormatFactory
from app.utils.process_tracker import track, track_error

# Re-export for tests and callers
__all__ = ["CSV_COLUMNS", "ExportFile", "ExportFormat", "ExportRow", "ExportService"]


class ExportService:
    """Orchestrates loading approved rows and delegating to export format strategies."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        format_factory: ExportFormatFactory | None = None,
    ):
        self.db = db
        self.brd_repo = BrdRepository(db)
        self.format_factory = format_factory or ExportFormatFactory()

    async def export_brd(
        self,
        user_id: int,
        brd_id: int,
        *,
        format: ExportFormat = "csv",
    ) -> ExportFile:
        if format not in self.format_factory.supported_formats():
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=(
                    f"Export format '{format}' is not supported. "
                    "Use format=csv, format=jira, or format=markdown."
                ),
            )

        brd = await self._get_owned_brd(user_id, brd_id)
        rows = await self._load_approved_rows(user_id, brd_id)
        if not rows:
            track_error(
                "export blocked (no approved stories)",
                brd_id=brd_id,
                format=format,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No approved stories to export. Approve at least one story first.",
            )

        exporter = self.format_factory.get(format)
        result = exporter.export(brd, rows)
        track(
            f"exported {format}",
            brd_id=brd_id,
            rows=len(rows),
            filename=result.filename,
        )
        return result

    async def _get_owned_brd(self, user_id: int, brd_id: int) -> BrdDocument:
        brd = await self.brd_repo.get_by_id_for_user(brd_id, user_id)
        if not brd:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="BRD not found",
            )
        return brd

    async def _load_approved_rows(self, user_id: int, brd_id: int) -> list[ExportRow]:
        query = (
            select(BrdFeature, BrdSubFeature, BrdStory, BrdTestCase)
            .join(BrdSubFeature, BrdSubFeature.feature_id == BrdFeature.id)
            .join(BrdStory, BrdStory.sub_feature_id == BrdSubFeature.id)
            .outerjoin(
                BrdTestCase,
                and_(
                    BrdTestCase.story_id == BrdStory.id,
                    BrdTestCase.status == TestCaseStatus.APPROVED.value,
                    BrdTestCase.user_id == user_id,
                ),
            )
            .where(
                BrdFeature.brd_id == brd_id,
                BrdFeature.user_id == user_id,
                BrdStory.user_id == user_id,
                BrdStory.status == StoryReviewStatus.APPROVED.value,
            )
            .order_by(
                BrdFeature.sort_order.asc(),
                BrdFeature.id.asc(),
                BrdSubFeature.sort_order.asc(),
                BrdSubFeature.id.asc(),
                BrdStory.sort_order.asc(),
                BrdStory.id.asc(),
                BrdTestCase.sort_order.asc().nulls_last(),
                BrdTestCase.id.asc().nulls_last(),
            )
        )
        result = await self.db.execute(query)
        return [
            ExportRow(
                feature=feature,
                sub_feature=sub_feature,
                story=story,
                test_case=test_case,
            )
            for feature, sub_feature, story, test_case in result.all()
        ]
