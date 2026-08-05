import { useCallback, useEffect, useState } from 'react'
import * as featureApi from '../api/features'
import * as subFeatureApi from '../api/subFeatures'
import { useOperationPoll } from '../hooks/useOperationPoll'
import { OperationBanner } from './OperationBanner'
import { SubFeatureDetailModal } from './SubFeatureDetailModal'
import { SubFeatureTile } from './SubFeatureTile'

export function SubFeatureSection({ feature, onRefresh }) {
  const [subFeatures, setSubFeatures] = useState([])
  const [selectedSubFeature, setSelectedSubFeature] = useState(null)
  const [busy, setBusy] = useState(false)
  const { operation, error, loading, startPoll } = useOperationPoll()

  const load = useCallback(async () => {
    const data = await featureApi.listSubFeatures(feature.id)
    setSubFeatures(data.items)
    setSelectedSubFeature((current) => {
      if (!current) return null
      return data.items.find((item) => item.id === current.id) ?? current
    })
  }, [feature.id])

  useEffect(() => {
    load()
  }, [load])

  async function handleGenerate() {
    setBusy(true)
    try {
      const op = await featureApi.generateSubFeatures(feature.id)
      await startPoll(op)
      await load()
      onRefresh?.()
    } finally {
      setBusy(false)
    }
  }

  async function handleReview(id, action) {
    setBusy(true)
    try {
      if (action === 'approve') await subFeatureApi.approveSubFeature(id)
      else await subFeatureApi.rejectSubFeature(id)
      await load()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="nested-section">
      <div className="section-toolbar">
        <h5>Sub-features</h5>
        {feature.status === 'approved' && (
          <button type="button" className="btn btn-primary btn-sm" onClick={handleGenerate} disabled={busy || loading}>
            Generate sub-features
          </button>
        )}
      </div>
      <OperationBanner operation={operation} error={error} loading={loading} />
      {subFeatures.length === 0 && <p className="empty-hint">No sub-features yet.</p>}
      {subFeatures.length > 0 && (
        <div className="feature-grid">
          {subFeatures.map((sf) => (
            <SubFeatureTile key={sf.id} subFeature={sf} onClick={setSelectedSubFeature} />
          ))}
        </div>
      )}

      {selectedSubFeature && (
        <SubFeatureDetailModal
          key={selectedSubFeature.id}
          subFeature={selectedSubFeature}
          busy={busy}
          onClose={() => setSelectedSubFeature(null)}
          onReview={handleReview}
          onUpdated={load}
        />
      )}
    </div>
  )
}
