import { useState } from 'react'
import { StatusBadge } from './StatusBadge'

export function ReviewCard({
  title,
  description,
  extra,
  status,
  confidence,
  rationale,
  actions,
  children,
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <article className="review-card">
      <div className="review-card-header">
        <div>
          <h4>{title}</h4>
          <StatusBadge status={status} />
          {confidence != null && (
            <span className="meta">Confidence: {(confidence * 100).toFixed(0)}%</span>
          )}
        </div>
        <div className="review-actions">{actions}</div>
      </div>
      <p className="review-description">{description}</p>
      {extra}
      {rationale && (
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setExpanded(!expanded)}>
          {expanded ? 'Hide rationale' : 'Show rationale'}
        </button>
      )}
      {expanded && rationale && <p className="rationale">{rationale}</p>}
      {children}
    </article>
  )
}

export function ReviewActions({ onApprove, onReject, onEdit, disabled }) {
  return (
    <>
      <button type="button" className="btn btn-success btn-sm" onClick={onApprove} disabled={disabled}>
        Approve
      </button>
      <button type="button" className="btn btn-danger btn-sm" onClick={onReject} disabled={disabled}>
        Reject
      </button>
      {onEdit && (
        <button type="button" className="btn btn-secondary btn-sm" onClick={onEdit} disabled={disabled}>
          Edit
        </button>
      )}
    </>
  )
}
