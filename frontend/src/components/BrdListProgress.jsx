import { useEffect, useState } from 'react'
import { getPipelineSummary } from '../api/brds'

function buildChips(stages) {
  if (!stages) return []
  const chips = []
  const features = stages.features?.counts
  const stories = stages.stories?.counts
  const tests = stages.tests?.counts
  if (features?.total > 0) {
    chips.push({ label: 'Features', pct: Math.round((features.approved / features.total) * 100) })
  }
  if (stories?.total > 0) {
    chips.push({ label: 'Stories', pct: Math.round((stories.approved / stories.total) * 100) })
  }
  if (tests?.total > 0) {
    chips.push({ label: 'Tests', pct: Math.round((tests.approved / tests.total) * 100) })
  }
  return chips
}

export function BrdListProgress({ brdId, brdStatus }) {
  const [chips, setChips] = useState([])
  const [pending, setPending] = useState(null)

  useEffect(() => {
    if (brdStatus !== 'parsed') {
      setChips([])
      setPending(null)
      return
    }

    let cancelled = false

    getPipelineSummary(brdId)
      .then((summary) => {
        if (cancelled) return
        setChips(buildChips(summary.stages))
        setPending(summary.totals?.pending_review ?? 0)
      })
      .catch(() => {
        if (!cancelled) {
          setChips([])
          setPending(null)
        }
      })

    return () => {
      cancelled = true
    }
  }, [brdId, brdStatus])

  if (brdStatus !== 'parsed') return null
  if (chips.length === 0 && !pending) return null

  return (
    <div className="brd-list-progress">
      {chips.map((chip) => (
        <span
          key={chip.label}
          className={`stage-chip ${chip.pct >= 100 ? 'stage-chip-complete' : chip.pct > 0 ? 'stage-chip-partial' : ''}`}
        >
          {chip.label} {chip.pct}%
        </span>
      ))}
      {pending > 0 && <span className="pending-badge">{pending} pending</span>}
    </div>
  )
}
