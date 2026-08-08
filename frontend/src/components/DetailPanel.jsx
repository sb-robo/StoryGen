import { useCallback, useEffect, useState } from 'react'
import * as featureApi from '../api/features'
import * as subFeatureApi from '../api/subFeatures'
import * as storyApi from '../api/stories'
import * as testCaseApi from '../api/testCases'
import { ITEM_TYPES } from '../utils/pipeline'
import { buildAncestorPath, nodeToItem } from '../utils/lineage'
import { Breadcrumb } from './Breadcrumb'
import { ClarifyingAnswersForm } from './ClarifyingAnswersForm'
import { EditModal } from './EditModal'
import { ReviewActions } from './ReviewCard'
import { StatusBadge } from './StatusBadge'
import { StoryDetailTabs } from './StoryDetailTabs'
import { SubFeatureTile } from './SubFeatureTile'

export function DetailPanel({ item, busy, onClose, onRefresh, onSelectItem, onRunJob, parents, wide }) {
  const [editItem, setEditItem] = useState(null)
  const [showRationale, setShowRationale] = useState(false)
  const [childCount, setChildCount] = useState(null)
  const itemKey = item ? `${item.type}:${item.id}` : null
  const [trackedItemKey, setTrackedItemKey] = useState(itemKey)
  const rootClassName = `detail-panel ${wide ? 'detail-panel-wide' : ''}`

  // Reset the fetched child count (sub-features/stories) whenever the selected
  // item changes, so a stale count from a previous selection can't leak in.
  if (trackedItemKey !== itemKey) {
    setTrackedItemKey(itemKey)
    setChildCount(null)
  }

  if (!item) {
    return (
      <aside className={`${rootClassName} detail-panel-empty`}>
        <p className="empty-hint">Select an item from the review queue or structure tree to see details.</p>
      </aside>
    )
  }

  const entity = item.entity
  const breadcrumbPath = parents ? buildAncestorPath(item, parents) : []
  const parentNode = breadcrumbPath.length > 1 ? breadcrumbPath[breadcrumbPath.length - 2] : null

  async function handleReview(action) {
    switch (item.type) {
      case ITEM_TYPES.FEATURE:
        if (action === 'approve') await featureApi.approveFeature(entity.id)
        else await featureApi.rejectFeature(entity.id)
        break
      case ITEM_TYPES.SUB_FEATURE:
        if (action === 'approve') await subFeatureApi.approveSubFeature(entity.id)
        else await subFeatureApi.rejectSubFeature(entity.id)
        break
      case ITEM_TYPES.STORY:
        if (action === 'approve') await storyApi.approveStory(entity.id)
        else await storyApi.rejectStory(entity.id)
        break
      case ITEM_TYPES.POINTS:
        await storyApi.approvePoints(entity.id)
        break
      case ITEM_TYPES.TEST_CASE:
        if (action === 'approve') await testCaseApi.approveTestCase(entity.id)
        else await testCaseApi.rejectTestCase(entity.id)
        break
      default:
        break
    }
    await onRefresh?.()
  }

  async function handleSave(updateFn, payload) {
    await updateFn(entity.id, payload)
    await onRefresh?.()
  }

  const isPending =
    item.type === ITEM_TYPES.POINTS
      ? entity.points_status === 'pending_review'
      : entity.status === 'pending_review'

  const nextHint = getNextHint(item.type, entity)
  const nextAction = getNextAction(item.type, entity, childCount)

  return (
    <aside className={rootClassName}>
      <div className="detail-panel-header">
        <div>
          <div className="detail-panel-nav">
            {parentNode && (
              <button
                type="button"
                className="btn btn-ghost btn-sm detail-back-btn"
                onClick={() => onSelectItem?.(nodeToItem(parentNode))}
              >
                ← Back
              </button>
            )}
            <Breadcrumb path={breadcrumbPath} onNavigate={onSelectItem} />
          </div>
          <h3>{entity.title}</h3>
          <div className="feature-detail-meta">
            <StatusBadge status={item.type === ITEM_TYPES.POINTS ? entity.points_status : entity.status} />
            {entity.confidence != null && (
              <span className="meta">Confidence: {(entity.confidence * 100).toFixed(0)}%</span>
            )}
          </div>
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onClose} aria-label="Close panel">
          ✕
        </button>
      </div>

      {isPending && (
        <div className="detail-panel-toolbar">
          <ReviewActions
            onApprove={() => handleReview('approve')}
            onReject={item.type === ITEM_TYPES.POINTS ? undefined : () => handleReview('reject')}
            onEdit={() => setEditItem(entity)}
            disabled={busy}
          />
        </div>
      )}

      <div className="detail-panel-body">
        {item.type === ITEM_TYPES.FEATURE && (
          <FeatureDetailContent
            feature={entity}
            showRationale={showRationale}
            onToggleRationale={() => setShowRationale(!showRationale)}
            onRefresh={onRefresh}
            busy={busy}
            onRunJob={onRunJob}
            onChildCountChange={setChildCount}
            onSelectSubFeature={(sf) =>
              onSelectItem?.({
                id: sf.id,
                type: ITEM_TYPES.SUB_FEATURE,
                title: sf.title,
                parentLabel: entity.title,
                confidence: sf.confidence,
                status: sf.status,
                entity: sf,
              })
            }
          />
        )}

        {item.type === ITEM_TYPES.SUB_FEATURE && (
          <SubFeatureDetailContent
            subFeature={entity}
            showRationale={showRationale}
            onToggleRationale={() => setShowRationale(!showRationale)}
            onRefresh={onRefresh}
            busy={busy}
            onRunJob={onRunJob}
            onChildCountChange={setChildCount}
            onSelectStory={(story) =>
              onSelectItem?.({
                id: story.id,
                type: ITEM_TYPES.STORY,
                title: story.title,
                parentLabel: entity.title,
                confidence: story.confidence,
                status: story.status,
                entity: story,
              })
            }
          />
        )}

        {(item.type === ITEM_TYPES.STORY || item.type === ITEM_TYPES.POINTS) && (
          <StoryDetailTabs
            story={entity}
            initialTab={item.type === ITEM_TYPES.POINTS ? 'points' : 'story'}
            onRefresh={onRefresh}
            busy={busy}
            onSelectTestCase={(tc) =>
              onSelectItem?.({
                id: tc.id,
                type: ITEM_TYPES.TEST_CASE,
                title: tc.title,
                parentLabel: entity.title,
                confidence: tc.confidence,
                status: tc.status,
                entity: tc,
              })
            }
          />
        )}

        {item.type === ITEM_TYPES.TEST_CASE && (
          <TestCaseDetailContent entity={entity} showRationale={showRationale} onToggleRationale={() => setShowRationale(!showRationale)} />
        )}
      </div>

      {(nextHint || nextAction) && (
        <div className="detail-panel-footer">
          {nextHint && <p className="next-hint">{nextHint}</p>}
          {nextAction && onRunJob && (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => onRunJob(nextAction.label, nextAction.run)}
              disabled={busy}
            >
              {nextAction.buttonLabel}
            </button>
          )}
        </div>
      )}

      {editItem && item.type === ITEM_TYPES.FEATURE && (
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
          onSave={(payload) => handleSave(featureApi.updateFeature, payload)}
          onClose={() => setEditItem(null)}
        />
      )}

      {editItem && item.type === ITEM_TYPES.SUB_FEATURE && (
        <EditModal
          title="Edit sub-feature"
          fields={[
            { name: 'title', label: 'Title', value: editItem.title },
            { name: 'description', label: 'Description', type: 'textarea', value: editItem.description },
          ]}
          onSave={(payload) => handleSave(subFeatureApi.updateSubFeature, payload)}
          onClose={() => setEditItem(null)}
        />
      )}

      {editItem && item.type === ITEM_TYPES.STORY && (
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
          onSave={(payload) => handleSave(storyApi.updateStory, payload)}
          onClose={() => setEditItem(null)}
        />
      )}

      {editItem && item.type === ITEM_TYPES.TEST_CASE && (
        <EditModal
          title="Edit test case"
          fields={[
            { name: 'title', label: 'Title', value: editItem.title },
            { name: 'steps', label: 'Steps', type: 'textarea', value: editItem.steps },
            { name: 'expected_result', label: 'Expected result', type: 'textarea', value: editItem.expected_result },
            { name: 'test_type', label: 'Type (happy_path / edge_case / negative)', value: editItem.test_type },
          ]}
          onSave={(payload) => handleSave(testCaseApi.updateTestCase, payload)}
          onClose={() => setEditItem(null)}
        />
      )}
    </aside>
  )
}

