import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, UploadFile

from app.db.models.brd_document import BrdStatus
from app.services.brd.service import BrdService, _sniff_content_sync


def _service_with_repo(repo: MagicMock) -> BrdService:
    service = BrdService.__new__(BrdService)
    service.db = MagicMock()
    service.repo = repo
    service.operation_repo = MagicMock()
    service.storage = MagicMock()
    service.parser_service = MagicMock()
    return service


def test_normalize_extension_rejects_unsupported_format():
    service = _service_with_repo(MagicMock())
    with pytest.raises(HTTPException) as exc:
        service._normalize_extension("requirements.doc")
    assert exc.value.status_code == 400
    assert "Supported formats" in exc.value.detail


def test_normalize_extension_accepts_supported_formats():
    service = _service_with_repo(MagicMock())
    assert service._normalize_extension("a.PDF") == ".pdf"
    assert service._normalize_extension("a.docx") == ".docx"
    assert service._normalize_extension("a.xlsx") == ".xlsx"


def test_validate_mime_type_rejects_mismatch():
    service = _service_with_repo(MagicMock())
    with pytest.raises(HTTPException) as exc:
        service._validate_mime_type("text/plain", ".pdf")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_upload_rejects_duplicate_brd_name():
    repo = MagicMock()
    repo.find_by_name_for_user = AsyncMock(
        return_value=MagicMock(id=9, name="Payments BRD")
    )
    repo.find_by_original_filename_for_user = AsyncMock(return_value=None)
    service = _service_with_repo(repo)

    upload = MagicMock(spec=UploadFile)
    upload.filename = "spec.pdf"
    upload.content_type = "application/pdf"

    with pytest.raises(HTTPException) as exc:
        await service.upload(user_id=1, file=upload, name="Payments BRD")
    assert exc.value.status_code == 409
    assert "already exists" in exc.value.detail


@pytest.mark.asyncio
async def test_upload_rejects_duplicate_filename():
    repo = MagicMock()
    repo.find_by_name_for_user = AsyncMock(return_value=None)
    repo.find_by_original_filename_for_user = AsyncMock(
        return_value=MagicMock(
            id=3, name="Old BRD", original_filename="spec.pdf"
        )
    )
    service = _service_with_repo(repo)

    upload = MagicMock(spec=UploadFile)
    upload.filename = "spec.pdf"
    upload.content_type = "application/pdf"

    with pytest.raises(HTTPException) as exc:
        await service.upload(user_id=1, file=upload, name="New BRD")
    assert exc.value.status_code == 409
    assert "already uploaded" in exc.value.detail


def test_sniff_content_accepts_real_pdf(tmp_path: Path):
    path = tmp_path / "real.pdf"
    path.write_bytes(b"%PDF-1.4\n%rest of a real pdf...")
    assert _sniff_content_sync(path, ".pdf") is True


def test_sniff_content_rejects_renamed_file_as_pdf(tmp_path: Path):
    path = tmp_path / "fake.pdf"
    path.write_bytes(b"this is actually just plain text")
    assert _sniff_content_sync(path, ".pdf") is False


def test_sniff_content_accepts_real_docx(tmp_path: Path):
    path = tmp_path / "real.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", "<xml/>")
    assert _sniff_content_sync(path, ".docx") is True


def test_sniff_content_rejects_zip_without_docx_marker(tmp_path: Path):
    path = tmp_path / "fake.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("not_word/data.txt", "hello")
    assert _sniff_content_sync(path, ".docx") is False


def test_sniff_content_rejects_non_zip_as_xlsx(tmp_path: Path):
    path = tmp_path / "fake.xlsx"
    path.write_bytes(b"not a zip file at all")
    assert _sniff_content_sync(path, ".xlsx") is False


@pytest.mark.asyncio
async def test_enqueue_reparse_rejects_when_already_parsing():
    repo = MagicMock()
    repo.get_by_id_for_user = AsyncMock(
        return_value=MagicMock(id=1, status=BrdStatus.PARSING.value)
    )
    service = _service_with_repo(repo)

    with pytest.raises(HTTPException) as exc:
        await service.enqueue_reparse(user_id=1, brd_id=1)
    assert exc.value.status_code == 409
    assert "already being parsed" in exc.value.detail


@pytest.mark.asyncio
async def test_delete_brd_also_cleans_up_operation_history():
    repo = MagicMock()
    brd = MagicMock(id=1, user_id=1)
    repo.get_by_id_for_user = AsyncMock(return_value=brd)
    repo.delete = AsyncMock()
    service = _service_with_repo(repo)
    service.storage.delete_brd_dir = AsyncMock()
    service.operation_repo.delete_for_resource = AsyncMock()

    result = await service.delete_brd(user_id=1, brd_id=1)

    assert result.id == 1
    service.operation_repo.delete_for_resource.assert_awaited_once_with(1, "brd", 1)


@pytest.mark.asyncio
async def test_rename_brd_rejects_conflicting_name():
    repo = MagicMock()
    repo.get_by_id_for_user = AsyncMock(return_value=MagicMock(id=1, name="Old Name"))
    repo.find_by_name_for_user = AsyncMock(
        return_value=MagicMock(id=2, name="Taken Name")
    )
    service = _service_with_repo(repo)

    with pytest.raises(HTTPException) as exc:
        await service.rename_brd(user_id=1, brd_id=1, new_name="Taken Name")
    assert exc.value.status_code == 409
    repo.find_by_name_for_user.assert_awaited_once_with(1, "Taken Name", exclude_id=1)
