import { useEffect, useState } from 'react'
import { computePipelineState, getProgressLabel, getTotalPending } from '../utils/pipeline'
import { loadFullPipeline } from '../utils/loadPipeline'

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

    loadFullPipeline(brdId)
      .then((data) => {
        if (cancelled) return
        const pipeline = computePipelineState({
          brdStatus,
          features: data.features,
          subFeatures: data.subFeatures,
          stories: data.stories,
          testCases: data.testCases,
        })
        setProgress(getProgressLabel(pipeline))
        setPending(getTotalPending(pipeline))
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
