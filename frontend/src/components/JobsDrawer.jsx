import { useJobs } from '../context/JobsContext'

function JobStatusIcon({ status }) {
  if (status === 'running') return <span className="job-icon job-icon-running">●</span>
  if (status === 'succeeded') return <span className="job-icon job-icon-success">✓</span>
  return <span className="job-icon job-icon-failed">✕</span>
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
  const { jobs, drawerOpen, setDrawerOpen, clearFinished } = useJobs()

  if (!drawerOpen) return null

  const hasFinished = jobs.some((j) => j.status !== 'running')

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
              {jobs.map((job) => (
                <li key={job.id} className={`job-item job-${job.status}`}>
                  <JobStatusIcon status={job.status} />
                  <div className="job-item-body">
                    <strong>{job.label}</strong>
                    <span className="meta">
                      {job.status === 'running' && 'Running…'}
                      {job.status === 'succeeded' && 'Completed'}
                      {job.status === 'failed' && (job.error || 'Failed')}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </aside>
    </>
  )
}
