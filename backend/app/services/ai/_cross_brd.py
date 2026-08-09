"""Cross-BRD near-duplicate retrieval helpers (Phase 5)."""

from __future__ import annotations

from app.ai.openai_client import OpenAIClient
from app.ai.rag.chunk_retrieval import build_retrieval_query
from app.ai.rag.feature_retrieval import (
    format_similar_cross_brd_features,
    retrieve_similar_features,
)
from app.ai.rag.story_retrieval import (
    format_similar_cross_brd_stories,
    retrieve_similar_stories_cross_brd,
)
from app.utils.process_tracker import track, track_error


async def fetch_cross_brd_feature_context(
    db,
    client: OpenAIClient,
    *,
    user_id: int,
    exclude_brd_id: int,
    query_parts: list[str | None],
) -> str:
    """
    Retrieve similar approved features from the user's other BRDs.

    Returns a formatted prompt block, or empty string when unavailable.
    """
    query = build_retrieval_query(*query_parts)
    if not query:
        track("skipped cross-BRD feature search (empty query)", brd_id=exclude_brd_id)
        return ""

    track("search cross-BRD similar features", brd_id=exclude_brd_id)
    try:
        matches = await retrieve_similar_features(
            db,
            client,
            user_id=user_id,
            query_text=query,
            exclude_brd_id=exclude_brd_id,
        )
    except Exception as exc:
        track_error(
            "cross-BRD feature retrieval failed; continuing",
            exc=exc,
            brd_id=exclude_brd_id,
        )
        return ""

    if not matches:
        track("no cross-BRD feature matches", brd_id=exclude_brd_id)
        return ""
    track(
        "cross-BRD features retrieved",
        brd_id=exclude_brd_id,
        count=len(matches),
    )
    return format_similar_cross_brd_features(matches)


async def fetch_cross_brd_story_context(
    db,
    client: OpenAIClient,
    *,
    user_id: int,
    exclude_brd_id: int,
    query_parts: list[str | None],
) -> str:
    """Retrieve similar approved stories from the user's other BRDs for generation."""
    query = build_retrieval_query(*query_parts)
    if not query:
        track("skipped cross-BRD story search (empty query)", brd_id=exclude_brd_id)
        return ""

    track("search cross-BRD similar stories", brd_id=exclude_brd_id)
    try:
        matches = await retrieve_similar_stories_cross_brd(
            db,
            client,
            user_id=user_id,
            query_text=query,
            exclude_brd_id=exclude_brd_id,
        )
    except Exception as exc:
        track_error(
            "cross-BRD story retrieval failed; continuing",
            exc=exc,
            brd_id=exclude_brd_id,
        )
        return ""

    if not matches:
        track("no cross-BRD story matches", brd_id=exclude_brd_id)
        return ""
    track(
        "cross-BRD stories retrieved",
        brd_id=exclude_brd_id,
        count=len(matches),
    )
    return format_similar_cross_brd_stories(matches)


async def annotate_features_with_cross_brd_matches(
    db,
    client: OpenAIClient,
    *,
    user_id: int,
    exclude_brd_id: int,
    features: list,
) -> None:
    """Attach near-duplicate matches onto each feature for UI warnings (best-effort)."""
    if not features or not client.is_configured:
        return

    track(
        "annotate features with cross-BRD matches",
        brd_id=exclude_brd_id,
        count=len(features),
    )
    for feature in features:
        query = build_retrieval_query(feature.title, feature.description)
        if not query:
            continue
        try:
            matches = await retrieve_similar_features(
                db,
                client,
                user_id=user_id,
                query_text=query,
                exclude_brd_id=exclude_brd_id,
            )
        except Exception as exc:
            track_error(
                "feature cross-BRD annotate failed",
                exc=exc,
                feature_id=getattr(feature, "id", None),
            )
            continue
        feature.cross_brd_similar = (
            [m.to_match_dict() for m in matches] if matches else None
        )


async def annotate_stories_with_cross_brd_matches(
    db,
    client: OpenAIClient,
    *,
    user_id: int,
    exclude_brd_id: int,
    stories: list,
) -> None:
    """Attach near-duplicate matches onto each story for UI warnings (best-effort)."""
    if not stories or not client.is_configured:
        return

    track(
        "annotate stories with cross-BRD matches",
        brd_id=exclude_brd_id,
        count=len(stories),
    )
    for story in stories:
        query = build_retrieval_query(story.title, story.description)
        if not query:
            continue
        try:
            matches = await retrieve_similar_stories_cross_brd(
                db,
                client,
                user_id=user_id,
                query_text=query,
                exclude_brd_id=exclude_brd_id,
            )
        except Exception as exc:
            track_error(
                "story cross-BRD annotate failed",
                exc=exc,
                story_id=getattr(story, "id", None),
            )
            continue
        story.cross_brd_similar = (
            [m.to_match_dict() for m in matches] if matches else None
        )
