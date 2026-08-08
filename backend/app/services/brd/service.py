import asyncio
import zipfile
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.core.config import settings
from app.db.models.async_operation import AsyncOperation, OperationStatus, OperationType
from app.db.models.brd_document import BrdDocument, BrdStatus
from app.repositories.brd_repository import BrdRepository
from app.repositories.llm_call_log_repository import LlmCallLogRepository
from app.repositories.operation_repository import OperationRepository
from app.schemas.brd_schema import (
    BrdContentResponse,
    BrdDeleteResponse,
    BrdDetailResponse,
    BrdImageListResponse,
    BrdImageResponse,
    BrdListResponse,
    BrdResponse,
)
from app.schemas.llm_usage_schema import (
    LlmCallLogResponse,
    LlmNodeUsage,
    LlmUsageSummaryResponse,
)
from app.schemas.operation_schema import OperationResponse
from app.schemas.pipeline_settings_schema import (
    BrdPipelineSettings,
    parse_pipeline_settings,
)
from app.services.brd.chunk_service import BrdChunkService
from app.services.brd.parser_service import BrdParserService
from app.services.brd.storage_service import BrdStorageService
from app.utils.process_tracker import track, track_error, track_queued, track_run, track_saved

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx"}
ALLOWED_FORMAT_LABEL = "PDF (.pdf), Word (.docx), Excel (.xlsx)"
EXTENSION_MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
# Browsers sometimes send a generic type; accept those when the extension is valid.
ALLOWED_MIME_TYPES = set(EXTENSION_MIME.values()) | {
    "application/octet-stream",
    "binary/octet-stream",
}
PREVIEW_CHARS = 280
PDF_MAGIC = b"%PDF-"


def _sniff_content_sync(path: Path, extension: str) -> bool:
    """
    Verify the file's actual bytes match the claimed extension.

    Cheap, dependency-free defense against a renamed file (e.g. an .exe
    renamed to .pdf) rather than relying purely on extension/MIME headers.
    """
    if extension == ".pdf":
        with open(path, "rb") as handle:
            return handle.read(len(PDF_MAGIC)) == PDF_MAGIC

    if extension in {".docx", ".xlsx"}:
        # DOCX/XLSX are OOXML — zip containers with a well-known internal layout.
        if not zipfile.is_zipfile(path):
            return False
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
        marker = "word/document.xml" if extension == ".docx" else "xl/workbook.xml"
        return marker in names

    return True


