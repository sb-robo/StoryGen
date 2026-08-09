import { useCallback, useEffect, useMemo, useState } from 'react'
import * as storyApi from '../api/stories'
import * as testCaseApi from '../api/testCases'
import { useJobs } from '../context/JobsContext'
import { CrossBrdSimilarWarning } from './CrossBrdSimilarWarning'
import { EditModal } from './EditModal'
import { ReviewActions } from './ReviewCard'
import { SourceGrounding } from './SourceGrounding'
import { StatusBadge } from './StatusBadge'

const TABS = [
  { id: 'story', label: 'Story' },
  { id: 'points', label: 'Points' },
  { id: 'tests', label: 'Test cases' },
]

function testCasesForStory(allTestCases, storyId) {
  return allTestCases.filter((tc) => Number(tc.story_id) === Number(storyId))
}

export function StoryDetailTabs({
  story,
  pipelineTestCases = [],
  initialTab = 'story',
  onRefresh,
  busy,
  onOpenChunk,
  onSelectTestCase,
}) {
  const [tab, setTab] = useState(initialTab)
  const [testCases, setTestCases] = useState(() => testCasesForStory(pipelineTestCases, story.id))
  const [editPoints, setEditPoints] = useState(false)
  const [editTestCase, setEditTestCase] = useState(null)
  const [enqueueing, setEnqueueing] = useState(false)
  const [reviewBusy, setReviewBusy] = useState(false)
  const { trackJob, isJobRunningFor } = useJobs()
  const pointsJobRunning = isJobRunningFor('story', story.id, 'story_point_estimation')
  const testsJobRunning = isJobRunningFor('story', story.id, 'test_case_generation')

  const pipelineCases = useMemo(
    () => testCasesForStory(pipelineTestCases, story.id),
    [pipelineTestCases, story.id],
  )

  const loadTestCases = useCallback(async () => {
    try {
      const res = await storyApi.listTestCases(story.id)
      setTestCases(res.items ?? [])
    } catch {
      setTestCases(pipelineCases)
    }
  }, [story.id, pipelineCases])

  useEffect(() => {
    setTestCases(pipelineCases)
  }, [pipelineCases])

  useEffect(() => {
    void loadTestCases()
  }, [loadTestCases])

  useEffect(() => {
    setTab(initialTab)
  }, [story.id, initialTab])

  useEffect(() => {
    if (!testsJobRunning) {
      void loadTestCases()
    }
  }, [testsJobRunning, loadTestCases])

  async function runJob(label, fn) {
    setEnqueueing(true)
    try {
      const op = await fn()
      void trackJob(op, {
        label,
        onComplete: () => {
          void loadTestCases()
          void onRefresh?.()
        },
      }).catch(() => {})
    } finally {
      setEnqueueing(false)
    }
  }

  async function handleReviewTestCase(id, action) {
    setReviewBusy(true)
    try {
      if (action === 'approve') await testCaseApi.approveTestCase(id)
      else await testCaseApi.rejectTestCase(id)
      await loadTestCases()
      await onRefresh?.()
    } finally {
      setReviewBusy(false)
    }
  }

  const formBusy = busy || enqueueing || reviewBusy
  const pointsBusy = formBusy || pointsJobRunning
  const testsBusy = formBusy || testsJobRunning
  const storiesWithTestsCount = useMemo(
    () => new Set(pipelineTestCases.map((tc) => tc.story_id)).size,
    [pipelineTestCases],
  )
  const pointsLabel =
    story.story_points != null ? `${story.story_points} pts` : 'Not estimated'
  const testsLabel = testCases.length === 1 ? '1 test case' : `${testCases.length} test cases`

  function tabLabel(t) {
    if (t.id === 'points' && story.story_points != null) {
      return `${t.label} (${story.story_points})`
    }
    if (t.id === 'tests' && testCases.length > 0) {
      return `${t.label} (${testCases.length})`
    }
    return t.label
  }

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
            {tabLabel(t)}
          </button>
        ))}
      </div>

      {tab === 'story' && (
        <div className="tab-panel">
          <section className="detail-block story-derived-summary">
            <h4>Story points &amp; tests</h4>
            <div className="story-derived-grid">
              <button type="button" className="story-derived-card" onClick={() => setTab('points')}>
                <span className="story-derived-label">Story points</span>
                <span className="story-derived-value">{pointsLabel}</span>
                {story.points_status && <StatusBadge status={story.points_status} />}
              </button>
              <button type="button" className="story-derived-card" onClick={() => setTab('tests')}>
                <span className="story-derived-label">Test cases</span>
                <span className="story-derived-value">{testsLabel}</span>
              </button>
            </div>
          </section>

          <section className="detail-block">
            <h4>Description</h4>
            <p className="review-description">{story.description}</p>
          </section>
          <CrossBrdSimilarWarning matches={story.cross_brd_similar} label="stories" />
          <SourceGrounding
            sourceExcerpt={story.source_excerpt}
            sourceChunkId={story.source_chunk_id}
            onOpenChunk={(id) => onOpenChunk?.(id, story.source_excerpt)}
          />
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
          {!story.story_points && story.status === 'approved' && (
            <p className="empty-hint">
              Points have not been estimated for this story yet. Click Estimate points below, or use
              {' '}
              <strong>Estimate points</strong>
              {' '}
              in Overview batch actions to run all stories at once.
            </p>
          )}
          {!story.story_points && story.status !== 'approved' && (
            <p className="empty-hint">Approve this story before estimating points.</p>
          )}
          {story.status === 'approved' && (
            <div className="detail-actions">
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => runJob('Estimate story points', () => storyApi.estimatePoints(story.id))}
                disabled={pointsBusy}
              >
                {pointsJobRunning ? 'Estimating…' : story.story_points ? 'Re-estimate points' : 'Estimate points'}
              </button>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setEditPoints(true)} disabled={formBusy}>
                Override
              </button>
              {story.story_points && story.points_status === 'pending_review' && (
                <button
                  type="button"
                  className="btn btn-success btn-sm"
                  onClick={async () => {
                    setReviewBusy(true)
                    try {
                      await storyApi.approvePoints(story.id)
                      await onRefresh?.()
                    } finally {
                      setReviewBusy(false)
                    }
                  }}
                  disabled={formBusy}
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
          {story.status !== 'approved' && (
            <p className="empty-hint">Approve this story before generating test cases.</p>
          )}
          {story.status === 'approved' && (
            <div className="detail-actions">
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => runJob('Generate test cases', () => testCaseApi.generateTestCases(story.id))}
                disabled={testsBusy}
              >
                {testsJobRunning ? 'Generating…' : testCases.length > 0 ? 'Regenerate test cases' : 'Generate test cases'}
              </button>
            </div>
          )}
          {testCases.length === 0 && (
            <p className="empty-hint">
              No test cases for this story yet.
              {storiesWithTestsCount > 0 && (
                <>
                  {' '}
                  {storiesWithTestsCount} other
                  {storiesWithTestsCount === 1 ? ' story has' : ' stories have'}
                  {' '}
                  test cases in this BRD — generation is per story.
                </>
              )}
              {story.status === 'approved' ? (
                <>
                  {' '}
                  Click Generate test cases below, or use
                  {' '}
                  <strong>Generate test cases</strong>
                  {' '}
                  in Overview batch actions for all stories still missing tests.
                </>
              ) : (
                ' Approve this story first, then generate test cases.'
              )}
            </p>
          )}
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
                        disabled={formBusy}
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
