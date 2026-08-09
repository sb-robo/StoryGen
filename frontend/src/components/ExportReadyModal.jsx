import { useDialogA11y } from '../hooks/useDialogA11y'
import { exportReadinessLabel } from '../utils/pipeline'

/**
 * Confirms export readiness and lets the user pick CSV / Jira / Markdown.
 */
export function ExportReadyModal({ exportReadiness, busy, onExport, onClose }) {
  const dialogRef = useDialogA11y({ onClose })
  const ready = (exportReadiness?.approvedStories ?? 0) > 0
  const label = exportReadinessLabel(exportReadiness ?? { approvedStories: 0, approvedTests: 0 })

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        ref={dialogRef}
        className="modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="export-ready-title"
        aria-describedby="export-ready-message"
      >
        <h3 id="export-ready-title">Export pipeline</h3>
        <p id="export-ready-message" className="confirm-modal-message">
          {ready
            ? label
            : 'Approve at least one story before exporting. Pending reviews will not be included.'}
        </p>
        {!ready && (
          <p className="meta" style={{ marginTop: '-0.5rem' }}>
            You can still open export formats once stories are approved.
          </p>
        )}
        <div className="modal-actions export-ready-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose} data-initial-focus>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={busy || !ready}
            onClick={() => onExport?.('markdown')}
          >
            Markdown
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={busy || !ready}
            onClick={() => onExport?.('jira')}
          >
            Jira CSV
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={busy || !ready}
            onClick={() => onExport?.('csv')}
          >
            StoryGen CSV
          </button>
        </div>
      </div>
    </div>
  )
}