class BrdService:
    def __init__(
        self,
        db: AsyncSession,
        storage: BrdStorageService | None = None,
        parser_service: BrdParserService | None = None,
        chunk_service: BrdChunkService | None = None,
    ):
        self.db = db
        self.repo = BrdRepository(db)
        self.operation_repo = OperationRepository(db)
        self.llm_log_repo = LlmCallLogRepository(db)
        self.storage = storage or BrdStorageService()
        self.parser_service = parser_service or BrdParserService(storage=self.storage)
        self.chunk_service = chunk_service or BrdChunkService(db)

    def _normalize_extension(self, filename: str) -> str:
        extension = Path(filename).suffix.lower()
        if not extension:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "File has no extension. "
                    f"StoryGen only supports BRD uploads as {ALLOWED_FORMAT_LABEL}."
                ),
            )
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unsupported BRD format '{extension}'. "
                    f"Supported formats: {ALLOWED_FORMAT_LABEL}."
                ),
            )
        return extension

    def _validate_mime_type(self, mime_type: str | None, extension: str) -> str:
        resolved = (mime_type or "").strip().lower() or EXTENSION_MIME[extension]
        # Some clients append charset, e.g. application/pdf; charset=utf-8
        resolved = resolved.split(";")[0].strip()
        expected = EXTENSION_MIME[extension]
        if resolved not in ALLOWED_MIME_TYPES and resolved != expected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"MIME type '{resolved}' does not match supported BRD formats. "
                    f"Supported formats: {ALLOWED_FORMAT_LABEL}."
                ),
            )
        return resolved if resolved in EXTENSION_MIME.values() else expected

    async def _ensure_unique_upload(
        self, user_id: int, *, name: str, original_filename: str
    ) -> None:
        existing_by_name = await self.repo.find_by_name_for_user(user_id, name)
        if existing_by_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"A BRD named '{existing_by_name.name}' already exists "
                    f"(id={existing_by_name.id}). Choose a different name."
                ),
            )

        existing_by_file = await self.repo.find_by_original_filename_for_user(
            user_id, original_filename
        )
        if existing_by_file:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"File '{existing_by_file.original_filename}' was already uploaded "
                    f"as BRD '{existing_by_file.name}' (id={existing_by_file.id})."
                ),
            )

    async def _get_owned_brd(
        self, user_id: int, brd_id: int, *, include_deleted: bool = False
    ) -> BrdDocument:
        brd = await self.repo.get_by_id_for_user(
            brd_id, user_id, include_deleted=include_deleted
        )
        if not brd:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="BRD not found",
            )
        return brd

    def _operation_response(self, operation: AsyncOperation) -> OperationResponse:
        return OperationResponse(
            operation_id=operation.id,
            operation_type=operation.operation_type,
            status=operation.status,
            resource_type=operation.resource_type,
            resource_id=operation.resource_id,
            error_message=operation.error_message,
            created_at=operation.created_at,
            updated_at=operation.updated_at,
            completed_at=operation.completed_at,
        )

    async def upload(
        self,
        user_id: int,
        file: UploadFile,
        *,
        name: str,
        pipeline_settings: BrdPipelineSettings | None = None,
    ) -> OperationResponse:
        """
        Stream the file to disk and return an operation_id immediately.

        Schedule `run_brd_parse_task(operation_id)` from the router afterward.
        """
        brd_name = name.strip()
        if not brd_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="BRD name is required",
            )
        if len(brd_name) > 255:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="BRD name must be at most 255 characters",
            )

        if not file.filename or not file.filename.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required",
            )

        original_filename = Path(file.filename).name.strip()
        if not original_filename or original_filename in {".", ".."}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename",
            )

        extension = self._normalize_extension(original_filename)
        mime_type = self._validate_mime_type(file.content_type, extension)
        await self._ensure_unique_upload(
            user_id, name=brd_name, original_filename=original_filename
        )

        stored_filename = f"original{extension}"

        operation = await self.operation_repo.create(
            AsyncOperation(
                user_id=user_id,
                operation_type=OperationType.BRD_UPLOAD.value,
                status=OperationStatus.PENDING.value,
                resource_type="brd",
            )
        )
        # Commit the operation row on its own so it survives a rollback below
        # (the unique-name insert failure rolls back the whole transaction).
        await self.db.commit()

        settings = parse_pipeline_settings(pipeline_settings)
        brd = BrdDocument(
            user_id=user_id,
            name=brd_name,
            original_filename=original_filename,
            stored_filename=stored_filename,
            mime_type=mime_type,
            file_extension=extension,
            file_size_bytes=0,
            storage_path="",
            original_path="",
            status=BrdStatus.UPLOADED.value,
            pipeline_settings=settings.model_dump(mode="json"),
        )
        try:
            brd = await self.repo.create(brd)
        except IntegrityError as exc:
            # DB-level unique index is the source of truth for the race window
            # between the pre-check above and this insert.
            await self.db.rollback()
            await self.operation_repo.mark_failed(operation, "Duplicate BRD name")
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A BRD named '{brd_name}' already exists. Choose a different name.",
            ) from exc

        brd_dir = await self.storage.ensure_brd_dir(user_id, brd.id)
        brd.storage_path = str(brd_dir)

        try:
            original_path, size = await self.storage.save_upload_stream(
                user_id,
                brd.id,
                stored_filename,
                file,
                max_bytes=settings.max_upload_size_bytes,
            )
        except ValueError as exc:
            await self.storage.delete_brd_dir(user_id, brd.id)
            await self.repo.delete(brd)
            await self.operation_repo.mark_failed(operation, str(exc))
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            await self.storage.delete_brd_dir(user_id, brd.id)
            await self.repo.delete(brd)
            await self.operation_repo.mark_failed(operation, str(exc))
            await self.db.commit()
            raise

        if size == 0:
            await self.storage.delete_brd_dir(user_id, brd.id)
            await self.repo.delete(brd)
            await self.operation_repo.mark_failed(operation, "Uploaded file is empty")
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty",
            )

        if not await asyncio.to_thread(_sniff_content_sync, original_path, extension):
            await self.storage.delete_brd_dir(user_id, brd.id)
            await self.repo.delete(brd)
            error = (
                f"File content does not look like a valid {extension} file. "
                "The extension may have been changed on a different file type."
            )
            await self.operation_repo.mark_failed(operation, error)
            await self.db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

        brd.original_path = str(original_path)
        brd.file_size_bytes = size
        brd.status = BrdStatus.PARSING.value
        brd.error_message = None
        brd = await self.repo.update(brd)

        operation.resource_id = brd.id
        operation = await self.operation_repo.mark_running(operation)

        # Commit before the response so the background task can see both rows.
        await self.db.commit()
        track_queued(
            "brd_upload",
            brd_id=brd.id,
            name=brd_name,
            operation_id=operation.id,
        )
        return self._operation_response(operation)

    async def enqueue_reparse(self, user_id: int, brd_id: int) -> OperationResponse:
        """Create a reparse operation; caller schedules background parse by operation_id."""
        brd = await self._get_owned_brd(user_id, brd_id)
        if brd.status == BrdStatus.PARSING.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This BRD is already being parsed. Wait for it to finish.",
            )
        original = await self.storage.resolve_original_path(brd.original_path)
        if original is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Original BRD file is missing from storage",
            )

        operation = await self.operation_repo.create(
            AsyncOperation(
                user_id=user_id,
                operation_type=OperationType.BRD_REPARSE.value,
                status=OperationStatus.RUNNING.value,
                resource_type="brd",
                resource_id=brd.id,
            )
        )

        brd.status = BrdStatus.PARSING.value
        brd.error_message = None
        await self.repo.update(brd)
        await self.db.commit()
        track_queued(
            "brd_reparse",
            brd_id=brd.id,
            operation_id=operation.id,
        )
        return self._operation_response(operation)

    async def complete_parse(self, brd_id: int) -> BrdDocument | None:
        """Used by the background worker (no ownership check — internal)."""
        brd = await self.repo.get_by_id(brd_id)
        if not brd:
            return None

        try:
            return await self._run_parse(brd)
        except Exception as exc:
            track_error("parse failed", exc=exc, brd_id=brd_id)
            brd.status = BrdStatus.PARSE_FAILED.value
            brd.error_message = str(exc)
            return await self.repo.update(brd)

    async def _run_parse(self, brd: BrdDocument) -> BrdDocument:
        track_run("parse document", brd_id=brd.id, name=brd.name)
        brd_dir = Path(brd.storage_path)
        parsed = await self.parser_service.parse_and_persist(
            user_id=brd.user_id,
            brd_id=brd.id,
            original_path=Path(brd.original_path),
            mime_type=brd.mime_type,
            extension=brd.file_extension,
        )
        brd.parsed_text_path = str(brd_dir / "parsed.md")
        brd.images_path = str(brd_dir / "images")
        brd.page_count = parsed.page_count
        brd.table_count = len(parsed.tables)
        brd.image_count = len(parsed.images)
        brd.status = BrdStatus.PARSED.value
        brd.error_message = None
        updated = await self.repo.update(brd)
        chunk_count = await self.chunk_service.index_parsed_markdown(
            updated,
            parsed.text,
            parser_tables=parsed.tables,
        )
        track_saved(
            "parsed BRD",
            brd_id=updated.id,
            pages=parsed.page_count,
            chunks=chunk_count,
        )
        return updated

    async def list_brds(
        self,
        user_id: int,
        *,
        page: int = 1,
        page_size: int = 20,
        status_filter: str | None = None,
        search: str | None = None,
        file_extension: str | None = None,
        has_images: bool | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        trashed: bool = False,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> BrdListResponse:
        if created_from and created_to and created_from > created_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="created_from must be earlier than or equal to created_to",
            )

        offset = (page - 1) * page_size
        filters = {
            "status": status_filter,
            "search": search,
            "file_extension": file_extension,
            "has_images": has_images,
            "created_from": created_from,
            "created_to": created_to,
            "trashed": trashed,
        }
        items = await self.repo.list_for_user(
            user_id,
            offset=offset,
            limit=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            **filters,
        )
        total = await self.repo.count_for_user(user_id, **filters)
        summaries = [await self._to_summary(item) for item in items]
        return BrdListResponse.build(
            items=summaries,
            total=total,
            page=page,
            page_size=page_size,
            status=status_filter,
            search=search,
            file_extension=file_extension,
            has_images=has_images,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def get_brd(
        self, user_id: int, brd_id: int, *, include_text: bool = True
    ) -> BrdDetailResponse:
        brd = await self._get_owned_brd(user_id, brd_id)
        return await self._to_detail(brd, include_text=include_text)

    async def get_content(self, user_id: int, brd_id: int) -> BrdContentResponse:
        brd = await self._get_owned_brd(user_id, brd_id)
        text = await self.storage.read_parsed_markdown(brd.parsed_text_path)
        if text is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parsed content is not available for this BRD",
            )
        return BrdContentResponse(
            brd_id=brd.id,
            status=brd.status,
            original_filename=brd.original_filename,
            char_count=len(text),
            word_count=len(text.split()),
            content=text,
        )

    async def list_images(self, user_id: int, brd_id: int) -> BrdImageListResponse:
        brd = await self._get_owned_brd(user_id, brd_id)
        images = await self._image_responses(brd)
        return BrdImageListResponse(brd_id=brd.id, total=len(images), items=images)

    async def get_image_path(self, user_id: int, brd_id: int, filename: str) -> Path:
        await self._get_owned_brd(user_id, brd_id)
        path = await self.storage.resolve_image_path(user_id, brd_id, filename)
        if path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found",
            )
        return path

    async def get_original_path(
        self, user_id: int, brd_id: int
    ) -> tuple[Path, str, str | None]:
        brd = await self._get_owned_brd(user_id, brd_id)
        path = await self.storage.resolve_original_path(brd.original_path)
        if path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Original file not found",
            )
        return path, brd.original_filename, brd.mime_type

    async def update_pipeline_settings(
        self, user_id: int, brd_id: int, settings: BrdPipelineSettings
    ) -> BrdDetailResponse:
        brd = await self._get_owned_brd(user_id, brd_id)
        previous = parse_pipeline_settings(brd.pipeline_settings)
        brd.pipeline_settings = settings.model_dump(mode="json")
        brd = await self.repo.update(brd)

        if (
            brd.status == BrdStatus.PARSED.value
            and previous.chunk_level != settings.chunk_level
        ):
            text = await self.storage.read_parsed_markdown(brd.parsed_text_path)
            if text:
                await self.chunk_service.index_parsed_markdown(
                    brd,
                    text,
                    chunk_strategy=settings.chunk_level,
                )

        return await self._to_detail(brd, include_text=False)

    async def get_llm_usage(
        self, user_id: int, brd_id: int, *, recent_limit: int = 25
    ) -> LlmUsageSummaryResponse:
        await self._get_owned_brd(user_id, brd_id)
        summary = await self.llm_log_repo.summarize_for_brd(brd_id, user_id=user_id)
        recent = await self.llm_log_repo.list_for_brd(
            brd_id, user_id=user_id, limit=recent_limit
        )
        return LlmUsageSummaryResponse(
            brd_id=brd_id,
            total_calls=summary["total_calls"],
            total_tokens_in=summary["total_tokens_in"],
            total_tokens_out=summary["total_tokens_out"],
            total_latency_ms=summary["total_latency_ms"],
            by_node=[LlmNodeUsage(**row) for row in summary["by_node"]],
            recent_calls=[
                LlmCallLogResponse(
                    id=row.id,
                    operation_id=row.operation_id,
                    brd_id=row.brd_id,
                    node_name=row.node_name,
                    iteration=row.iteration,
                    model=row.model,
                    tokens_in=row.tokens_in,
                    tokens_out=row.tokens_out,
                    latency_ms=row.latency_ms,
                    created_at=row.created_at,
                )
                for row in recent
            ],
        )

    async def list_chunks(self, user_id: int, brd_id: int):
        brd = await self._get_owned_brd(user_id, brd_id)
        if brd.status != BrdStatus.PARSED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="BRD must be parsed before chunks are available",
            )
        return await self.chunk_service.list_chunks(brd)

    async def rename_brd(
        self, user_id: int, brd_id: int, new_name: str
    ) -> BrdDetailResponse:
        brd = await self._get_owned_brd(user_id, brd_id)
        conflict = await self.repo.find_by_name_for_user(
            user_id, new_name, exclude_id=brd_id
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"A BRD named '{conflict.name}' already exists "
                    f"(id={conflict.id}). Choose a different name."
                ),
            )

        brd.name = new_name
        try:
            brd = await self.repo.update(brd)
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A BRD named '{new_name}' already exists. Choose a different name.",
            ) from exc
        return await self._to_detail(brd, include_text=False)

    async def delete_brd(self, user_id: int, brd_id: int) -> BrdDeleteResponse:
        """Soft-delete: hide from lists but keep files/DB row for restore."""
        brd = await self._get_owned_brd(user_id, brd_id)
        await self.repo.soft_delete(brd)
        return BrdDeleteResponse(id=brd_id, message="BRD moved to trash")

    async def restore_brd(self, user_id: int, brd_id: int) -> BrdDetailResponse:
        brd = await self._get_owned_brd(user_id, brd_id, include_deleted=True)
        if brd.deleted_at is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="BRD is not in trash.",
            )
        conflict = await self.repo.find_by_name_for_user(user_id, brd.name, exclude_id=brd.id)
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Cannot restore: an active BRD named '{brd.name}' already exists. "
                    "Rename or delete it first."
                ),
            )
        brd = await self.repo.restore(brd)
        return await self._to_detail(brd, include_text=False)

    async def purge_brd(self, user_id: int, brd_id: int) -> BrdDeleteResponse:
        """Permanently delete a trashed BRD (files + row)."""
        brd = await self._get_owned_brd(user_id, brd_id, include_deleted=True)
        if brd.deleted_at is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Move the BRD to trash before permanently deleting it.",
            )
        await self.storage.delete_brd_dir(user_id, brd_id)
        await self.repo.delete(brd)
        await self.operation_repo.delete_for_resource(user_id, "brd", brd_id)
        return BrdDeleteResponse(id=brd_id, message="BRD permanently deleted")

    async def _preview(self, brd: BrdDocument) -> str | None:
        text = await self.storage.read_parsed_markdown(brd.parsed_text_path)
        if not text:
            return None
        collapsed = " ".join(text.split())
        if len(collapsed) <= PREVIEW_CHARS:
            return collapsed
        return f"{collapsed[:PREVIEW_CHARS].rstrip()}…"

    async def _image_responses(self, brd: BrdDocument) -> list[BrdImageResponse]:
        items = await self.storage.list_images(brd.user_id, brd.id)
        return [
            BrdImageResponse(
                filename=item["filename"],
                size_bytes=item["size_bytes"],
                content_type=item["content_type"],
                url=f"/api/v1/brds/{brd.id}/images/{item['filename']}",
            )
            for item in items
        ]

    async def _to_summary(self, brd: BrdDocument) -> BrdResponse:
        chunk_count = (
            await self.chunk_service.chunk_count(brd.id)
            if brd.status == BrdStatus.PARSED.value
            else 0
        )
        return BrdResponse(
            id=brd.id,
            user_id=brd.user_id,
            name=brd.name,
            original_filename=brd.original_filename,
            mime_type=brd.mime_type,
            file_extension=brd.file_extension,
            file_size_bytes=brd.file_size_bytes,
            status=brd.status,
            error_message=brd.error_message,
            page_count=brd.page_count,
            table_count=brd.table_count,
            image_count=brd.image_count,
            created_at=brd.created_at,
            updated_at=brd.updated_at,
            preview=await self._preview(brd),
            pipeline_settings=parse_pipeline_settings(brd.pipeline_settings),
            chunk_count=chunk_count,
        )

    async def _to_detail(
        self, brd: BrdDocument, *, include_text: bool
    ) -> BrdDetailResponse:
        text = (
            await self.storage.read_parsed_markdown(brd.parsed_text_path)
            if include_text
            else None
        )
        summary = await self._to_summary(brd)
        return BrdDetailResponse(
            **summary.model_dump(exclude={"file_size_mb", "is_ready", "has_parse_error"}),
            images=await self._image_responses(brd),
            parsed_text=text,
            char_count=len(text) if text is not None else None,
            word_count=len(text.split()) if text is not None else None,
        )
