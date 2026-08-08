from unittest.mock import MagicMock

from app.ai.feature_extraction.context_builder import FeatureExtractionContextBuilder
from app.ai.feature_extraction.feature_merger import FeatureMerger
from app.ai.states.feature_state import ExtractedFeatureItem, FeatureExtractionOutput
from app.db.models.brd_chunk import BrdChunk


def _chunk(
    *,
    idx: int,
    section_path: str,
    content: str,
    heading: str | None = None,
) -> BrdChunk:
    chunk = MagicMock(spec=BrdChunk)
    chunk.chunk_index = idx
    chunk.section_path = section_path
    chunk.heading = heading
    chunk.content = content
    chunk.chunk_kind = "section"
    return chunk


def test_context_builder_formats_chunks():
    builder = FeatureExtractionContextBuilder(MagicMock())
    chunks = [
        _chunk(idx=0, section_path="Auth", heading="Authentication", content="Users log in."),
        _chunk(idx=1, section_path="Auth > MFA", heading="MFA", content="Second factor required."),
    ]
    formatted = builder._format_chunks(chunks)
    assert "[Auth]" in formatted
    assert "Users log in." in formatted
    assert "[Auth > MFA]" in formatted


def test_feature_merger_deduplicates_titles():
    merger = FeatureMerger()
    first = FeatureExtractionOutput(
        features=[
            ExtractedFeatureItem(
                title="User Login",
                description="Short",
                confidence=0.8,
                rationale="a",
            )
        ]
    )
    second = FeatureExtractionOutput(
        features=[
            ExtractedFeatureItem(
                title="user login",
                description="Longer description",
                confidence=0.9,
                rationale="b",
            )
        ]
    )
    merged = merger.merge([first, second])
    assert len(merged.features) == 1
    assert merged.features[0].description == "Longer description"
