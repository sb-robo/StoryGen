from pathlib import Path

from app.parsers.base import DocumentParser
from app.parsers.models import ImageAsset, ParsedDocument, TableBlock

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx"}
SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class DoclingParser(DocumentParser):
    """DocumentParser implementation backed by IBM Docling."""

    def supports(self, mime_type: str | None, extension: str) -> bool:
        ext = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
        if ext in SUPPORTED_EXTENSIONS:
            return True
        if mime_type and mime_type.lower() in SUPPORTED_MIME_TYPES:
            return True
        return False

    def parse(self, file_path: Path, *, images_dir: Path | None = None) -> ParsedDocument:
        from docling.document_converter import DocumentConverter

        if not file_path.exists():
            raise FileNotFoundError(f"BRD file not found: {file_path}")

        converter = DocumentConverter()
        result = converter.convert(str(file_path))
        document = result.document

        text = document.export_to_markdown()
        tables = self._extract_tables(document)
        images = self._extract_images(document, images_dir) if images_dir is not None else []
        page_count = self._page_count(document)

        return ParsedDocument(
            text=text,
            tables=tables,
            images=images,
            page_count=page_count,
            metadata={
                "source": str(file_path),
                "parser": "docling",
                "table_count": len(tables),
                "image_count": len(images),
            },
        )

    def _extract_tables(self, document) -> list[TableBlock]:
        tables: list[TableBlock] = []
        for index, table in enumerate(getattr(document, "tables", []) or []):
            markdown = ""
            try:
                if hasattr(table, "export_to_markdown"):
                    markdown = table.export_to_markdown(doc=document)
                elif hasattr(table, "export_to_dataframe"):
                    markdown = table.export_to_dataframe(doc=document).to_markdown(index=False)
            except Exception:
                markdown = str(table)

            row_count = 0
            column_count = 0
            data = getattr(table, "data", None)
            if data is not None:
                row_count = getattr(data, "num_rows", 0) or 0
                column_count = getattr(data, "num_cols", 0) or 0

            tables.append(
                TableBlock(
                    index=index,
                    markdown=markdown or "",
                    row_count=row_count,
                    column_count=column_count,
                )
            )
        return tables

    def _extract_images(self, document, images_dir: Path) -> list[ImageAsset]:
        images_dir.mkdir(parents=True, exist_ok=True)
        assets: list[ImageAsset] = []

        for index, picture in enumerate(getattr(document, "pictures", []) or []):
            image = getattr(picture, "image", None)
            if image is None:
                continue

            pil_image = getattr(image, "pil_image", None)
            if pil_image is None:
                continue

            filename = f"img_{index + 1:03d}.png"
            absolute_path = images_dir / filename
            try:
                pil_image.save(absolute_path)
            except Exception:
                continue

            caption = None
            captions = getattr(picture, "captions", None)
            if captions:
                caption = str(captions[0])

            assets.append(
                ImageAsset(
                    index=index,
                    filename=filename,
                    relative_path=f"images/{filename}",
                    caption=caption,
                )
            )
        return assets

    def _page_count(self, document) -> int | None:
        pages = getattr(document, "pages", None)
        if pages is None:
            return None
        try:
            return len(pages)
        except TypeError:
            return None
