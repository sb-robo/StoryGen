import { useState } from 'react'
import { exportReadinessLabel, PIPELINE_STAGES } from '../utils/pipeline'
import { LlmUsagePanel } from './LlmUsagePanel'

const VISIBLE_BLOCKERS = 3

function stageSummary(stage) {
  if (stage.status === 'locked') return 'Locked'
  if (stage.status === 'complete') return 'Complete'
  if (stage.status === 'ready') return 'Ready'
  if (stage.status === 'needs_review') return `${stage.pending} pending`
  if (stage.status === 'failed') return 'Failed'
  if (stage.status === 'in_progress') return 'In progress'
  if (stage.counts?.total > 0) {
    return `${stage.counts.approved}/${stage.counts.total} approved`
  }
  return 'Not started'
}

function BlockersPanel({ blockers }) {
  const [expanded, setExpanded] = useState(false)
  const visible = expanded ? blockers : blockers.slice(0, VISIBLE_BLOCKERS)
  const remaining = blockers.length - VISIBLE_BLOCKERS

  return (
    <div className="overview-section blockers-panel">
      <h3>Blockers <span className="chip-count">{blockers.length}</span></h3>
      <ul className="blocker-list">
        {visible.map((b) => (
          <li key={b.id}>
            <strong>{b.featureTitle}</strong>
            <span className="blocker-count">
              {b.unanswered} unanswered clarifying question{b.unanswered !== 1 ? 's' : ''}
            </span>
          </li>
        ))}
      </ul>
      {remaining > 0 && (
        <button type="button" className="btn btn-ghost btn-sm blockers-toggle" onClick={() => setExpanded(true)}>
          Show {remaining} more
        </button>
      )}
      {expanded && blockers.length > VISIBLE_BLOCKERS && (
        <button type="button" className="btn btn-ghost btn-sm blockers-toggle" onClick={() => setExpanded(false)}>
          Show less
        </button>
      )}
    </div>
  )
}

export function OverviewTab({
  brdId,
  pipeline,
  reviewQueue,
  blockers,
  suggestedStep,
  recentJobs,
  batchActions,
  exportReadiness,
  busy,
  onGoToQueue,
  onSuggestedAction,
  onBatchAction,
}) {
  const exportReady = pipeline?.stages?.export?.status === 'ready'

  return (
    <section className="overview-tab">
      <div className="overview-stack">
        <div className="overview-section overview-next">
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

        {exportReady && exportReadiness && (
          <div className="overview-section overview-export-ready">
            <h3>Export readiness</h3>
            <p className="overview-suggestion">{exportReadinessLabel(exportReadiness)}</p>
            <p className="meta">
              Only approved stories and approved test cases are included. Pending review items are skipped.
            </p>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => onSuggestedAction?.({ action: 'export_csv', label: 'Export' })}
              disabled={busy || exportReadiness.approvedStories <= 0}
            >
              Export…
            </button>
          </div>
        )}

        <div className="overview-section overview-attention">
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

        {blockers.length > 0 && <BlockersPanel blockers={blockers} />}

        <div className="overview-section">
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
          <div className="overview-section">
            <h3>Batch actions</h3>
            <div className="batch-actions">
              {batchActions.map((action) => (
                <button
                  key={action.id}
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => onBatchAction(action.id)}
                  disabled={busy || action.disabled}
                  title={action.detail || undefined}
                >
                  {action.label}
                  {action.count != null && ` (${action.count})`}
                </button>
              ))}
            </div>
          </div>
        )}

        {recentJobs.length > 0 && (
          <div className="overview-section">
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

        {brdId != null && <LlmUsagePanel brdId={brdId} />}
      </div>
    </section>
  )
}
