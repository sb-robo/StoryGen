from __future__ import annotations

from collections import OrderedDict

from app.ai.states.feature_state import (
    ExtractedFeatureItem,
    FeatureExtractionOutput,
)


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

    @staticmethod
    def _normalize_key(title: str) -> str:
        return " ".join(title.lower().split())
