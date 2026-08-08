const STATUS_CLASSES = {
  parsed: 'success',
  uploaded: 'neutral',
  parsing: 'running',
  parse_failed: 'error',
  pending_review: 'warning',
  approved: 'success',
  rejected: 'error',
  draft: 'neutral',
  pending: 'running',
  running: 'running',
  succeeded: 'success',
  failed: 'error',
  cancelled: 'neutral',
}

export function StatusBadge({ status }) {
  const variant = STATUS_CLASSES[status] || 'neutral'
  return <span className={`badge badge-${variant}`}>{status.replace(/_/g, ' ')}</span>
}
