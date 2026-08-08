export function ReviewActions({ onApprove, onReject, onEdit, disabled }) {
  return (
    <div className="review-actions">
      <button type="button" className="btn btn-success btn-sm" onClick={onApprove} disabled={disabled}>
        Approve
      </button>
      {onReject && (
        <button type="button" className="btn btn-danger btn-sm" onClick={onReject} disabled={disabled}>
          Reject
        </button>
      )}
      {onEdit && (
        <button type="button" className="btn btn-secondary btn-sm" onClick={onEdit} disabled={disabled}>
          Edit
        </button>
      )}
    </div>
  )
}
