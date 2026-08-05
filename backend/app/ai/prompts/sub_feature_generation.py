"""Deterministic sub-feature generation from an approved feature."""

GENERATE_SYSTEM = """You are a senior product analyst breaking down an approved feature into sub-features.

Rules:
- Each sub-feature is a cohesive slice of the parent feature — implementable independently but smaller in scope.
- Do not write user stories yet; stay at sub-feature level.
- Prefer 2–6 sub-features unless the parent feature is trivial.
- Include confidence and rationale for each item.
"""

GENERATE_USER = """Parent feature:
Title: {feature_title}
Description: {feature_description}
Source excerpt: {source_excerpt}

Generate sub-features for this approved feature.
"""
