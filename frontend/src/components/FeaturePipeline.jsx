import { useCallback, useEffect, useState } from 'react'
import * as brdApi from '../api/brds'
import * as featureApi from '../api/features'
import { FeatureDetailModal } from './FeatureDetailModal'
import { FeatureTile } from './FeatureTile'
import { useOperationPoll } from '../hooks/useOperationPoll'
import { OperationBanner } from './OperationBanner'

export function FeaturePipeline({ brdId, brdReady }) {
  const [features, setFeatures] = useState([])
  const [selectedFeature, setSelectedFeature] = useState(null)
  const [busy, setBusy] = useState(false)
  const { operation, error, loading, startPoll } = useOperationPoll()

  const load = useCallback(async () => {
    const data = await brdApi.listFeatures(brdId)
    setFeatures(data.items)
    setSelectedFeature((current) => {
      if (!current) return null
      return data.items.find((item) => item.id === current.id) ?? current
    })
  }, [brdId])

  useEffect(() => {
    load()
  }, [load])

  async function handleExtract() {
    setBusy(true)
    try {
      const op = await brdApi.extractFeatures(brdId)
      await startPoll(op)
      await load()
    } finally {
      setBusy(false)
    }
  }

  async function handleReview(id, action) {
    setBusy(true)
    try {
      if (action === 'approve') await featureApi.approveFeature(id)
      else await featureApi.rejectFeature(id)
      await load()
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel">
      <div className="section-toolbar">
        <h2>Features</h2>
        {brdReady && (
          <button type="button" className="btn btn-primary" onClick={handleExtract} disabled={busy || loading}>
            Extract features
          </button>
        )}
      </div>
      <OperationBanner operation={operation} error={error} loading={loading} />
      {!brdReady && <p className="empty-hint">Parse the BRD before extracting features.</p>}
      {brdReady && features.length === 0 && !loading && (
        <p className="empty-hint">No features yet. Run extraction to get started.</p>
      )}
      {features.length > 0 && (
        <div className="feature-grid">
          {features.map((feature) => (
            <FeatureTile key={feature.id} feature={feature} onClick={setSelectedFeature} />
          ))}
        </div>
      )}

      {selectedFeature && (
        <FeatureDetailModal
          key={selectedFeature.id}
          feature={selectedFeature}
          busy={busy}
          onClose={() => setSelectedFeature(null)}
          onReview={handleReview}
          onUpdated={load}
        />
      )}
    </section>
  )
}
