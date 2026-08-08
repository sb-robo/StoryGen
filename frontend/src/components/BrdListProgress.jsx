import { useEffect, useState } from 'react'
import { getPipelineSummary } from '../api/brds'

function formatProgress(stages) {
  if (!stages) return null
  const parts = []
  const features = stages.features?.counts
  const stories = stages.stories?.counts
  const tests = stages.tests?.counts
  if (features?.total > 0) {
    parts.push(`Features ${Math.round((features.approved / features.total) * 100)}%`)
  }
  if (stories?.total > 0) {
    parts.push(`Stories ${Math.round((stories.approved / stories.total) * 100)}%`)
  }
  if (tests?.total > 0) {
    parts.push(`Tests ${Math.round((tests.approved / tests.total) * 100)}%`)
  }
  return parts.length > 0 ? parts.join(' · ') : null
}

export function BrdListProgress({ brdId, brdStatus }) {
  const [progress, setProgress] = useState(null)
  const [pending, setPending] = useState(null)

  useEffect(() => {
    if (brdStatus !== 'parsed') {
      setProgress(null)
      setPending(null)
      return
    }

    let cancelled = false

    getPipelineSummary(brdId)
      .then((summary) => {
        if (cancelled) return
        setProgress(formatProgress(summary.stages))
        setPending(summary.totals?.pending_review ?? 0)
      })
      .catch(() => {
        if (!cancelled) {
          setProgress(null)
          setPending(null)
        }
      })

    return () => {
      cancelled = true
    }
  }, [brdId, brdStatus])

  if (brdStatus !== 'parsed') return null

  return (
    <div className="brd-list-progress">
      {progress && <span className="meta progress-label">{progress}</span>}
      {pending > 0 && <span className="pending-badge">{pending} pending</span>}
    </div>
  )
}
