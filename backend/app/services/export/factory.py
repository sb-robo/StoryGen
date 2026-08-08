from __future__ import annotations

from app.services.export.base import BrdExporter, ExportFormat
from app.services.export.csv_exporter import CsvExporter
from app.services.export.jira_exporter import JiraExporter
from app.services.export.markdown_exporter import MarkdownExporter


class ExportFormatFactory:
    """Factory that selects a BRD export formatter by format key."""

    def __init__(self, exporters: list[BrdExporter] | None = None):
        instances = exporters or [CsvExporter(), JiraExporter(), MarkdownExporter()]
        self._by_format: dict[ExportFormat, BrdExporter] = {
            exporter.format: exporter for exporter in instances
        }

    def get(self, format: ExportFormat) -> BrdExporter:
        try:
            return self._by_format[format]
        except KeyError as exc:
            raise ValueError(f"Unsupported export format: {format!r}") from exc

    def register(self, exporter: BrdExporter) -> None:
        self._by_format[exporter.format] = exporter

    def supported_formats(self) -> frozenset[ExportFormat]:
        return frozenset(self._by_format)
