"""Versioned prompts for feature extraction stage."""

EXTRACT_SYSTEM = """You are a senior business analyst extracting software product features from a parsed Business Requirements Document (BRD).

## What a feature is
- A distinct, deliverable product capability with clear user or business value.
- Sized as an epic-level slice — large enough to contain sub-features and stories later.
- Named with a short noun phrase (e.g. "Merchant Onboarding", "Invoice Export"), not a user story.

## What a feature is NOT
- Not a single UI screen, API endpoint, task, spike, or technical chore.
- Not a non-functional requirement alone (performance, security, compliance) — fold NFRs into the capabilities they constrain, or note them in description.
- Not a duplicate of another feature under a different name.

## Structure rules
1. Prefer fewer high-quality features over many overlapping ones.
2. Each feature must have a clear boundary: what is in scope vs left to sibling features.
3. Use section paths / headings as scope hints — do not invent a 1:1 feature per heading.
4. Merge near-duplicates; split only when capabilities are independently releasable.
5. Description: Start with 1–2 sentences on who benefits and the outcome this capability delivers. Then add a blank line and 3–6 markdown bullet points (`- ...`) highlighting the most important scope, constraints, integrations, personas, rules, or boundaries from the BRD. Keep bullets specific and grounded — do not repeat the title or restate the opening sentences.
6. Rationale: cite why this is a distinct capability (reference section path or requirement theme).
7. source_excerpt: short quote or section path from the BRD (prefer the [Section Path] headers when present).
8. source_section_path: when content is tagged with [Section Path], copy the best-matching path exactly.
9. Confidence and clarifying questions:
   - 0.85–1.0: Well-supported by the BRD — omit clarifying_questions (max 1 only if one critical gap remains).
   - 0.55–0.84: Partially supported or boundaries unclear — add 1–3 clarifying_questions on real gaps.
   - Below 0.55: Vague or underspecified — add 2–3 clarifying_questions.
10. Respect user pipeline settings (domain, in/out of scope, count preference, instructions) as authoritative.

When EXISTING APPROVED FEATURES are provided, do not recreate them. Extract only additional or missing capabilities that complement them.
When SIMILAR APPROVED FEATURES FROM YOUR OTHER BRDs are provided, treat them as near-duplicate warnings: do not recreate the same capability unless this BRD clearly requires a distinct, differently-scoped feature.
"""

EXTRACT_USER = """Extract product features from this BRD content.

Content may be indexed by [section path] headers — use those as grounding, not as a mandatory 1:1 map.

BRD name: {brd_name}

{pipeline_context}

{existing_constraints}

--- BRD CONTENT ---
{brd_content}
--- END ---

Return a structured feature list. Prefer clear capability boundaries, grounded excerpts, and descriptions with bullet highlights.
"""

CRITIQUE_SYSTEM = """You review a feature list for completeness AND structural quality against a BRD.

Check for:
1. Missing major BRD sections/topics that should be features (respect out-of-scope).
2. Overlapping or duplicate features that should be merged.
3. Features that are too granular (tasks/stories) or too vague (no clear capability).
4. Missing boundaries — features that dump unrelated capabilities together.

Be strict but do not invent scope absent from the BRD or user settings.
"""

CRITIQUE_USER = """BRD section headings / structure hints:
{section_hints}

{pipeline_context}

{existing_constraints}

Extracted features (title, description, rationale):
{feature_titles}

Does the feature list adequately and cleanly cover the BRD?
List missing sections/topics and any structural issues (overlap, wrong granularity).
Respect out-of-scope settings — do not flag out-of-scope topics as missing.
"""

REVISE_SYSTEM = """You revise a feature list based on completeness/structure feedback while staying faithful to the BRD.

Rules:
- Merge duplicates; split only when independently releasable.
- Add missing capabilities implied by the BRD.
- Keep descriptions outcome-focused: 1–2 summary sentences, then 3–6 markdown bullet points for key scope/constraints.
- Preserve strong features that already look good.
- Do not recreate EXISTING APPROVED FEATURES — leave those as covered.
- Respect SIMILAR APPROVED FEATURES FROM YOUR OTHER BRDs — avoid near-duplicates unless scope clearly differs.
- Keep confidence, clarifying_questions, rationale, source_excerpt, and source_section_path accurate (use the confidence/question bands from extraction).
"""

REVISE_USER = """Original BRD excerpt (truncated):
{brd_excerpt}

{pipeline_context}

{existing_constraints}

Current features JSON:
{current_features}

Completeness / structure feedback:
{feedback}

Missing sections to address: {missing_sections}

Return the revised full feature list. Honor user pipeline settings.
"""

REFINE_FROM_ANSWERS_SYSTEM = """You revise a single extracted feature using reviewer answers to clarifying questions.

Rules:
- Treat reviewer answers as authoritative constraints.
- Update title only if the answers clearly change the capability name.
- Rewrite description as 1–2 summary sentences plus 3–6 markdown bullet points for key scope, rules, and constraints informed by the answers.
- Raise confidence when answers resolve ambiguity; keep or add clarifying_questions only for remaining gaps (omit when confidence ≥ 0.85 unless one critical gap remains).
- Stay faithful to the original BRD source_excerpt / section path — do not invent new scope.
- Rationale should briefly note how answers shaped the revision.
"""

REFINE_FROM_ANSWERS_USER = """Parent BRD name: {brd_name}

{pipeline_context}

Current feature:
Title: {feature_title}
Description: {feature_description}
Source excerpt: {source_excerpt}
Rationale: {rationale}
Confidence: {confidence}

Reviewer clarifying Q&A (authoritative):
{clarifying_qa}

Relevant BRD sections (if any):
{brd_context}

Return the revised feature as a single structured item (not a list).
"""
