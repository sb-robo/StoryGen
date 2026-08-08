from pathlib import Path

from app.ai.chunking.markdown_chunker import chunk_markdown
from app.schemas.pipeline_settings_schema import BrdChunkStrategy

SAMPLE_BRD = Path(__file__).resolve().parents[1] / "samples" / "sample_brd.md"


def test_section_level_splits_on_h1_and_h2():
    text = SAMPLE_BRD.read_text()
    chunks = chunk_markdown(text, level=BrdChunkStrategy.SECTION)

    assert len(chunks) >= 5
    paths = {chunk.section_path for chunk in chunks}
    assert any("Overview" in path for path in paths)
    assert any("Authentication" in path for path in paths)
    assert all(chunk.chunk_index == idx for idx, chunk in enumerate(chunks))


def test_subsection_level_is_at_least_as_fine_as_section():
    text = SAMPLE_BRD.read_text()
    section_chunks = chunk_markdown(text, level=BrdChunkStrategy.SECTION)
    subsection_chunks = chunk_markdown(text, level=BrdChunkStrategy.SUBSECTION)

    assert len(subsection_chunks) >= len(section_chunks)


def test_preamble_before_first_heading():
    text = "Intro paragraph before headings.\n\n# Title\n\nBody under title."
    chunks = chunk_markdown(text, level=BrdChunkStrategy.SECTION)

    assert chunks[0].section_path == "Preamble"
    assert "Intro paragraph" in chunks[0].content
    assert any(chunk.heading == "Title" for chunk in chunks)


def test_oversized_section_splits_into_multiple_chunks():
    body = "Paragraph one.\n\n" + ("x" * 7000)
    text = f"# Big section\n\n{body}"
    chunks = chunk_markdown(text, level=BrdChunkStrategy.SECTION, max_chunk_chars=1000)

    assert len(chunks) >= 2
    assert all(chunk.char_count <= 1000 for chunk in chunks)
