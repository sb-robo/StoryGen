from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.db.models.brd_document import BrdDocument
from app.db.models.brd_feature import BrdFeature
from app.db.models.brd_story import BrdStory
from app.db.models.brd_sub_feature import BrdSubFeature
from app.db.models.brd_test_case import BrdTestCase

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


class BrdExporter:
    """
    Base class for export format handlers.

    Subclasses set `format` and implement `export`.
    """

    format: ExportFormat

    def export(self, brd: BrdDocument, rows: list[ExportRow]) -> ExportFile:
        raise NotImplementedError
