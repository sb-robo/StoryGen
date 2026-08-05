from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.async_operation import AsyncOperation, OperationStatus, OperationType
from app.db.models.brd_document import BrdDocument, BrdStatus
from app.repositories.brd_repository import BrdRepository
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
from app.schemas.operation_schema import OperationResponse
from app.services.brd.parser_service import BrdParserService
from app.services.brd.storage_service import BrdStorageService

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx"}
EXTENSION_MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
PREVIEW_CHARS = 280


class BrdService:
    def __init__(
        self,
        db: AsyncSession,
        storage: BrdStorageService | None = None,
        parser_service: BrdParserService | None = None,
    ):
        self.db = db
        self.repo = BrdRepository(db)
        self.operation_repo = OperationRepository(db)
        self.storage = storage or BrdStorageService()
        self.parser_service = parser_service or BrdParserService(storage=self.storage)

    def _normalize_extension(self, filename: str) -> str:
        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '{extension}'. Allowed: PDF, DOCX, XLSX.",
            )
        return extension

    async def _get_owned_brd(self, user_id: int, brd_id: int) -> BrdDocument:
        brd = await self.repo.get_by_id_for_user(brd_id, user_id)
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
        self, user_id: int, file: UploadFile, *, name: str
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

        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required",
            )

        extension = self._normalize_extension(file.filename)
        mime_type = file.content_type or EXTENSION_MIME.get(extension)
        stored_filename = f"original{extension}"

        operation = await self.operation_repo.create(
            AsyncOperation(
                user_id=user_id,
                operation_type=OperationType.BRD_UPLOAD.value,
                status=OperationStatus.PENDING.value,
                resource_type="brd",
            )
        )

        brd = BrdDocument(
            user_id=user_id,
            name=brd_name,
            original_filename=file.filename,
            stored_filename=stored_filename,
            mime_type=mime_type,
            file_extension=extension,
            file_size_bytes=0,
            storage_path="",
            original_path="",
            status=BrdStatus.UPLOADED.value,
        )
        brd = await self.repo.create(brd)

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

        brd.original_path = str(original_path)
        brd.file_size_bytes = size
        brd.status = BrdStatus.PARSING.value
        brd.error_message = None
        brd = await self.repo.update(brd)

        operation.resource_id = brd.id
        operation = await self.operation_repo.mark_running(operation)

        # Commit before the response so the background task can see both rows.
        await self.db.commit()
        return self._operation_response(operation)

    async def enqueue_reparse(self, user_id: int, brd_id: int) -> OperationResponse:
        """Create a reparse operation; caller schedules background parse by operation_id."""
        brd = await self._get_owned_brd(user_id, brd_id)
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
        return self._operation_response(operation)

    async def complete_parse(self, brd_id: int) -> BrdDocument | None:
        """Used by the background worker (no ownership check — internal)."""
        brd = await self.repo.get_by_id(brd_id)
        if not brd:
            return None

        try:
            return await self._run_parse(brd)
        except Exception as exc:
            brd.status = BrdStatus.PARSE_FAILED.value
            brd.error_message = str(exc)
            return await self.repo.update(brd)

    async def _run_parse(self, brd: BrdDocument) -> BrdDocument:
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
        return await self.repo.update(brd)

    async def list_brds(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
        status_filter: str | None = None,
        search: str | None = None,
    ) -> BrdListResponse:
        items = await self.repo.list_for_user(
            user_id,
            skip=skip,
            limit=limit,
            status=status_filter,
            search=search,
        )
        total = await self.repo.count_for_user(
            user_id,
            status=status_filter,
            search=search,
        )
        summaries = [await self._to_summary(item) for item in items]
        return BrdListResponse(
            items=summaries,
            total=total,
            skip=skip,
            limit=limit,
            status=status_filter,
            search=search,
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

    async def delete_brd(self, user_id: int, brd_id: int) -> BrdDeleteResponse:
        brd = await self._get_owned_brd(user_id, brd_id)
        await self.storage.delete_brd_dir(user_id, brd_id)
        await self.repo.delete(brd)
        return BrdDeleteResponse(id=brd_id)

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
