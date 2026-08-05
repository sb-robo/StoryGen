import { useCallback, useEffect, useState } from 'react'
import * as storyApi from '../api/stories'
import * as testCaseApi from '../api/testCases'
import { useJobs } from '../context/JobsContext'
import { EditModal } from './EditModal'
import { ReviewActions } from './ReviewCard'
import { StatusBadge } from './StatusBadge'

const TABS = [
  { id: 'story', label: 'Story' },
  { id: 'points', label: 'Points' },
  { id: 'tests', label: 'Test cases' },
]

export function StoryDetailTabs({ story, initialTab = 'story', onRefresh, busy, onSelectTestCase }) {
  const [tab, setTab] = useState(initialTab)
  const [testCases, setTestCases] = useState([])
  const [editPoints, setEditPoints] = useState(false)
  const [editTestCase, setEditTestCase] = useState(null)
  const [localBusy, setLocalBusy] = useState(false)
  const { trackJob } = useJobs()

  const loadTestCases = useCallback(async () => {
    const res = await storyApi.listTestCases(story.id)
    setTestCases(res.items)
  }, [story.id])

  useEffect(() => {
    loadTestCases()
  }, [loadTestCases])

  useEffect(() => {
    setTab(initialTab)
  }, [story.id, initialTab])

  async function runJob(label, fn) {
    setLocalBusy(true)
    try {
      const op = await fn()
      await trackJob(op, { label, onComplete: () => onRefresh?.() })
      await loadTestCases()
      await onRefresh?.()
    } finally {
      setLocalBusy(false)
    }
  }

  async function handleReviewTestCase(id, action) {
    setLocalBusy(true)
    try {
      if (action === 'approve') await testCaseApi.approveTestCase(id)
      else await testCaseApi.rejectTestCase(id)
      await loadTestCases()
      await onRefresh?.()
    } finally {
      setLocalBusy(false)
    }
  }

  const isBusy = busy || localBusy

  return (
    <div className="story-tabs">
      <div className="tab-bar" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={`tab-btn ${tab === t.id ? 'tab-btn-active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'story' && (
        <div className="tab-panel">
          <section className="detail-block">
            <h4>Description</h4>
            <p className="review-description">{story.description}</p>
          </section>
          {story.acceptance_criteria?.length > 0 && (
            <section className="detail-block">
              <h4>Acceptance criteria</h4>
              <ul className="criteria-list">
                {story.acceptance_criteria.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </section>
          )}
          {story.rationale && (
            <section className="detail-block">
              <h4>Rationale</h4>
              <p className="rationale">{story.rationale}</p>
            </section>
          )}
        </div>
      )}

      {tab === 'points' && (
        <div className="tab-panel">
          <div className="points-row">
            <span>Points: {story.story_points ?? '—'}</span>
            {story.points_status && <StatusBadge status={story.points_status} />}
          </div>
          {story.points_rationale && <p className="meta">{story.points_rationale}</p>}
          {story.status === 'approved' && (
            <div className="detail-actions">
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => runJob('Estimate story points', () => storyApi.estimatePoints(story.id))}
                disabled={isBusy}
              >
                Estimate points
              </button>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setEditPoints(true)} disabled={isBusy}>
                Override
              </button>
              {story.story_points && story.points_status === 'pending_review' && (
                <button
                  type="button"
                  className="btn btn-success btn-sm"
                  onClick={async () => {
                    setLocalBusy(true)
                    try {
                      await storyApi.approvePoints(story.id)
                      await onRefresh?.()
                    } finally {
                      setLocalBusy(false)
                    }
                  }}
                  disabled={isBusy}
                >
                  Approve points
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {tab === 'tests' && (
        <div className="tab-panel">
          {story.status === 'approved' && (
            <div className="detail-actions">
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => runJob('Generate test cases', () => storyApi.generateTestCases(story.id))}
                disabled={isBusy}
              >
                Generate test cases
              </button>
            </div>
          )}
          {testCases.length === 0 && <p className="empty-hint">No test cases yet.</p>}
          {testCases.length > 0 && (
            <div className="feature-grid">
              {testCases.map((tc) => (
                <button key={tc.id} type="button" className="feature-tile" onClick={() => onSelectTestCase?.(tc)}>
                  <div className="feature-tile-top">
                    <StatusBadge status={tc.status} />
                    {tc.confidence != null && (
                      <span className="feature-tile-confidence">{(tc.confidence * 100).toFixed(0)}%</span>
                    )}
                  </div>
                  <h4 className="feature-tile-title">{tc.title}</h4>
                  <p className="feature-tile-preview">{tc.steps}</p>
                  <div className="feature-tile-footer">
                    <span className="meta">{tc.test_type}</span>
                    {tc.status === 'pending_review' && (
                      <ReviewActions
                        onApprove={() => handleReviewTestCase(tc.id, 'approve')}
                        onReject={() => handleReviewTestCase(tc.id, 'reject')}
                        onEdit={() => setEditTestCase(tc)}
                        disabled={isBusy}
                      />
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {editPoints && (
        <EditModal
          title="Override story points"
          fields={[
            { name: 'story_points', label: 'Points (1–21)', type: 'number', value: story.story_points ?? '', min: 1, max: 21 },
            { name: 'points_rationale', label: 'Rationale', type: 'textarea', value: story.points_rationale ?? '' },
          ]}
          onSave={(payload) => storyApi.updatePoints(story.id, payload).then(() => onRefresh?.())}
          onClose={() => setEditPoints(false)}
        />
      )}

      {editTestCase && (
        <EditModal
          title="Edit test case"
          fields={[
            { name: 'title', label: 'Title', value: editTestCase.title },
            { name: 'steps', label: 'Steps', type: 'textarea', value: editTestCase.steps },
            { name: 'expected_result', label: 'Expected result', type: 'textarea', value: editTestCase.expected_result },
            { name: 'test_type', label: 'Type', value: editTestCase.test_type },
          ]}
          onSave={(payload) => testCaseApi.updateTestCase(editTestCase.id, payload).then(loadTestCases)}
          onClose={() => setEditTestCase(null)}
        />
      )}
    </div>
  )
}
