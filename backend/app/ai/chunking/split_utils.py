from __future__ import annotations

import re

_DEFAULT_OVERLAP_CHARS = 200


def split_oversized(
    text: str,
    *,
    max_chars: int,
    overlap: int = _DEFAULT_OVERLAP_CHARS,
) -> list[str]:
    """Split long text on paragraph boundaries with optional overlap."""
    stripped = text.strip()
    if not stripped:
        return []
    if len(stripped) <= max_chars:
        return [stripped]

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", stripped) if part.strip()]
    if not paragraphs:
        return [stripped[:max_chars]]

    parts: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if not current:
            return
        parts.append("\n\n".join(current))
        current = []
        current_len = 0

    for paragraph in paragraphs:
        paragraph_len = len(paragraph)
        if paragraph_len > max_chars:
            flush()
            start = 0
            while start < paragraph_len:
                end = min(start + max_chars, paragraph_len)
                parts.append(paragraph[start:end].strip())
                if end >= paragraph_len:
                    break
                start = max(end - overlap, start + 1)
            continue

        extra = 2 if current else 0
        if current and current_len + extra + paragraph_len > max_chars:
            flush()
        current.append(paragraph)
        current_len += extra + paragraph_len

    flush()
    return parts or [stripped[:max_chars]]
