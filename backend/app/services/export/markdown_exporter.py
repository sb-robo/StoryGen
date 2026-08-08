from __future__ import annotations

from app.db.models.brd_document import BrdDocument
from app.repositories.story_repository import decode_acceptance_criteria
from app.services.export.base import BrdExporter, ExportFile, ExportFormat, ExportRow
from app.services.export.helpers import slugify


def _as_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


class MarkdownExporter(BrdExporter):
    @property
    def format(self) -> ExportFormat:
        return "markdown"

    def export(self, brd: BrdDocument, rows: list[ExportRow]) -> ExportFile:
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

        safe_name = slugify(brd.name) or f"brd-{brd.id}"
        return ExportFile(
            content="\n".join(lines).rstrip().encode("utf-8") + b"\n",
            filename=f"{safe_name}-export.md",
            media_type="text/markdown; charset=utf-8",
        )
