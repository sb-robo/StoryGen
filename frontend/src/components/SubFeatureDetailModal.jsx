import { useState } from 'react'
import * as subFeatureApi from '../api/subFeatures'
import { EditModal } from './EditModal'
import { ReviewActions } from './ReviewCard'
import { StatusBadge } from './StatusBadge'
import { StorySection } from './StorySection'

export function SubFeatureDetailModal({
  subFeature,
  busy,
  onClose,
  onReview,
  onUpdated,
}) {
  const [editItem, setEditItem] = useState(null)
  const [showRationale, setShowRationale] = useState(false)

  if (!subFeature) return null

  async function handleSave(payload) {
    await subFeatureApi.updateSubFeature(subFeature.id, payload)
    await onUpdated?.()
  }

  return (
    <div className="modal-backdrop modal-backdrop-nested" onClick={onClose}>
      <div className="modal modal-lg feature-detail-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3>{subFeature.title}</h3>
            <div className="feature-detail-meta">
              <StatusBadge status={subFeature.status} />
              {subFeature.confidence != null && (
                <span className="meta">Confidence: {(subFeature.confidence * 100).toFixed(0)}%</span>
              )}
            </div>
          </div>
          <button type="button" className="btn btn-ghost btn-sm modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        {subFeature.status === 'pending_review' && (
          <div className="modal-toolbar">
            <ReviewActions
              onApprove={() => onReview(subFeature.id, 'approve')}
              onReject={() => onReview(subFeature.id, 'reject')}
              onEdit={() => setEditItem(subFeature)}
              disabled={busy}
            />
          </div>
        )}

        <div className="modal-body">
          <section className="detail-block">
            <h4>Description</h4>
            <p className="review-description">{subFeature.description}</p>
          </section>

          {subFeature.rationale && (
            <section className="detail-block">
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setShowRationale(!showRationale)}
              >
                {showRationale ? 'Hide rationale' : 'Show rationale'}
              </button>
              {showRationale && <p className="rationale">{subFeature.rationale}</p>}
            </section>
          )}

          {subFeature.source_excerpt && (
            <section className="detail-block">
              <h4>Source excerpt</h4>
              <p className="source-excerpt">{subFeature.source_excerpt}</p>
            </section>
          )}

          <StorySection subFeature={subFeature} onRefresh={onUpdated} />
        </div>
      </div>

      {editItem && (
        <EditModal
          title="Edit sub-feature"
          fields={[
            { name: 'title', label: 'Title', value: editItem.title },
            { name: 'description', label: 'Description', type: 'textarea', value: editItem.description },
          ]}
          onSave={handleSave}
          onClose={() => setEditItem(null)}
          layered
        />
      )}
    </div>
  )
}
