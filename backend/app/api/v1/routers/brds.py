from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from app.core.dependencies import get_brd_service, get_current_user, get_operation_service
from app.db.models.user import User
from app.schemas.brd_schema import (
    BrdContentResponse,
    BrdDeleteResponse,
    BrdDetailResponse,
    BrdImageListResponse,
    BrdListResponse,
    BrdStatusFilter,
)
from app.schemas.operation_schema import OperationResponse, OperationResultResponse
from app.services.brd import BrdService
from app.services.brd.tasks import run_brd_parse_task
from app.services.operations import OperationService

router = APIRouter()


@router.post(
    "/upload",
    response_model=OperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a BRD document (async operation)",
    description=(
        "Multipart form: `name` (BRD display name) + `file` (PDF/DOCX/XLSX). "
        "Returns an `operation_id` immediately. "
        "Poll `GET /brds/status/{operation_id}` for status, then "
        "`GET /brds/result/{operation_id}` for the parsed BRD."
    ),
)
async def upload_brd(
    background_tasks: BackgroundTasks,
    name: str = Form(
        ...,
        min_length=1,
        max_length=255,
        description="Display name for this BRD",
        examples=["Payments Platform BRD"],
    ),
    file: UploadFile = File(..., description="BRD file (PDF, DOCX, or XLSX)"),
    current_user: User = Depends(get_current_user),
    brd_service: BrdService = Depends(get_brd_service),
) -> OperationResponse:
    operation = await brd_service.upload(current_user.id, file, name=name)
    background_tasks.add_task(run_brd_parse_task, operation.operation_id)
    return operation


@router.get(
    "/status/{operation_id}",
    response_model=OperationResponse,
    summary="Get BRD upload/reparse status",
    description="Poll this endpoint until `done` is true (`succeeded` or `failed`).",
)
async def get_brd_operation_status(
    operation_id: str,
    current_user: User = Depends(get_current_user),
    operation_service: OperationService = Depends(get_operation_service),
) -> OperationResponse:
    return await operation_service.get_status(current_user.id, operation_id)


@router.get(
    "/result/{operation_id}",
    response_model=OperationResultResponse,
    summary="Get BRD upload/reparse result",
    description=(
        "Returns the BRD detail when the operation succeeded. "
        "Responds 409 while running, 422 if failed."
    ),
)
async def get_brd_operation_result(
    operation_id: str,
    include_text: bool = Query(
        True,
        description="Include full parsed Markdown in the BRD result payload",
    ),
    current_user: User = Depends(get_current_user),
    operation_service: OperationService = Depends(get_operation_service),
) -> OperationResultResponse:
    return await operation_service.get_result(
        current_user.id, operation_id, include_text=include_text
    )


@router.get(
    "",
    response_model=BrdListResponse,
    summary="List my BRDs",
    description="Paginated list with optional status filter and filename search.",
)
async def list_brds(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
    status_filter: BrdStatusFilter | None = Query(
        default=None,
        alias="status",
        description="Filter by pipeline status",
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=200,
        description="Case-insensitive search on BRD name or original filename",
    ),
    current_user: User = Depends(get_current_user),
    brd_service: BrdService = Depends(get_brd_service),
) -> BrdListResponse:
    return await brd_service.list_brds(
        current_user.id,
        skip=skip,
        limit=limit,
        status_filter=status_filter.value if status_filter else None,
        search=search,
    )


@router.get(
    "/{brd_id}",
    response_model=BrdDetailResponse,
    summary="Get BRD detail",
    description="Metadata, image inventory, and optionally full parsed Markdown.",
)
async def get_brd(
    brd_id: int,
    include_text: bool = Query(
        True,
        description="Include full parsed Markdown in the response",
    ),
    current_user: User = Depends(get_current_user),
    brd_service: BrdService = Depends(get_brd_service),
) -> BrdDetailResponse:
    return await brd_service.get_brd(
        current_user.id, brd_id, include_text=include_text
    )


@router.get(
    "/{brd_id}/content",
    response_model=BrdContentResponse,
    summary="Get parsed Markdown content",
    description="Returns only the extracted Markdown body for pipeline/LLM use.",
)
async def get_brd_content(
    brd_id: int,
    current_user: User = Depends(get_current_user),
    brd_service: BrdService = Depends(get_brd_service),
) -> BrdContentResponse:
    return await brd_service.get_content(current_user.id, brd_id)


@router.get(
    "/{brd_id}/images",
    response_model=BrdImageListResponse,
    summary="List extracted images",
)
async def list_brd_images(
    brd_id: int,
    current_user: User = Depends(get_current_user),
    brd_service: BrdService = Depends(get_brd_service),
) -> BrdImageListResponse:
    return await brd_service.list_images(current_user.id, brd_id)


@router.get(
    "/{brd_id}/images/{filename}",
    summary="Download an extracted image",
    response_class=FileResponse,
)
async def get_brd_image(
    brd_id: int,
    filename: str,
    current_user: User = Depends(get_current_user),
    brd_service: BrdService = Depends(get_brd_service),
) -> FileResponse:
    path = await brd_service.get_image_path(current_user.id, brd_id, filename)
    return FileResponse(path, filename=filename, media_type=None)


@router.get(
    "/{brd_id}/download",
    summary="Download original BRD file",
    response_class=FileResponse,
)
async def download_brd(
    brd_id: int,
    current_user: User = Depends(get_current_user),
    brd_service: BrdService = Depends(get_brd_service),
) -> FileResponse:
    path, filename, mime_type = await brd_service.get_original_path(
        current_user.id, brd_id
    )
    return FileResponse(path, filename=filename, media_type=mime_type)


@router.post(
    "/{brd_id}/reparse",
    response_model=OperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Re-parse an uploaded BRD (async operation)",
    description=(
        "Queues a background Docling re-parse and returns an `operation_id`. "
        "Poll `/brds/status/{operation_id}` then `/brds/result/{operation_id}`."
    ),
)
async def reparse_brd(
    brd_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    brd_service: BrdService = Depends(get_brd_service),
) -> OperationResponse:
    operation = await brd_service.enqueue_reparse(current_user.id, brd_id)
    background_tasks.add_task(run_brd_parse_task, operation.operation_id)
    return operation


@router.delete(
    "/{brd_id}",
    response_model=BrdDeleteResponse,
    summary="Delete a BRD",
    description="Deletes the database row and all on-disk artifacts for this BRD.",
)
async def delete_brd(
    brd_id: int,
    current_user: User = Depends(get_current_user),
    brd_service: BrdService = Depends(get_brd_service),
) -> BrdDeleteResponse:
    return await brd_service.delete_brd(current_user.id, brd_id)
