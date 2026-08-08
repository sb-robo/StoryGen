import csv
import io
import re
from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.brd_document import BrdDocument
from app.db.models.brd_feature import BrdFeature
from app.db.models.brd_story import BrdStory, StoryReviewStatus
from app.db.models.brd_sub_feature import BrdSubFeature
from app.db.models.brd_test_case import BrdTestCase, TestCaseStatus
from app.repositories.brd_repository import BrdRepository
from app.repositories.story_repository import decode_acceptance_criteria
from app.schemas.pipeline_settings_schema import parse_pipeline_settings

ExportFormat = Literal["csv", "jira", "markdown"]


@dataclass(frozen=True)
class ExportFile:
    content: bytes
    filename: str
    media_type: str


@dataclass(frozen=True)
class ExportRow:
    feature: BrdFeature
    sub_feature: BrdSubFeature
    story: BrdStory
    test_case: BrdTestCase | None


CSV_COLUMNS = [
    "brd_name",
    "feature_id",
    "feature_title",
    "sub_feature_id",
    "sub_feature_title",
    "story_id",
    "story_title",
    "story_description",
    "acceptance_criteria",
    "story_points",
    "points_status",
    "test_case_id",
    "test_case_title",
    "test_steps",
    "expected_result",
    "test_type",
]

# Jira External System Import–style CSV (upload via Jira CSV importer).
JIRA_COLUMNS = [
    "Project Key",
    "Summary",
    "Issue Type",
    "Description",
    "Story Points",
    "Labels",
    "Epic Name",
    "External ID",
]


