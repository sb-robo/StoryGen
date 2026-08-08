from __future__ import annotations

import re

from app.services.export.base import BrdExporter, ExportFormat, ExportFile


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:80]
