export const DEFAULT_PIPELINE_SETTINGS = {
  instructions: '',
  domain_context: '',
  in_scope: '',
  out_of_scope: '',
  personas: '',
  feature_count: 'auto',
  sub_feature_count: 'auto',
  story_style: 'classic',
  pointing_scale: 'fibonacci',
  test_depth: 'standard',
  chunk_level: 'section',
  export_project_key: '',
  export_epic_prefix: '',
}

/** Chunking strategies — keep in sync with backend BrdChunkStrategy / GET /brds/chunk-strategies */
export const CHUNK_STRATEGY_OPTIONS = [
  {
    value: 'section',
    label: 'Section (H1 + H2)',
    summary: 'Split on major section headings — recommended default.',
    whenToUse:
      'Standard BRDs with clear headings. Best for feature extraction and first-pass review.',
    tradeoffs: 'Broader chunks; may merge related sub-topics under one section.',
    recommended: true,
  },
  {
    value: 'subsection',
    label: 'Subsection (H1 + H2 + H3)',
    summary: 'Finer splits at third-level headings.',
    whenToUse:
      'Long BRDs where H2 sections are still too large, or when you need tighter grounding for stories/tests.',
    tradeoffs: 'More chunks; slightly higher indexing cost.',
  },
  {
    value: 'requirement',
    label: 'Requirement-aware',
    summary: 'Split on numbered requirements and shall/must bullet items.',
    whenToUse:
      'Enterprise BRDs with REQ-001 / 1.2.3 numbering or explicit shall/must statements.',
    tradeoffs: 'Weak when the BRD has no numbered requirements or IDs.',
  },
  {
    value: 'fixed_size',
    label: 'Fixed-size windows',
    summary: 'Even-sized chunks (~1500 chars) with overlap.',
    whenToUse:
      'Unstructured or flat documents with poor headings, pasted specs, or legacy Word exports.',
    tradeoffs: 'May cut mid-requirement; use only when headings are unreliable.',
  },
  {
    value: 'hybrid',
    label: 'Hybrid (best quality)',
    summary: 'Sections → table extraction → semantic split for large sections.',
    whenToUse:
      'Production BRDs with tables, long sections, and mixed formatting. Best retrieval quality.',
    tradeoffs: 'Slowest indexing; uses embedding API during parse/reparse.',
  },
]

/** @deprecated use CHUNK_STRATEGY_OPTIONS */
export const CHUNK_LEVEL_OPTIONS = CHUNK_STRATEGY_OPTIONS.map(({ value, label }) => ({
  value,
  label,
}))

export function getChunkStrategyGuide(value) {
  return CHUNK_STRATEGY_OPTIONS.find((opt) => opt.value === value) ?? CHUNK_STRATEGY_OPTIONS[0]
}

export const FEATURE_COUNT_OPTIONS = [
  { value: 'auto', label: 'Auto (let AI decide)' },
  { value: 'fewer', label: 'Fewer (~5–8 epic features)' },
  { value: 'balanced', label: 'Balanced (~8–12)' },
  { value: 'granular', label: 'Granular (~12–20)' },
]

export const SUB_FEATURE_COUNT_OPTIONS = [
  { value: 'auto', label: 'Auto (2–6 typical)' },
  { value: 'fewer', label: 'Fewer (2–3)' },
  { value: 'balanced', label: 'Balanced (3–5)' },
  { value: 'more', label: 'More (5–8)' },
]

export const STORY_STYLE_OPTIONS = [
  { value: 'classic', label: 'Classic (As a… I want… so that…)' },
  { value: 'job_story', label: 'Job story (When… I want… so I can…)' },
  { value: 'plain', label: 'Plain description' },
]

export const POINTING_SCALE_OPTIONS = [
  { value: 'fibonacci', label: 'Fibonacci (1, 2, 3, 5, 8, 13, 21)' },
  { value: 't_shirt', label: 'T-shirt (XS–XXL → points)' },
  { value: 'linear', label: 'Linear (1–10)' },
]

export const TEST_DEPTH_OPTIONS = [
  { value: 'happy_path', label: 'Happy path focus' },
  { value: 'standard', label: 'Standard (happy + edge + negative)' },
  { value: 'thorough', label: 'Thorough (extra boundaries)' },
]

/** Strip empty strings so the API stores nulls / omits noise. */
export function serializePipelineSettings(settings) {
  const out = {}
  for (const [key, value] of Object.entries(settings)) {
    if (typeof value === 'string') {
      const trimmed = value.trim()
      if (trimmed) out[key] = trimmed
    } else if (value != null) {
      out[key] = value
    }
  }
  return out
}

/** Normalize API/settings payload into controlled form state. */
export function hydratePipelineSettings(raw) {
  return {
    ...DEFAULT_PIPELINE_SETTINGS,
    ...(raw || {}),
    instructions: raw?.instructions ?? '',
    domain_context: raw?.domain_context ?? '',
    in_scope: raw?.in_scope ?? '',
    out_of_scope: raw?.out_of_scope ?? '',
    personas: raw?.personas ?? '',
    export_project_key: raw?.export_project_key ?? '',
    export_epic_prefix: raw?.export_epic_prefix ?? '',
    chunk_level: raw?.chunk_level ?? 'section',
  }
}