class ExportService:
    """Deterministic export of approved stories (+ approved test cases) for a BRD."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.brd_repo = BrdRepository(db)

    async def export_brd(
        self,
        user_id: int,
        brd_id: int,
        *,
        format: ExportFormat = "csv",
    ) -> ExportFile:
        if format not in {"csv", "jira", "markdown"}:
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
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No approved stories to export. Approve at least one story first.",
            )

        safe_name = _slugify(brd.name) or f"brd-{brd.id}"
        if format == "jira":
            return ExportFile(
                content=self._format_jira_csv(brd, rows),
                filename=f"{safe_name}-jira-import.csv",
                media_type="text/csv; charset=utf-8",
            )
        if format == "markdown":
            return ExportFile(
                content=self._format_markdown(brd, rows),
                filename=f"{safe_name}-export.md",
                media_type="text/markdown; charset=utf-8",
            )

        return ExportFile(
            content=self._format_csv(brd, rows),
            filename=f"{safe_name}-export.csv",
            media_type="text/csv; charset=utf-8",
        )

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

    def _format_csv(self, brd: BrdDocument, rows: list[ExportRow]) -> bytes:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            criteria = decode_acceptance_criteria(row.story.acceptance_criteria)
            tc = row.test_case
            writer.writerow(
                {
                    "brd_name": brd.name,
                    "feature_id": row.feature.id,
                    "feature_title": row.feature.title,
                    "sub_feature_id": row.sub_feature.id,
                    "sub_feature_title": row.sub_feature.title,
                    "story_id": row.story.id,
                    "story_title": row.story.title,
                    "story_description": row.story.description,
                    "acceptance_criteria": " | ".join(criteria),
                    "story_points": row.story.story_points
                    if row.story.story_points is not None
                    else "",
                    "points_status": row.story.points_status or "",
                    "test_case_id": tc.id if tc else "",
                    "test_case_title": tc.title if tc else "",
                    "test_steps": tc.steps if tc else "",
                    "expected_result": tc.expected_result if tc else "",
                    "test_type": tc.test_type if tc else "",
                }
            )
        return ("\ufeff" + buffer.getvalue()).encode("utf-8")

    def _format_jira_csv(self, brd: BrdDocument, rows: list[ExportRow]) -> bytes:
        """One Jira Story row per approved story; test cases folded into Description."""
        by_story: dict[int, list[ExportRow]] = {}
        for row in rows:
            by_story.setdefault(row.story.id, []).append(row)

        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=JIRA_COLUMNS, lineterminator="\n")
        writer.writeheader()

        for story_rows in by_story.values():
            first = story_rows[0]
            criteria = decode_acceptance_criteria(first.story.acceptance_criteria)
            description_parts = [
                first.story.description.strip(),
                "",
                f"*BRD:* {brd.name}",
                f"*Feature:* {first.feature.title}",
                f"*Sub-feature:* {first.sub_feature.title}",
            ]
            if criteria:
                description_parts.extend(["", "*Acceptance criteria:*"])
                description_parts.extend(f"* {item}" for item in criteria)

            test_cases = [r.test_case for r in story_rows if r.test_case is not None]
            if test_cases:
                description_parts.extend(["", "*Test cases:*"])
                for tc in test_cases:
                    description_parts.extend(
                        [
                            "",
                            f"h3. {tc.title} ({tc.test_type})",
                            f"*Steps:* {tc.steps}",
                            f"*Expected:* {tc.expected_result}",
                        ]
                    )

            settings = parse_pipeline_settings(getattr(brd, "pipeline_settings", None))
            project_key = settings.export_project_key or ""
            epic_prefix = (settings.export_epic_prefix or "").strip()
            epic_name = (
                f"{epic_prefix} {first.feature.title}".strip()
                if epic_prefix
                else first.feature.title
            )

            labels = _jira_labels(first.feature.title, first.sub_feature.title)
            writer.writerow(
                {
                    "Project Key": project_key,
                    "Summary": first.story.title,
                    "Issue Type": "Story",
                    "Description": "\n".join(description_parts).strip(),
                    "Story Points": first.story.story_points
                    if first.story.story_points is not None
                    else "",
                    "Labels": labels,
                    "Epic Name": epic_name,
                    "External ID": f"story-{first.story.id}",
                }
            )

        return ("\ufeff" + buffer.getvalue()).encode("utf-8")

    def _format_markdown(self, brd: BrdDocument, rows: list[ExportRow]) -> bytes:
        """Stakeholder-friendly Markdown pack of approved stories (+ tests)."""
        by_feature: dict[int, dict] = {}
        for row in rows:
            feature_bucket = by_feature.setdefault(
                row.feature.id,
                {"feature": row.feature, "sub_features": {}},
            )
            sf_bucket = feature_bucket["sub_features"].setdefault(
                row.sub_feature.id,
                {"sub_feature": row.sub_feature, "stories": {}},
            )
            story_bucket = sf_bucket["stories"].setdefault(
                row.story.id,
                {"story": row.story, "test_cases": []},
            )
            if row.test_case is not None:
                story_bucket["test_cases"].append(row.test_case)

        lines: list[str] = [
            f"# {brd.name}",
            "",
            "Approved delivery pack exported from StoryGen.",
            "",
        ]

        for feature_bucket in by_feature.values():
            feature = feature_bucket["feature"]
            lines.extend([f"## Feature: {feature.title}", ""])
            feature_desc = _as_text(feature.description)
            if feature_desc:
                lines.extend([feature_desc, ""])

            for sf_bucket in feature_bucket["sub_features"].values():
                sub = sf_bucket["sub_feature"]
                lines.extend([f"### Sub-feature: {sub.title}", ""])
                sub_desc = _as_text(sub.description)
                if sub_desc:
                    lines.extend([sub_desc, ""])

                for story_bucket in sf_bucket["stories"].values():
                    story = story_bucket["story"]
                    lines.extend([f"#### Story: {story.title}", ""])
                    story_desc = _as_text(story.description)
                    if story_desc:
                        lines.extend([story_desc, ""])
                    if story.story_points is not None:
                        lines.append(f"**Story points:** {story.story_points}")
                        lines.append("")

                    criteria = decode_acceptance_criteria(story.acceptance_criteria)
                    if criteria:
                        lines.append("**Acceptance criteria**")
                        lines.append("")
                        lines.extend(f"- {item}" for item in criteria)
                        lines.append("")

                    test_cases = story_bucket["test_cases"]
                    if test_cases:
                        lines.append("**Test cases**")
                        lines.append("")
                        for tc in test_cases:
                            lines.append(f"- **{tc.title}** ({tc.test_type})")
                            lines.append(f"  - Steps: {_as_text(tc.steps)}")
                            lines.append(f"  - Expected: {_as_text(tc.expected_result)}")
                        lines.append("")

        return "\n".join(lines).rstrip().encode("utf-8") + b"\n"


def _as_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:80]


def _jira_labels(*parts: str) -> str:
    labels: list[str] = []
    for part in parts:
        label = re.sub(r"[^a-zA-Z0-9]+", "-", part.strip().lower()).strip("-")
        if label:
            labels.append(label[:255])
    return " ".join(labels)
