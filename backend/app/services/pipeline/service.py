from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.brd_document import BrdDocument
from app.db.models.brd_feature import BrdFeature
from app.db.models.brd_story import BrdStory, StoryReviewStatus
from app.db.models.brd_sub_feature import BrdSubFeature
from app.db.models.brd_test_case import BrdTestCase
from app.repositories.brd_repository import BrdRepository
from app.repositories.feature_repository import (
    decode_clarifying_answers,
    decode_clarifying_questions,
)
from app.schemas.pipeline_schema import (
    PipelineBlocker,
    PipelineSummaryResponse,
    PipelineTotals,
    StageSummary,
    StatusCounts,
    SuggestedStep,
)


class PipelineService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.brd_repo = BrdRepository(db)

    async def get_summary(self, user_id: int, brd_id: int) -> PipelineSummaryResponse:
        brd = await self.brd_repo.get_by_id_for_user(brd_id, user_id)
        if not brd:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="BRD not found",
            )

        features = await self._list_features(user_id, brd_id)
        feature_ids = [f.id for f in features]
        sub_features = await self._list_sub_features(user_id, feature_ids)
        sub_feature_ids = [sf.id for sf in sub_features]
        stories = await self._list_stories(user_id, sub_feature_ids)
        story_ids = [s.id for s in stories]
        test_cases = await self._list_test_cases(user_id, story_ids)

        stages = _compute_stages(brd, features, sub_features, stories, test_cases)
        blockers = _compute_blockers(features)
        totals = PipelineTotals(
            pending_review=_total_pending(stages),
            approved_stories=sum(
                1 for s in stories if s.status == StoryReviewStatus.APPROVED.value
            ),
        )
        suggested = _suggested_step(brd.status, stages, totals.pending_review)

        return PipelineSummaryResponse(
            brd_id=brd.id,
            brd_status=brd.status,
            stages=stages,
            blockers=blockers,
            suggested_step=suggested,
            totals=totals,
        )

    async def _list_features(self, user_id: int, brd_id: int) -> list[BrdFeature]:
        result = await self.db.execute(
            select(BrdFeature)
            .where(BrdFeature.user_id == user_id, BrdFeature.brd_id == brd_id)
            .order_by(BrdFeature.sort_order.asc(), BrdFeature.id.asc())
        )
        return list(result.scalars().all())

    async def _list_sub_features(
        self, user_id: int, feature_ids: list[int]
    ) -> list[BrdSubFeature]:
        if not feature_ids:
            return []
        result = await self.db.execute(
            select(BrdSubFeature)
            .where(
                BrdSubFeature.user_id == user_id,
                BrdSubFeature.feature_id.in_(feature_ids),
            )
            .order_by(BrdSubFeature.sort_order.asc(), BrdSubFeature.id.asc())
        )
        return list(result.scalars().all())

    async def _list_stories(
        self, user_id: int, sub_feature_ids: list[int]
    ) -> list[BrdStory]:
        if not sub_feature_ids:
            return []
        result = await self.db.execute(
            select(BrdStory)
            .where(
                BrdStory.user_id == user_id,
                BrdStory.sub_feature_id.in_(sub_feature_ids),
            )
            .order_by(BrdStory.sort_order.asc(), BrdStory.id.asc())
        )
        return list(result.scalars().all())

    async def _list_test_cases(
        self, user_id: int, story_ids: list[int]
    ) -> list[BrdTestCase]:
        if not story_ids:
            return []
        result = await self.db.execute(
            select(BrdTestCase)
            .where(
                BrdTestCase.user_id == user_id,
                BrdTestCase.story_id.in_(story_ids),
            )
            .order_by(BrdTestCase.sort_order.asc(), BrdTestCase.id.asc())
        )
        return list(result.scalars().all())


def _count_by_status(statuses: list[str]) -> StatusCounts:
    counts = StatusCounts(total=len(statuses))
    for value in statuses:
        if value == "approved":
            counts.approved += 1
        elif value == "pending_review":
            counts.pending_review += 1
        elif value == "rejected":
            counts.rejected += 1
        else:
            counts.other += 1
    return counts


def _stage_status(counts: StatusCounts) -> str:
    if counts.total == 0:
        return "not_started"
    if counts.pending_review > 0:
        return "needs_review"
    if counts.approved == counts.total:
        return "complete"
    return "in_progress"


