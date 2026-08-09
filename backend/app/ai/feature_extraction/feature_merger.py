from __future__ import annotations

import math
from collections import OrderedDict
from collections.abc import Awaitable, Callable

from app.ai.states.feature_state import (
    ExtractedFeatureItem,
    FeatureExtractionOutput,
)

EmbedBatchFn = Callable[[list[str]], Awaitable[list[list[float]]]]

DEFAULT_SEMANTIC_DEDUP_THRESHOLD = 0.88


class FeatureMerger:
    """Merge feature lists from map-reduce passes, dropping obvious duplicates."""

    def merge(self, outputs: list[FeatureExtractionOutput]) -> FeatureExtractionOutput:
        merged: OrderedDict[str, ExtractedFeatureItem] = OrderedDict()
        for output in outputs:
            for feature in output.features:
                key = self._normalize_key(feature.title)
                if key not in merged:
                    merged[key] = feature
                    continue
                existing = merged[key]
                if len(feature.description) > len(existing.description):
                    merged[key] = feature
        return FeatureExtractionOutput(features=list(merged.values()))

    async def merge_semantic(
        self,
        outputs: list[FeatureExtractionOutput],
        *,
        embed_batch: EmbedBatchFn,
        threshold: float = DEFAULT_SEMANTIC_DEDUP_THRESHOLD,
    ) -> FeatureExtractionOutput:
        """
        Exact-title merge, then an embedding-similarity pass to catch near-duplicates
        that survive under different wording (e.g. "User Login" vs "Login & Authentication")
        because they came from different section groups in the map-reduce split.
        """
        exact_merged = self.merge(outputs).features
        if len(exact_merged) <= 1:
            return FeatureExtractionOutput(features=exact_merged)

        texts = [f"{f.title}: {f.description}" for f in exact_merged]
        vectors = await embed_batch(texts)

        kept: list[ExtractedFeatureItem] = []
        kept_vectors: list[list[float]] = []
        for feature, vector in zip(exact_merged, vectors, strict=True):
            dup_index = self._find_duplicate(vector, kept_vectors, threshold)
            if dup_index is None:
                kept.append(feature)
                kept_vectors.append(vector)
                continue
            existing = kept[dup_index]
            if len(feature.description) > len(existing.description):
                kept[dup_index] = feature
                kept_vectors[dup_index] = vector

        return FeatureExtractionOutput(features=kept)

    @classmethod
    def _find_duplicate(
        cls,
        vector: list[float],
        kept_vectors: list[list[float]],
        threshold: float,
    ) -> int | None:
        for idx, other in enumerate(kept_vectors):
            if cls._cosine_similarity(vector, other) >= threshold:
                return idx
        return None

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _normalize_key(title: str) -> str:
        return " ".join(title.lower().split())
