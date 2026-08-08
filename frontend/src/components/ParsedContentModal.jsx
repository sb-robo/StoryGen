export function ParsedContentModal({ content, loading, onClose }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal modal-lg" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Parsed BRD content</h3>
          <button type="button" className="btn btn-ghost btn-sm modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <div className="modal-body">
          {loading ? (
            <p className="empty-hint">Loading full content…</p>
          ) : (
            <pre className="content-preview content-preview-modal">{content}</pre>
          )}
        </div>
      </div>
    </div>
  )
}
