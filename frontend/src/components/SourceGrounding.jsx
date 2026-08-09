/**
 * Shows AI source excerpt + optional click-through to the linked BRD chunk.
 */
export function SourceGrounding({
  sourceExcerpt,
  sourceChunkId,
  onOpenChunk,
  title = 'Source grounding',
}) {
  if (!sourceExcerpt && sourceChunkId == null) return null

  const canOpen = sourceChunkId != null && typeof onOpenChunk === 'function'

  return (
    <section className="detail-block">
      <h4>{title}</h4>
      {sourceExcerpt && <p className="source-excerpt">{sourceExcerpt}</p>}
      {sourceChunkId != null && (
        <div className="source-chunk-row">
          {canOpen ? (
            <button
              type="button"
              className="btn btn-ghost btn-sm source-chunk-link"
              onClick={() => onOpenChunk(sourceChunkId)}
            >
              View BRD section (chunk #{sourceChunkId})
            </button>
          ) : (
            <p className="meta">Linked BRD chunk #{sourceChunkId}</p>
          )}
        </div>
      )}
    </section>
  )
}
