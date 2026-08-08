import { useCallback, useEffect, useState } from 'react'
import { getLlmUsage } from '../api/brds'

function formatTokens(n) {
  if (n == null) return '0'
  return n.toLocaleString()
}

export function LlmUsagePanel({ brdId }) {
  const [usage, setUsage] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    if (!brdId) return
    setLoading(true)
    setError('')
    try {
      setUsage(await getLlmUsage(brdId))
    } catch (err) {
      setError(err.message || 'Failed to load LLM usage')
      setUsage(null)
    } finally {
      setLoading(false)
    }
  }, [brdId])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="overview-section llm-usage-panel">
      <div className="panel-header-row">
        <h3>LLM usage</h3>
        <button type="button" className="btn btn-ghost btn-sm" onClick={load} disabled={loading}>
          Refresh
        </button>
      </div>
      {loading && <p className="empty-hint">Loading usage…</p>}
      {error && <p className="form-error">{error}</p>}
      {!loading && usage && (
        <>
          <p className="meta">
            {formatTokens(usage.total_calls)} calls ·{' '}
            {formatTokens(usage.total_tokens_in + usage.total_tokens_out)} tokens ·{' '}
            {formatTokens(usage.total_latency_ms)} ms
          </p>
          {usage.by_node?.length > 0 ? (
            <ul className="llm-usage-nodes">
              {usage.by_node.slice(0, 8).map((node) => (
                <li key={node.node_name}>
                  <strong>{node.node_name}</strong>
                  <span className="meta">
                    {node.calls}× · {formatTokens(node.tokens_in + node.tokens_out)} tok
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty-hint">No LLM calls logged for this BRD yet.</p>
          )}
        </>
      )}
    </div>
  )
}
