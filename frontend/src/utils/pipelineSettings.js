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
  export_project_key: '',
  export_epic_prefix: '',
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
