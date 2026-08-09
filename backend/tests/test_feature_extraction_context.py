from unittest.mock import AsyncMock, MagicMock

import pytest

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


@pytest.mark.asyncio
async def test_merge_semantic_collapses_near_duplicate_titles():
    merger = FeatureMerger()
    outputs = [
        FeatureExtractionOutput(
            features=[
                ExtractedFeatureItem(
                    title="User Login",
                    description="Short",
                    confidence=0.8,
                    rationale="a",
                )
            ]
        ),
        FeatureExtractionOutput(
            features=[
                ExtractedFeatureItem(
                    title="Login & Authentication",
                    description="Users authenticate with email and password, longer text",
                    confidence=0.85,
                    rationale="b",
                )
            ]
        ),
        FeatureExtractionOutput(
            features=[
                ExtractedFeatureItem(
                    title="Settlement Reporting",
                    description="Export settlement reports as CSV",
                    confidence=0.8,
                    rationale="c",
                )
            ]
        ),
    ]

    # Embeddings crafted so the two "login" features are near-identical vectors
    # and the reporting feature is orthogonal — mirrors real embedding geometry
    # for semantically similar vs. unrelated text.
    embed_batch = AsyncMock(
        return_value=[
            [1.0, 0.0, 0.0],
            [0.99, 0.01, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )

    merged = await merger.merge_semantic(outputs, embed_batch=embed_batch)

    assert len(merged.features) == 2
    titles = {f.title for f in merged.features}
    assert "Settlement Reporting" in titles
    login_feature = next(f for f in merged.features if f.title != "Settlement Reporting")
    assert login_feature.description.startswith("Users authenticate")


@pytest.mark.asyncio
async def test_merge_semantic_keeps_distinct_features_when_below_threshold():
    merger = FeatureMerger()
    outputs = [
        FeatureExtractionOutput(
            features=[
                ExtractedFeatureItem(
                    title="User Login",
                    description="Sign in with email and password",
                    confidence=0.8,
                    rationale="a",
                ),
                ExtractedFeatureItem(
                    title="Settlement Reporting",
                    description="Export settlement reports as CSV",
                    confidence=0.8,
                    rationale="b",
                ),
            ]
        )
    ]

    embed_batch = AsyncMock(return_value=[[1.0, 0.0], [0.0, 1.0]])

    merged = await merger.merge_semantic(outputs, embed_batch=embed_batch)

    assert len(merged.features) == 2
