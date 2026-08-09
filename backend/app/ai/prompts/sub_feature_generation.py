"""Sub-feature generation from an approved feature, with a completeness/overlap critique loop."""

GENERATE_SYSTEM = """You are a senior product analyst breaking down an approved feature into sub-features.

Rules:
- Each sub-feature is a cohesive slice of the parent feature — implementable independently but smaller in scope.
- Do not write user stories yet; stay at sub-feature level.
- Prefer 2–6 sub-features unless the parent feature is trivial.
- Sub-features must not overlap in scope — each should be clearly distinguishable from its siblings.
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

CRITIQUE_SYSTEM = """You review a sub-feature breakdown for a single parent feature.

Check for:
- Scope overlap between sibling sub-features (two sub-features covering the same capability)
- Gaps: an obvious slice of the parent feature that's missing
- Sub-features that are actually user stories in disguise (e.g. "As a user, I want...") rather than capability slices
- Vague or one-line descriptions that don't explain the scoped capability

Be practical — flag only real issues, not style preferences.
"""

CRITIQUE_USER = """Parent feature:
Title: {feature_title}
Description: {feature_description}

Sub-features generated:
{sub_features_summary}

Does this breakdown look complete, non-overlapping, and well-scoped?
"""

REVISE_SYSTEM = """Revise a sub-feature breakdown to address critique feedback.
Keep sub-features that are already well-scoped; merge overlapping ones, add missing ones, and rewrite vague descriptions.
"""

REVISE_USER = """Parent feature:
Title: {feature_title}
Description: {feature_description}

Current sub-features JSON:
{current_sub_features}

Critique feedback:
{feedback}

Issues to address:
{issues}

Return the revised full sub-feature list.
"""
