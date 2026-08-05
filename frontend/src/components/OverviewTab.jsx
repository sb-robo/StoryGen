import { PIPELINE_STAGES } from '../utils/pipeline'

function stageSummary(stage) {
  if (stage.status === 'locked') return 'Locked'
  if (stage.status === 'complete') return 'Complete'
  if (stage.status === 'needs_review') return `${stage.pending} pending`
  if (stage.status === 'failed') return 'Failed'
  if (stage.status === 'in_progress') return 'In progress'
  if (stage.counts?.total > 0) {
    return `${stage.counts.approved}/${stage.counts.total} approved`
  }
  return 'Not started'
}

export function OverviewTab({
  pipeline,
  reviewQueue,
  blockers,
  suggestedStep,
  recentJobs,
  batchActions,
  busy,
  onGoToQueue,
  onSuggestedAction,
  onBatchAction,
}) {
  return (
    <section className="overview-tab">
      <div className="overview-hero">
        <div className="overview-attention">
          <h2>Needs your attention</h2>
          {reviewQueue.length > 0 ? (
            <>
              <p className="overview-count">{reviewQueue.length} item{reviewQueue.length !== 1 ? 's' : ''} pending review</p>
              <button type="button" className="btn btn-primary" onClick={onGoToQueue} disabled={busy}>
                Open review queue
              </button>
            </>
          ) : (
            <p className="empty-hint">All caught up — nothing pending review.</p>
          )}
        </div>

        <div className="overview-next">
          <h2>Suggested next step</h2>
          <p className="overview-suggestion">{suggestedStep?.label ?? 'Loading…'}</p>
          {suggestedStep?.action && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => onSuggestedAction(suggestedStep)}
              disabled={busy}
            >
              {suggestedStep.label}
            </button>
          )}
        </div>
      </div>

      {blockers.length > 0 && (
        <div className="overview-section panel-inner">
          <h3>Blockers</h3>
          <ul className="blocker-list">
            {blockers.map((b) => (
              <li key={b.id}>
                <strong>{b.featureTitle}</strong> — {b.unanswered} unanswered clarifying question{b.unanswered !== 1 ? 's' : ''}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="overview-section panel-inner">
        <h3>Pipeline progress</h3>
        <ul className="pipeline-checklist">
          {PIPELINE_STAGES.filter((s) => s.id !== 'parse').map((stage) => {
            const data = pipeline?.stages?.[stage.id]
            if (!data) return null
            return (
              <li key={stage.id} className={`checklist-item checklist-${data.status}`}>
                <span className="checklist-label">{stage.label}</span>
                <span className="checklist-status">{stageSummary(data)}</span>
              </li>
            )
          })}
        </ul>
      </div>

      {batchActions.length > 0 && (
        <div className="overview-section panel-inner">
          <h3>Batch actions</h3>
          <div className="batch-actions">
            {batchActions.map((action) => (
              <button
                key={action.id}
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => onBatchAction(action.id)}
                disabled={busy || action.disabled}
              >
                {action.label}
                {action.count != null && ` (${action.count})`}
              </button>
            ))}
          </div>
        </div>
      )}

      {recentJobs.length > 0 && (
        <div className="overview-section panel-inner">
          <h3>Recent AI runs</h3>
          <ul className="recent-jobs-list">
            {recentJobs.map((job) => (
              <li key={job.id} className={`recent-job recent-job-${job.status}`}>
                <span>{job.label}</span>
                <span className="meta">
                  {job.status === 'running' && 'Running…'}
                  {job.status === 'succeeded' && 'Completed'}
                  {job.status === 'failed' && (job.error || 'Failed')}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
