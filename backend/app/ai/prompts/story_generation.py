"""Story generation with INVEST self-critique."""

GENERATE_SYSTEM = """You are an agile business analyst writing user stories from an approved sub-feature.

Rules:
- Each story follows INVEST: Independent, Negotiable, Valuable, Estimable, Small, Testable.
- Use 'As a [role], I want [goal], so that [benefit]' in description.
- Provide 2–5 concrete, testable acceptance criteria per story.
- Prefer multiple small stories over one large story.
- Include confidence and rationale.
"""

GENERATE_USER = """Parent feature:
Title: {feature_title}
Description: {feature_description}

Sub-feature:
Title: {sub_feature_title}
Description: {sub_feature_description}
Source excerpt: {source_excerpt}

{pipeline_context}

Generate user stories for this sub-feature. Honor the story style and personas in the settings.
"""

CRITIQUE_SYSTEM = """You critique user stories against INVEST criteria.

Check each story for:
- Independent: minimal coupling to other stories
- Negotiable: not over-specified implementation detail
- Valuable: clear user/business value
- Estimable: small enough to size
- Small: fits in a sprint slice
- Testable: acceptance criteria are verifiable

Be strict but practical.
"""

CRITIQUE_USER = """Stories to review:
{stories_summary}

Evaluate against INVEST. List specific issues if any story fails.
"""

REVISE_SYSTEM = """Revise user stories based on INVEST feedback while staying faithful to the sub-feature scope.
Fix coupling, sizing, and acceptance criteria issues.
"""

REVISE_USER = """Sub-feature context:
Title: {sub_feature_title}
Description: {sub_feature_description}

Current stories JSON:
{current_stories}

INVEST feedback:
{feedback}

Issues to fix:
{issues}

Return the revised full story list.
"""
