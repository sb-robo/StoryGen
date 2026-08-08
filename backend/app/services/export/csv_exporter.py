from __future__ import annotations

import csv
import io

from app.db.models.brd_document import BrdDocument
from app.repositories.story_repository import decode_acceptance_criteria
from app.services.export.base import BrdExporter, ExportFile, ExportFormat, ExportRow
from app.services.export.helpers import slugify

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


class CsvExporter(BrdExporter):
    @property
    def format(self) -> ExportFormat:
        return "csv"

    def export(self, brd: BrdDocument, rows: list[ExportRow]) -> ExportFile:
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
        safe_name = slugify(brd.name) or f"brd-{brd.id}"
        return ExportFile(
            content=("\ufeff" + buffer.getvalue()).encode("utf-8"),
            filename=f"{safe_name}-export.csv",
            media_type="text/csv; charset=utf-8",
        )
