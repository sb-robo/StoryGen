from __future__ import annotations

import csv
import io
import re

from app.db.models.brd_document import BrdDocument
from app.repositories.story_repository import decode_acceptance_criteria
from app.schemas.pipeline_settings_schema import parse_pipeline_settings
from app.services.export.base import BrdExporter, ExportFile, ExportFormat, ExportRow
from app.services.export.helpers import slugify

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


def _jira_labels(*parts: str) -> str:
    labels: list[str] = []
    for part in parts:
        label = re.sub(r"[^a-zA-Z0-9]+", "-", part.strip().lower()).strip("-")
        if label:
            labels.append(label[:255])
    return " ".join(labels)


class JiraExporter(BrdExporter):
    @property
    def format(self) -> ExportFormat:
        return "jira"

    def export(self, brd: BrdDocument, rows: list[ExportRow]) -> ExportFile:
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

            writer.writerow(
                {
                    "Project Key": project_key,
                    "Summary": first.story.title,
                    "Issue Type": "Story",
                    "Description": "\n".join(description_parts).strip(),
                    "Story Points": first.story.story_points
                    if first.story.story_points is not None
                    else "",
                    "Labels": _jira_labels(first.feature.title, first.sub_feature.title),
                    "Epic Name": epic_name,
                    "External ID": f"story-{first.story.id}",
                }
            )

        safe_name = slugify(brd.name) or f"brd-{brd.id}"
        return ExportFile(
            content=("\ufeff" + buffer.getvalue()).encode("utf-8"),
            filename=f"{safe_name}-jira-import.csv",
            media_type="text/csv; charset=utf-8",
        )
