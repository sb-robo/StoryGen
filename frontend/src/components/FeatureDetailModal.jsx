import { useState } from 'react'
import * as featureApi from '../api/features'
import { ClarifyingAnswersForm } from './ClarifyingAnswersForm'
import { EditModal } from './EditModal'
import { ReviewActions } from './ReviewCard'
import { StatusBadge } from './StatusBadge'
import { SubFeatureSection } from './SubFeatureSection'

export function FeatureDetailModal({
  feature,
  busy,
  onClose,
  onReview,
  onUpdated,
}) {
  const [editItem, setEditItem] = useState(null)
  const [showRationale, setShowRationale] = useState(false)

  if (!feature) return null

  async function handleSave(payload) {
    await featureApi.updateFeature(feature.id, payload)
    await onUpdated?.()
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal modal-lg feature-detail-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3>{feature.title}</h3>
            <div className="feature-detail-meta">
              <StatusBadge status={feature.status} />
              {feature.confidence != null && (
                <span className="meta">Confidence: {(feature.confidence * 100).toFixed(0)}%</span>
              )}
            </div>
          </div>
          <button type="button" className="btn btn-ghost btn-sm modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        {feature.status === 'pending_review' && (
          <div className="modal-toolbar">
            <ReviewActions
              onApprove={() => onReview(feature.id, 'approve')}
              onReject={() => onReview(feature.id, 'reject')}
              onEdit={() => setEditItem(feature)}
              disabled={busy}
            />
          </div>
        )}

        <div className="modal-body">
          <section className="detail-block">
            <h4>Description</h4>
            <p className="review-description">{feature.description}</p>
          </section>

          {feature.clarifying_questions?.length > 0 && (
            <section className="detail-block">
              <h4>Clarifying questions</h4>
              <ClarifyingAnswersForm feature={feature} onSaved={onUpdated} disabled={busy} />
            </section>
          )}

          {feature.rationale && (
            <section className="detail-block">
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setShowRationale(!showRationale)}
              >
                {showRationale ? 'Hide rationale' : 'Show rationale'}
              </button>
              {showRationale && <p className="rationale">{feature.rationale}</p>}
            </section>
          )}

          {feature.source_excerpt && (
            <section className="detail-block">
              <h4>Source excerpt</h4>
              <p className="source-excerpt">{feature.source_excerpt}</p>
            </section>
          )}

          <SubFeatureSection feature={feature} onRefresh={onUpdated} />
        </div>
      </div>

      {editItem && (
        <EditModal
          title="Edit feature"
          fields={[
            { name: 'title', label: 'Title', value: editItem.title },
            { name: 'description', label: 'Description', type: 'textarea', value: editItem.description },
            {
              name: 'clarifying_questions',
              label: 'Clarifying questions (one per line)',
              type: 'lines',
              value: editItem.clarifying_questions?.join('\n') ?? '',
            },
          ]}
          onSave={handleSave}
          onClose={() => setEditItem(null)}
          layered
        />
      )}
    </div>
  )
}
