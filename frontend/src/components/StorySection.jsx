import { useCallback, useEffect, useState } from 'react'
import * as storyApi from '../api/stories'
import * as subFeatureApi from '../api/subFeatures'
import { EditModal } from './EditModal'
import { ReviewActions, ReviewCard } from './ReviewCard'
import { useOperationPoll } from '../hooks/useOperationPoll'
import { OperationBanner } from './OperationBanner'
import { StatusBadge } from './StatusBadge'
import { TestCaseSection } from './TestCaseSection'

export function StorySection({ subFeature, onRefresh }) {
  const [stories, setStories] = useState([])
  const [editItem, setEditItem] = useState(null)
  const [editPoints, setEditPoints] = useState(null)
  const [busy, setBusy] = useState(false)
  const { operation, error, loading, startPoll } = useOperationPoll()

  const load = useCallback(async () => {
    const data = await subFeatureApi.listStories(subFeature.id)
    setStories(data.items)
  }, [subFeature.id])

  useEffect(() => {
    load()
  }, [load])

  async function handleGenerate() {
    setBusy(true)
    try {
      const op = await subFeatureApi.generateStories(subFeature.id)
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
      if (action === 'approve') await storyApi.approveStory(id)
      else await storyApi.rejectStory(id)
      await load()
    } finally {
      setBusy(false)
    }
  }

  async function handleEstimate(storyId) {
    setBusy(true)
    try {
      const op = await storyApi.estimatePoints(storyId)
      await startPoll(op)
      await load()
    } finally {
      setBusy(false)
    }
  }

  async function handleApprovePoints(storyId) {
    setBusy(true)
    try {
      await storyApi.approvePoints(storyId)
      await load()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="nested-section">
      <div className="section-toolbar">
        <h5>User stories</h5>
        {subFeature.status === 'approved' && (
          <button type="button" className="btn btn-primary btn-sm" onClick={handleGenerate} disabled={busy || loading}>
            Generate stories
          </button>
        )}
      </div>
      <OperationBanner operation={operation} error={error} loading={loading} />
      {stories.length === 0 && <p className="empty-hint">No stories yet.</p>}
      {stories.map((story) => (
        <ReviewCard
          key={story.id}
          title={story.title}
          description={story.description}
          status={story.status}
          confidence={story.confidence}
          rationale={story.rationale}
          extra={
            <>
              {story.acceptance_criteria?.length > 0 && (
                <ul className="criteria-list">
                  {story.acceptance_criteria.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              )}
              <div className="points-row">
                <span>Points: {story.story_points ?? '—'}</span>
                {story.points_status && <StatusBadge status={story.points_status} />}
                {story.status === 'approved' && (
                  <>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleEstimate(story.id)}
                      disabled={busy || loading}
                    >
                      Estimate
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => setEditPoints(story)}
                      disabled={busy}
                    >
                      Override
                    </button>
                    {story.story_points && story.points_status === 'pending_review' && (
                      <button
                        type="button"
                        className="btn btn-success btn-sm"
                        onClick={() => handleApprovePoints(story.id)}
                        disabled={busy}
                      >
                        Approve points
                      </button>
                    )}
                  </>
                )}
              </div>
              {story.points_rationale && <p className="meta">{story.points_rationale}</p>}
            </>
          }
          actions={
            story.status === 'pending_review' ? (
              <ReviewActions
                onApprove={() => handleReview(story.id, 'approve')}
                onReject={() => handleReview(story.id, 'reject')}
                onEdit={() => setEditItem(story)}
                disabled={busy}
              />
            ) : null
          }
        >
          <TestCaseSection story={story} onRefresh={load} />
        </ReviewCard>
      ))}
      {editItem && (
        <EditModal
          title="Edit story"
          fields={[
            { name: 'title', label: 'Title', value: editItem.title },
            { name: 'description', label: 'Description', type: 'textarea', value: editItem.description },
            {
              name: 'acceptance_criteria',
              label: 'Acceptance criteria (one per line)',
              type: 'lines',
              value: editItem.acceptance_criteria?.join('\n') ?? '',
            },
          ]}
          onSave={(payload) => storyApi.updateStory(editItem.id, payload).then(load)}
          onClose={() => setEditItem(null)}
        />
      )}
      {editPoints && (
        <EditModal
          title="Override story points"
          fields={[
            { name: 'story_points', label: 'Points (1–21)', type: 'number', value: editPoints.story_points ?? '', min: 1, max: 21 },
            { name: 'points_rationale', label: 'Rationale', type: 'textarea', value: editPoints.points_rationale ?? '' },
          ]}
          onSave={(payload) => storyApi.updatePoints(editPoints.id, payload).then(load)}
          onClose={() => setEditPoints(null)}
        />
      )}
    </div>
  )
}