function FeatureDetailContent({ feature, showRationale, onToggleRationale, onRefresh, busy, onRunJob, onSelectSubFeature, onChildCountChange }) {
  const [subFeatures, setSubFeatures] = useState([])
  const [generating, setGenerating] = useState(false)

  const load = useCallback(async () => {
    const res = await featureApi.listSubFeatures(feature.id)
    setSubFeatures(res.items)
    onChildCountChange?.(res.items.length)
  }, [feature.id, onChildCountChange])

  useEffect(() => {
    load()
  }, [load])

  async function handleGenerateSubFeatures() {
    if (!onRunJob) return
    setGenerating(true)
    try {
      const label = subFeatures.length > 0 ? `Regenerate sub-features: ${feature.title}` : `Generate sub-features: ${feature.title}`
      await onRunJob(label, () => featureApi.generateSubFeatures(feature.id))
      await load()
    } finally {
      setGenerating(false)
    }
  }

  const canGenerate = feature.status === 'approved' && onRunJob
  const isBusy = busy || generating

  return (
    <>
      <section className="detail-block">
        <h4>Description</h4>
        <p className="review-description">{feature.description}</p>
      </section>

      {feature.clarifying_questions?.length > 0 && (
        <section className="detail-block">
          <h4>Clarifying questions</h4>
          <ClarifyingAnswersForm feature={feature} onSaved={onRefresh} disabled={isBusy} />
        </section>
      )}

      {feature.rationale && (
        <section className="detail-block">
          <button type="button" className="btn btn-ghost btn-sm" onClick={onToggleRationale}>
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

      <section className="detail-block">
        <div className="section-toolbar">
          <h4>Sub-features {subFeatures.length > 0 ? `(${subFeatures.length})` : ''}</h4>
          {canGenerate && (
            <button type="button" className="btn btn-primary btn-sm" onClick={handleGenerateSubFeatures} disabled={isBusy}>
              {subFeatures.length > 0 ? 'Regenerate sub-features' : 'Generate sub-features'}
            </button>
          )}
        </div>
        {!canGenerate && feature.status !== 'approved' && (
          <p className="empty-hint">Approve this feature to generate sub-features.</p>
        )}
        {canGenerate && subFeatures.length === 0 && (
          <p className="empty-hint">No sub-features yet.</p>
        )}
        {subFeatures.length > 0 && (
          <div className="feature-grid">
            {subFeatures.map((sf) => (
              <SubFeatureTile key={sf.id} subFeature={sf} onClick={() => onSelectSubFeature(sf)} />
            ))}
          </div>
        )}
      </section>
    </>
  )
}

function SubFeatureDetailContent({ subFeature, showRationale, onToggleRationale, busy, onRunJob, onSelectStory, onChildCountChange }) {
  const [stories, setStories] = useState([])
  const [generating, setGenerating] = useState(false)

  const load = useCallback(async () => {
    const res = await subFeatureApi.listStories(subFeature.id)
    setStories(res.items)
    onChildCountChange?.(res.items.length)
  }, [subFeature.id, onChildCountChange])

  useEffect(() => {
    load()
  }, [load])

  async function handleGenerateStories() {
    if (!onRunJob) return
    setGenerating(true)
    try {
      const label = stories.length > 0 ? `Regenerate stories: ${subFeature.title}` : `Generate stories: ${subFeature.title}`
      await onRunJob(label, () => subFeatureApi.generateStories(subFeature.id))
      await load()
    } finally {
      setGenerating(false)
    }
  }

  const canGenerate = subFeature.status === 'approved' && onRunJob
  const isBusy = busy || generating

  return (
    <>
      <section className="detail-block">
        <h4>Description</h4>
        <p className="review-description">{subFeature.description}</p>
      </section>

      {subFeature.rationale && (
        <section className="detail-block">
          <button type="button" className="btn btn-ghost btn-sm" onClick={onToggleRationale}>
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

      <section className="detail-block">
        <div className="section-toolbar">
          <h4>Stories {stories.length > 0 ? `(${stories.length})` : ''}</h4>
          {canGenerate && (
            <button type="button" className="btn btn-primary btn-sm" onClick={handleGenerateStories} disabled={isBusy}>
              {stories.length > 0 ? 'Regenerate stories' : 'Generate stories'}
            </button>
          )}
        </div>
        {!canGenerate && subFeature.status !== 'approved' && (
          <p className="empty-hint">Approve this sub-feature to generate stories.</p>
        )}
        {canGenerate && stories.length === 0 && (
          <p className="empty-hint">No stories yet.</p>
        )}
        {stories.length > 0 && (
          <div className="feature-grid">
            {stories.map((story) => (
              <button key={story.id} type="button" className="feature-tile" onClick={() => onSelectStory(story)}>
                <div className="feature-tile-top">
                  <StatusBadge status={story.status} />
                  {story.confidence != null && (
                    <span className="feature-tile-confidence">{(story.confidence * 100).toFixed(0)}%</span>
                  )}
                </div>
                <h4 className="feature-tile-title">{story.title}</h4>
                <p className="feature-tile-preview">{story.description}</p>
                <div className="feature-tile-footer">
                  <span className="meta">
                    Story {story.status === 'approved' ? '✓' : '○'} · Points {story.points_status === 'approved' ? '✓' : story.points_status ? '⏳' : '○'}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>
    </>
  )
}

function TestCaseDetailContent({ entity, showRationale, onToggleRationale }) {
  return (
    <>
      <section className="detail-block">
        <h4>Steps</h4>
        <p className="review-description">{entity.steps}</p>
      </section>
      <section className="detail-block">
        <h4>Expected result</h4>
        <p className="review-description">{entity.expected_result}</p>
      </section>
      <p className="meta">Type: {entity.test_type}</p>
      {entity.rationale && (
        <section className="detail-block">
          <button type="button" className="btn btn-ghost btn-sm" onClick={onToggleRationale}>
            {showRationale ? 'Hide rationale' : 'Show rationale'}
          </button>
          {showRationale && <p className="rationale">{entity.rationale}</p>}
        </section>
      )}
    </>
  )
}

function getNextHint(type, entity) {
  switch (type) {
    case ITEM_TYPES.FEATURE:
      return entity.status === 'approved' ? null : 'After approve: generate sub-features'
    case ITEM_TYPES.SUB_FEATURE:
      return entity.status === 'approved' ? null : 'After approve: generate stories'
    case ITEM_TYPES.STORY:
      return entity.status === 'approved' ? 'Next: estimate points, then generate test cases' : 'After approve: estimate points'
    case ITEM_TYPES.POINTS:
      return 'After approve: generate test cases if not done'
    default:
      return null
  }
}

function getNextAction(type, entity, childCount) {
  const hasChildren = childCount > 0
  switch (type) {
    case ITEM_TYPES.FEATURE:
      if (entity.status !== 'approved') return null
      return {
        buttonLabel: hasChildren ? 'Regenerate sub-features' : 'Generate sub-features',
        label: `${hasChildren ? 'Regenerate' : 'Generate'} sub-features: ${entity.title}`,
        run: () => featureApi.generateSubFeatures(entity.id),
      }
    case ITEM_TYPES.SUB_FEATURE:
      if (entity.status !== 'approved') return null
      return {
        buttonLabel: hasChildren ? 'Regenerate stories' : 'Generate stories',
        label: `${hasChildren ? 'Regenerate' : 'Generate'} stories: ${entity.title}`,
        run: () => subFeatureApi.generateStories(entity.id),
      }
    default:
      return null
  }
}
