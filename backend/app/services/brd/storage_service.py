import asyncio
import shutil
from pathlib import Path

import aiofiles
import aiofiles.os
from fastapi import UploadFile

from app.core.config import settings

STREAM_CHUNK_SIZE = 1024 * 1024  # 1 MiB


class BrdStorageService:
    """Filesystem I/O for uploaded BRD originals and parsed artifacts."""

    def __init__(self, root: Path | None = None):
        self.root = root or settings.brd_storage_path

    def brd_dir(self, user_id: int, brd_id: int) -> Path:
        return self.root / str(user_id) / str(brd_id)

    async def ensure_brd_dir(self, user_id: int, brd_id: int) -> Path:
        path = self.brd_dir(user_id, brd_id)
        await asyncio.to_thread(path.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread((path / "images").mkdir, exist_ok=True)
        return path

    async def save_original(
        self, user_id: int, brd_id: int, filename: str, content: bytes
    ) -> Path:
        brd_dir = await self.ensure_brd_dir(user_id, brd_id)
        destination = brd_dir / filename
        async with aiofiles.open(destination, "wb") as handle:
            await handle.write(content)
        return destination

    async def save_upload_stream(
        self,
        user_id: int,
        brd_id: int,
        filename: str,
        upload: UploadFile,
        *,
        max_bytes: int,
    ) -> tuple[Path, int]:
        """
        Stream an UploadFile to disk in chunks so large BRDs do not load fully into memory.
        Returns (destination_path, bytes_written).
        """
        brd_dir = await self.ensure_brd_dir(user_id, brd_id)
        destination = brd_dir / filename
        size = 0

        try:
            async with aiofiles.open(destination, "wb") as handle:
                while True:
                    chunk = await upload.read(STREAM_CHUNK_SIZE)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_bytes:
                        raise ValueError(
                            f"File exceeds max size of {max_bytes // (1024 * 1024)}MB"
                        )
                    await handle.write(chunk)
        except Exception:
            if await aiofiles.os.path.exists(destination):
                await aiofiles.os.remove(destination)
            raise

        return destination, size

    async def save_parsed_markdown(self, user_id: int, brd_id: int, text: str) -> Path:
        brd_dir = await self.ensure_brd_dir(user_id, brd_id)
        destination = brd_dir / "parsed.md"
        async with aiofiles.open(destination, "w", encoding="utf-8") as handle:
            await handle.write(text)
        return destination

    async def images_dir(self, user_id: int, brd_id: int) -> Path:
        brd_dir = await self.ensure_brd_dir(user_id, brd_id)
        return brd_dir / "images"

    async def read_parsed_markdown(self, parsed_text_path: str | None) -> str | None:
        if not parsed_text_path:
            return None
        path = Path(parsed_text_path)
        if not await aiofiles.os.path.exists(path):
            return None
        async with aiofiles.open(path, "r", encoding="utf-8") as handle:
            return await handle.read()

    async def list_images(self, user_id: int, brd_id: int) -> list[dict]:
        images_dir = self.brd_dir(user_id, brd_id) / "images"
        if not await aiofiles.os.path.exists(images_dir):
            return []

        def _scan() -> list[dict]:
            items: list[dict] = []
            for path in sorted(images_dir.iterdir()):
                if not path.is_file():
                    continue
                items.append(
                    {
                        "filename": path.name,
                        "size_bytes": path.stat().st_size,
                        "content_type": self._guess_image_content_type(path.suffix),
                    }
                )
            return items

        return await asyncio.to_thread(_scan)

    async def resolve_image_path(
        self, user_id: int, brd_id: int, filename: str
    ) -> Path | None:
        if not filename or "/" in filename or "\\" in filename or filename.startswith("."):
            return None

        def _resolve() -> Path | None:
            images_root = (self.brd_dir(user_id, brd_id) / "images").resolve()
            path = (images_root / filename).resolve()
            if not path.is_relative_to(images_root):
                return None
            if not path.exists() or not path.is_file():
                return None
            return path

        return await asyncio.to_thread(_resolve)

    async def resolve_original_path(self, original_path: str | None) -> Path | None:
        if not original_path:
            return None
        path = Path(original_path)
        if not await aiofiles.os.path.isfile(path):
            return None
        return path

    async def delete_brd_dir(self, user_id: int, brd_id: int) -> None:
        path = self.brd_dir(user_id, brd_id)
        if await aiofiles.os.path.exists(path):
            await asyncio.to_thread(shutil.rmtree, path)

    @staticmethod
    def _guess_image_content_type(suffix: str) -> str:
        mapping = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        return mapping.get(suffix.lower(), "application/octet-stream")
