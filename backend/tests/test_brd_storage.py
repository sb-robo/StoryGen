from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.services.brd.storage_service import BrdStorageService


@pytest.mark.asyncio
async def test_save_original_and_parsed_markdown(tmp_path: Path):
    storage = BrdStorageService(root=tmp_path)
    original = await storage.save_original(
        user_id=7, brd_id=3, filename="original.pdf", content=b"%PDF-1.4"
    )
    parsed = await storage.save_parsed_markdown(user_id=7, brd_id=3, text="# Feature A\n")

    assert original.exists()
    assert original.read_bytes() == b"%PDF-1.4"
    assert parsed.exists()
    assert await storage.read_parsed_markdown(str(parsed)) == "# Feature A\n"
    assert (await storage.images_dir(7, 3)).is_dir()


@pytest.mark.asyncio
async def test_save_upload_stream(tmp_path: Path):
    storage = BrdStorageService(root=tmp_path)
    upload = AsyncMock()
    upload.read = AsyncMock(side_effect=[b"hello ", b"world", b""])

    path, size = await storage.save_upload_stream(
        user_id=1,
        brd_id=2,
        filename="original.txt",
        upload=upload,
        max_bytes=1024,
    )

    assert size == 11
    assert path.read_bytes() == b"hello world"


@pytest.mark.asyncio
async def test_save_upload_stream_rejects_oversized(tmp_path: Path):
    storage = BrdStorageService(root=tmp_path)
    upload = AsyncMock()
    upload.read = AsyncMock(side_effect=[b"12345", b""])

    with pytest.raises(ValueError, match="exceeds max size"):
        await storage.save_upload_stream(
            user_id=1,
            brd_id=2,
            filename="original.txt",
            upload=upload,
            max_bytes=4,
        )


@pytest.mark.asyncio
async def test_list_and_resolve_images(tmp_path: Path):
    storage = BrdStorageService(root=tmp_path)
    images_dir = await storage.images_dir(1, 2)
    (images_dir / "img_001.png").write_bytes(b"png-bytes")

    items = await storage.list_images(1, 2)
    assert len(items) == 1
    assert items[0]["filename"] == "img_001.png"
    assert items[0]["content_type"] == "image/png"

    assert await storage.resolve_image_path(1, 2, "img_001.png") is not None
    assert await storage.resolve_image_path(1, 2, "../secrets.txt") is None
    assert await storage.resolve_image_path(1, 2, "missing.png") is None


@pytest.mark.asyncio
async def test_clear_images_dir_removes_stale_files(tmp_path: Path):
    storage = BrdStorageService(root=tmp_path)
    images_dir = await storage.images_dir(1, 2)
    (images_dir / "img_001.png").write_bytes(b"png-bytes")
    (images_dir / "img_002.png").write_bytes(b"png-bytes")

    await storage.clear_images_dir(1, 2)

    assert list(images_dir.iterdir()) == []


@pytest.mark.asyncio
async def test_clear_images_dir_noop_when_missing(tmp_path: Path):
    storage = BrdStorageService(root=tmp_path)
    # Directory was never created for this brd — should not raise.
    await storage.clear_images_dir(99, 99)


@pytest.mark.asyncio
async def test_delete_brd_dir(tmp_path: Path):
    storage = BrdStorageService(root=tmp_path)
    brd_dir = await storage.ensure_brd_dir(4, 5)
    (brd_dir / "original.pdf").write_bytes(b"%PDF")
    await storage.delete_brd_dir(4, 5)
    assert not brd_dir.exists()
