import { useDialogA11y } from '../hooks/useDialogA11y'

export function ParsedContentModal({ content, loading, onClose }) {
  const dialogRef = useDialogA11y({ onClose })

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        ref={dialogRef}
        className="modal modal-lg"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="parsed-content-title"
      >
        <div className="modal-header">
          <h3 id="parsed-content-title">Parsed BRD content</h3>
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
