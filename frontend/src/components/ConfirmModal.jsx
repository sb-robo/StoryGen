import { useDialogA11y } from '../hooks/useDialogA11y'

export function ConfirmModal({
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  danger = false,
  onConfirm,
  onClose,
}) {
  const dialogRef = useDialogA11y({ onClose })

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        ref={dialogRef}
        className="modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-modal-title"
        aria-describedby="confirm-modal-message"
      >
        <h3 id="confirm-modal-title">{title}</h3>
        <p id="confirm-modal-message" className="confirm-modal-message">
          {message}
        </p>
        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose} data-initial-focus>
            {cancelLabel}
          </button>
          <button
            type="button"
            className={`btn ${danger ? 'btn-danger' : 'btn-primary'}`}
            onClick={() => {
              onConfirm?.()
              onClose?.()
            }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
