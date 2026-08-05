"""Story point estimation prompts."""

ESTIMATE_SYSTEM = """You are an agile tech lead estimating story points using a modified Fibonacci scale (1, 2, 3, 5, 8, 13, 21).

Consider complexity, uncertainty, and effort. Use historical similar stories when provided as calibration anchors.
"""

ESTIMATE_USER = """Estimate story points for this approved user story.

Title: {title}
Description: {description}
Acceptance criteria:
{acceptance_criteria}

Similar approved stories (for calibration):
{similar_stories}
"""

CRITIQUE_SYSTEM = """Review a story point estimate for consistency with the story scope and any similar historical stories.
Flag estimates that seem too high or too low relative to comparable work.
"""

CRITIQUE_USER = """Story:
Title: {title}
Description: {description}

Current estimate: {story_points} points
Rationale: {rationale}

Similar stories:
{similar_stories}

Is this estimate reasonable?
"""

REVISE_SYSTEM = """Revise a story point estimate based on critique feedback. Stay within 1-21 Fibonacci-like scale.
"""

REVISE_USER = """Story title: {title}

Current estimate: {story_points} points
Rationale: {rationale}

Critique feedback: {feedback}
Suggested points: {suggested_points}

Return revised estimate.
"""
