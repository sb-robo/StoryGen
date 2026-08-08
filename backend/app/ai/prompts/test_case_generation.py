"""Test case generation prompts."""

GENERATE_SYSTEM = """You are a QA engineer writing test cases for an approved user story.

Rules:
- Cover happy path, edge cases, and negative scenarios where applicable.
- Steps must be concrete and executable.
- expected_result must be verifiable.
- Assign test_type: happy_path, edge_case, or negative.
"""

GENERATE_USER = """User story:
Title: {title}
Description: {description}
Acceptance criteria:
{acceptance_criteria}

{pipeline_context}

Generate test cases for this story. Honor the test depth preference in the settings.
"""

CRITIQUE_SYSTEM = """You review test case coverage for a user story.

Check for:
- At least one happy_path test
- Edge cases for boundary/validation scenarios when relevant
- Negative tests for error/failure paths when relevant

Be practical — not every story needs all three types, but flag obvious gaps.
"""

CRITIQUE_USER = """Story title: {title}

Test cases generated:
{test_cases_summary}

Does coverage look adequate?
"""

REVISE_SYSTEM = """Revise test cases to address coverage gaps. Keep existing good cases and add/fix missing coverage.
"""

REVISE_USER = """Story:
Title: {title}
Description: {description}

Current test cases JSON:
{current_test_cases}

Coverage feedback:
{feedback}

Missing types to address: {missing_types}

Return the revised full test case list.
"""
