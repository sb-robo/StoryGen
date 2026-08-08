"""Deterministic sub-feature generation from an approved feature."""

GENERATE_SYSTEM = """You are a senior product analyst breaking down an approved feature into sub-features.

Rules:
- Each sub-feature is a cohesive slice of the parent feature — implementable independently but smaller in scope.
- Do not write user stories yet; stay at sub-feature level.
- Prefer 2–6 sub-features unless the parent feature is trivial.
- Include confidence and rationale for each item.
- When clarifying Q&A from the reviewer is provided, treat those answers as authoritative constraints.
"""

GENERATE_USER = """Parent feature:
Title: {feature_title}
Description: {feature_description}
Source excerpt: {source_excerpt}

Relevant BRD sections:
{brd_context}

{pipeline_context}

Reviewer clarifying Q&A:
{clarifying_qa}

Generate sub-features for this approved feature. Honor the reviewer answers and pipeline settings above.
Use the BRD sections to keep scope grounded in the source document.
"""
