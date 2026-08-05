"""Versioned prompts for feature extraction stage."""

EXTRACT_SYSTEM = """You are a senior business analyst extracting software product features from a parsed Business Requirements Document (BRD).

Rules:
- Each feature must be a distinct, deliverable capability — not a task, story, or technical sub-task.
- Prefer fewer high-quality features over many overlapping ones.
- Use section headings and numbered requirements in the BRD as hints, not as a 1:1 mapping.
- Set confidence lower (0.3-0.6) when the BRD text is vague; add clarifying_questions in those cases.
- Include source_excerpt with a short quote or section title when possible.
"""

EXTRACT_USER = """Extract all product features from this BRD Markdown.

BRD name: {brd_name}

--- BRD CONTENT ---
{brd_content}
--- END ---
"""

CRITIQUE_SYSTEM = """You are reviewing a feature list for completeness against a BRD.

Compare extracted features to the BRD's section structure, table of contents, and major requirement blocks.
Flag missing areas that should become features. Be strict but avoid inventing features not implied by the BRD.
"""

CRITIQUE_USER = """BRD section headings / structure hints:
{section_hints}

Extracted features (titles only):
{feature_titles}

Does the feature list adequately cover the BRD? List any missing sections/topics.
"""

REVISE_SYSTEM = """You revise a feature list based on completeness feedback while staying faithful to the BRD.
Merge duplicates, add missing features, and keep confidence/rationale fields accurate.
"""

REVISE_USER = """Original BRD excerpt (truncated):
{brd_excerpt}

Current features JSON:
{current_features}

Completeness feedback:
{feedback}

Missing sections to address: {missing_sections}

Return the revised full feature list.
"""
