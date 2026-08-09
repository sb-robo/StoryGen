import { useEffect, useState } from 'react'
import * as brdApi from '../api/brds'
import { useDialogA11y } from '../hooks/useDialogA11y'

/**
 * Loads BRD chunks and highlights the linked source_chunk_id for provenance review.
 */
export function ChunkProvenanceModal({ brdId, chunkId, sourceExcerpt, onClose }) {
  const dialogRef = useDialogA11y({ onClose })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [chunk, setChunk] = useState(null)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      setChunk(null)
      try {
        const res = await brdApi.listChunks(brdId)
        if (cancelled) return
        setTotal(res.total ?? res.items?.length ?? 0)
        const found = (res.items ?? []).find((c) => c.id === chunkId) ?? null
        setChunk(found)
        if (!found) {
          setError(`Chunk #${chunkId} was not found in the current index. Reparse may have refreshed chunks.`)
        }
      } catch (err) {
        if (!cancelled) setError(err?.message || 'Failed to load BRD chunks')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [brdId, chunkId])

  useEffect(() => {
    if (!chunk || loading) return
    const el = document.getElementById(`chunk-focus-${chunk.id}`)
    el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [chunk, loading])

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        ref={dialogRef}
        className="modal modal-lg"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="chunk-provenance-title"
      >
        <div className="modal-header">
          <h3 id="chunk-provenance-title">BRD source section</h3>
          <button
            type="button"
            className="btn btn-ghost btn-sm modal-close"
            onClick={onClose}
            aria-label="Close"
            data-initial-focus
          >
            ✕
          </button>
        </div>
        <div className="modal-body">
          {loading && <p className="empty-hint">Loading indexed chunks…</p>}
          {!loading && error && !chunk && <p className="form-error">{error}</p>}
          {!loading && chunk && (
            <article id={`chunk-focus-${chunk.id}`} className="chunk-provenance">
              <header className="chunk-provenance-header">
                <p className="chunk-provenance-path">{chunk.section_path}</p>
                {chunk.heading && <h4 className="chunk-provenance-heading">{chunk.heading}</h4>}
                <p className="meta">
                  Chunk #{chunk.id}
                  {chunk.chunk_kind && chunk.chunk_kind !== 'section' ? ` · ${chunk.chunk_kind}` : ''}
                  {total > 0 ? ` · ${total} indexed` : ''}
                </p>
              </header>
              {sourceExcerpt && (
                <p className="chunk-provenance-excerpt meta">
                  AI cited: <em>{sourceExcerpt}</em>
                </p>
              )}
              <pre className="content-preview content-preview-modal chunk-provenance-body">
                {chunk.content}
              </pre>
            </article>
          )}
        </div>
      </div>
    </div>
  )
}