def _compute_stages(
    brd: BrdDocument,
    features: list[BrdFeature],
    sub_features: list[BrdSubFeature],
    stories: list[BrdStory],
    test_cases: list[BrdTestCase],
) -> dict[str, StageSummary]:
    feature_counts = _count_by_status([f.status for f in features])
    sub_feature_counts = _count_by_status([sf.status for sf in sub_features])
    story_counts = _count_by_status([s.status for s in stories])

    points_items = [s for s in stories if s.story_points is not None or s.points_status]
    points_counts = StatusCounts(total=len(points_items))
    for story in points_items:
        if story.points_status == "approved":
            points_counts.approved += 1
        elif story.points_status == "pending_review":
            points_counts.pending_review += 1
        else:
            points_counts.other += 1

    test_counts = _count_by_status([tc.status for tc in test_cases])

    parse_complete = brd.status == "parsed"
    parse_failed = brd.status == "parse_failed"
    parse_status = (
        "failed"
        if parse_failed
        else "complete"
        if parse_complete
        else "in_progress"
        if brd.status == "parsing"
        else "not_started"
    )

    approved_features = feature_counts.approved
    approved_sub_features = sub_feature_counts.approved
    approved_stories = story_counts.approved

    if points_counts.total == 0:
        points_status = "locked" if approved_stories == 0 else "not_started"
    elif points_counts.pending_review > 0:
        points_status = "needs_review"
    elif points_counts.approved == points_counts.total:
        points_status = "complete"
    else:
        points_status = "in_progress"

    return {
        "parse": StageSummary(id="parse", status=parse_status, counts=None, pending=0),
        "features": StageSummary(
            id="features",
            status="locked" if not parse_complete else _stage_status(feature_counts),
            counts=feature_counts,
            pending=feature_counts.pending_review,
        ),
        "sub_features": StageSummary(
            id="sub_features",
            status=(
                "locked"
                if approved_features == 0
                else "not_started"
                if sub_feature_counts.total == 0
                else _stage_status(sub_feature_counts)
            ),
            counts=sub_feature_counts,
            pending=sub_feature_counts.pending_review,
            lock_reason=(
                "Approve at least one feature first" if approved_features == 0 else None
            ),
        ),
        "stories": StageSummary(
            id="stories",
            status=(
                "locked"
                if approved_sub_features == 0
                else "not_started"
                if story_counts.total == 0
                else _stage_status(story_counts)
            ),
            counts=story_counts,
            pending=story_counts.pending_review,
            lock_reason=(
                "Approve sub-features first" if approved_sub_features == 0 else None
            ),
        ),
        "points": StageSummary(
            id="points",
            status="locked" if approved_stories == 0 else points_status,
            counts=points_counts,
            pending=points_counts.pending_review,
            lock_reason="Approve stories first" if approved_stories == 0 else None,
        ),
        "tests": StageSummary(
            id="tests",
            status=(
                "locked"
                if approved_stories == 0
                else "not_started"
                if test_counts.total == 0
                else _stage_status(test_counts)
            ),
            counts=test_counts,
            pending=test_counts.pending_review,
            lock_reason="Approve stories first" if approved_stories == 0 else None,
        ),
        "export": StageSummary(
            id="export",
            status="locked" if approved_stories == 0 else "ready",
            counts=StatusCounts(total=approved_stories, approved=approved_stories),
            pending=0,
            lock_reason=(
                "Approve at least one story first" if approved_stories == 0 else None
            ),
        ),
    }


def _compute_blockers(features: list[BrdFeature]) -> list[PipelineBlocker]:
    blockers: list[PipelineBlocker] = []
    for feature in features:
        questions = decode_clarifying_questions(feature.clarifying_questions)
        answers = decode_clarifying_answers(feature.clarifying_answers)
        unanswered = max(0, len(questions) - len(answers))
        if unanswered > 0:
            blockers.append(
                PipelineBlocker(
                    feature_id=feature.id,
                    feature_title=feature.title,
                    unanswered=unanswered,
                )
            )
    return blockers


def _total_pending(stages: dict[str, StageSummary]) -> int:
    return sum(
        stages[key].pending
        for key in ("features", "sub_features", "stories", "points", "tests")
    )


def _suggested_step(
    brd_status: str, stages: dict[str, StageSummary], pending_review: int
) -> SuggestedStep:
    if brd_status == "parsing":
        return SuggestedStep(
            label="Parsing document…", action=None, stage_id="parse"
        )
    if brd_status == "parse_failed":
        return SuggestedStep(
            label="Parse failed — re-upload or reparse",
            action=None,
            stage_id="parse",
        )
    if brd_status != "parsed":
        return SuggestedStep(
            label="Waiting for parse to complete", action=None, stage_id="parse"
        )

    if pending_review > 0:
        stage_id = "features"
        for key in ("features", "sub_features", "stories", "points", "tests"):
            if stages[key].pending > 0:
                stage_id = key
                break
        return SuggestedStep(
            label=f"Review {pending_review} pending item{'s' if pending_review != 1 else ''}",
            action="review",
            stage_id=stage_id,
        )

    if (stages["features"].counts.total if stages["features"].counts else 0) == 0:
        return SuggestedStep(
            label="Extract features from BRD",
            action="extract_features",
            stage_id="features",
        )

    if (
        stages["sub_features"].status != "locked"
        and (stages["sub_features"].counts.total if stages["sub_features"].counts else 0)
        == 0
    ):
        return SuggestedStep(
            label="Generate sub-features for approved features",
            action="batch_sub_features",
            stage_id="sub_features",
        )

    if (
        stages["stories"].status != "locked"
        and (stages["stories"].counts.total if stages["stories"].counts else 0) == 0
    ):
        return SuggestedStep(
            label="Generate stories for approved sub-features",
            action="batch_stories",
            stage_id="stories",
        )

    if stages["points"].status == "not_started" and (
        stages["stories"].counts.approved if stages["stories"].counts else 0
    ) > 0:
        return SuggestedStep(
            label="Estimate story points for approved stories",
            action="batch_points",
            stage_id="points",
        )

    if (
        stages["tests"].status != "locked"
        and (stages["tests"].counts.total if stages["tests"].counts else 0) == 0
    ):
        return SuggestedStep(
            label="Generate test cases for approved stories",
            action="batch_tests",
            stage_id="tests",
        )

    if stages["export"].status != "locked":
        return SuggestedStep(
            label="Export approved stories as CSV",
            action="export_csv",
            stage_id="export",
        )

    return SuggestedStep(
        label="Pipeline complete — ready for export",
        action=None,
        stage_id="export",
    )
