import { useNavigate } from 'react-router-dom'
import { useJobs } from '../context/JobsContext'
import { brdIdForJob } from '../utils/jobFocus'

function JobStatusIcon({ status }) {
  if (status === 'running') return <span className="job-icon job-icon-running">●</span>
  if (status === 'succeeded') return <span className="job-icon job-icon-success">✓</span>
  if (status === 'cancelled') return <span className="job-icon job-icon-cancelled">–</span>
  return <span className="job-icon job-icon-failed">✕</span>
}

function statusLabel(job) {
  if (job.status === 'running') return 'Running…'
  if (job.status === 'succeeded') return 'Completed'
  if (job.status === 'cancelled') return 'Cancelled'
  return job.error || 'Failed'
}

export function JobsButton() {
  const { runningCount, setDrawerOpen } = useJobs()

  return (
    <button type="button" className="btn btn-ghost jobs-trigger" onClick={() => setDrawerOpen(true)}>
      Jobs
      {runningCount > 0 && <span className="jobs-badge">{runningCount}</span>}
    </button>
  )
}

export function JobsDrawer() {
  const navigate = useNavigate()
  const { jobs, drawerOpen, setDrawerOpen, clearFinished, cancelJob, retryJob, setJobFocus } =
    useJobs()

  if (!drawerOpen) return null

  const hasFinished = jobs.some((j) => j.status !== 'running')

  function openJob(job) {
    const brdId = brdIdForJob(job)
    if (brdId == null) return
    const focus = {
      brdId,
      resourceType: job.resourceType,
      resourceId: job.resourceId,
      operationType: job.operationType,
    }
    setJobFocus(focus)
    setDrawerOpen(false)
    navigate(`/brds/${brdId}`, { state: { jobFocus: focus } })
  }

  return (
    <>
      <div className="drawer-backdrop" onClick={() => setDrawerOpen(false)} />
      <aside className="jobs-drawer" aria-label="Background jobs">
        <div className="drawer-header">
          <h2>Jobs</h2>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setDrawerOpen(false)} aria-label="Close">
            ✕
          </button>
        </div>
        {jobs.length === 0 && <p className="empty-hint drawer-empty">No background jobs yet.</p>}
        {jobs.length > 0 && (
          <>
            {hasFinished && (
              <div className="drawer-toolbar">
                <button type="button" className="btn btn-ghost btn-sm" onClick={clearFinished}>
                  Clear finished
                </button>
              </div>
            )}
            <ul className="jobs-list">
              {jobs.map((job) => {
                const canOpen = brdIdForJob(job) != null
                return (
                  <li key={job.id} className={`job-item job-${job.status}`}>
                    <JobStatusIcon status={job.status} />
                    <div className="job-item-body">
                      {canOpen ? (
                        <button
                          type="button"
                          className="job-item-link"
                          onClick={() => openJob(job)}
                          title="Open affected BRD / item"
                        >
                          <strong>{job.label}</strong>
                        </button>
                      ) : (
                        <strong>{job.label}</strong>
                      )}
                      <span className="meta">{statusLabel(job)}</span>
                      {canOpen && (
                        <span className="meta job-item-hint">Click to open</span>
                      )}
                      <div className="job-item-actions">
                        {job.status === 'running' && (
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            onClick={() => cancelJob(job)}
                          >
                            Cancel
                          </button>
                        )}
                        {(job.status === 'failed' || job.status === 'cancelled') && (
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={() => retryJob(job)}
                          >
                            Retry
                          </button>
                        )}
                      </div>
                    </div>
                  </li>
                )
              })}
            </ul>
          </>
        )}
      </aside>
    </>
  )
}
