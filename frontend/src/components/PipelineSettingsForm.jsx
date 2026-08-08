import {
  CHUNK_STRATEGY_OPTIONS,
  FEATURE_COUNT_OPTIONS,
  getChunkStrategyGuide,
  POINTING_SCALE_OPTIONS,
  STORY_STYLE_OPTIONS,
  SUB_FEATURE_COUNT_OPTIONS,
  TEST_DEPTH_OPTIONS,
} from '../utils/pipelineSettings'

export function PipelineSettingsForm({ settings, onChange }) {
  function update(key, value) {
    onChange({ ...settings, [key]: value })
  }

  const chunkGuide = getChunkStrategyGuide(settings.chunk_level)

  return (
    <div className="pipeline-settings">
      <label className="field">
        <span>Instructions for AI</span>
        <textarea
          value={settings.instructions}
          onChange={(e) => update('instructions', e.target.value)}
          placeholder="e.g. Ignore legal appendix. Focus on customer portal. Treat payments as out of scope."
          rows={3}
        />
      </label>

      <div className="pipeline-settings-grid">
        <label className="field">
          <span>Domain / product</span>
          <input
            type="text"
            value={settings.domain_context}
            onChange={(e) => update('domain_context', e.target.value)}
            placeholder="B2B SaaS billing for SMBs"
          />
        </label>
        <label className="field">
          <span>Personas / roles</span>
          <input
            type="text"
            value={settings.personas}
            onChange={(e) => update('personas', e.target.value)}
            placeholder="Admin, Merchant, End customer"
          />
        </label>
      </div>

      <div className="pipeline-settings-grid">
        <label className="field">
          <span>In scope</span>
          <textarea
            value={settings.in_scope}
            onChange={(e) => update('in_scope', e.target.value)}
            placeholder="Must cover auth, reporting, notifications…"
            rows={2}
          />
        </label>
        <label className="field">
          <span>Out of scope</span>
          <textarea
            value={settings.out_of_scope}
            onChange={(e) => update('out_of_scope', e.target.value)}
            placeholder="Mobile app, third-party marketplace…"
            rows={2}
          />
        </label>
      </div>

      <div className="pipeline-settings-grid">
        <label className="field">
          <span>Feature count</span>
          <select value={settings.feature_count} onChange={(e) => update('feature_count', e.target.value)}>
            {FEATURE_COUNT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Sub-feature count</span>
          <select
            value={settings.sub_feature_count}
            onChange={(e) => update('sub_feature_count', e.target.value)}
          >
            {SUB_FEATURE_COUNT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Story style</span>
          <select value={settings.story_style} onChange={(e) => update('story_style', e.target.value)}>
            {STORY_STYLE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Pointing scale</span>
          <select value={settings.pointing_scale} onChange={(e) => update('pointing_scale', e.target.value)}>
            {POINTING_SCALE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Test depth</span>
          <select value={settings.test_depth} onChange={(e) => update('test_depth', e.target.value)}>
            {TEST_DEPTH_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="chunk-strategy-block">
        <label className="field">
          <span>BRD chunking strategy</span>
          <select value={settings.chunk_level} onChange={(e) => update('chunk_level', e.target.value)}>
            {CHUNK_STRATEGY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
                {opt.recommended ? ' (recommended)' : ''}
              </option>
            ))}
          </select>
        </label>
        <div className="chunk-strategy-guide" role="note">
          <p className="chunk-strategy-guide-summary">{chunkGuide.summary}</p>
          <p>
            <strong>When to use:</strong> {chunkGuide.whenToUse}
          </p>
          <p>
            <strong>Tradeoffs:</strong> {chunkGuide.tradeoffs}
          </p>
          <p className="chunk-strategy-guide-hint">
            Applied on parse/reparse. Changing strategy re-indexes chunks without re-uploading the file.
          </p>
        </div>
      </div>

      <div className="pipeline-settings-grid">
        <label className="field">
          <span>Jira project key (export)</span>
          <input
            type="text"
            value={settings.export_project_key}
            onChange={(e) => update('export_project_key', e.target.value)}
            placeholder="PAY"
            maxLength={32}
          />
        </label>
        <label className="field">
          <span>Epic name prefix (export)</span>
          <input
            type="text"
            value={settings.export_epic_prefix}
            onChange={(e) => update('export_epic_prefix', e.target.value)}
            placeholder="Payments —"
            maxLength={64}
          />
        </label>
      </div>
    </div>
  )
}
