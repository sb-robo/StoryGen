import { ITEM_TYPES } from './pipeline'
import { queueItemKey } from './reviewActions'

/**
 * Map a tracked job (resource + operation type) to a workspace selection target.
 */
export function resolveJobFocusTarget(focus, { features, subFeatures, stories, testCases, reviewQueue }) {
  const resourceType = focus.resourceType
  const resourceId = focus.resourceId
  const operationType = focus.operationType || ''

  if (!resourceType || resourceId == null) {
    return { tab: 'overview', item: null, queueFilter: null }
  }

  if (resourceType === 'brd') {
    if (operationType.includes('feature')) {
      const pending = reviewQueue.find((i) => i.type === ITEM_TYPES.FEATURE)
      return {
        tab: pending ? 'queue' : 'overview',
        item: pending || null,
        queueFilter: pending ? ITEM_TYPES.FEATURE : null,
      }
    }
    return { tab: 'overview', item: null, queueFilter: null }
  }

  if (resourceType === 'feature') {
    const feature = features.find((f) => f.id === resourceId)
    if (!feature) return { tab: 'overview', item: null, queueFilter: null }
    const pending =
      reviewQueue.find((i) => i.type === ITEM_TYPES.FEATURE && i.entity?.id === resourceId) ||
      reviewQueue.find((i) => i.type === ITEM_TYPES.SUB_FEATURE && i.entity?.feature_id === resourceId)
    if (pending) {
      return { tab: 'queue', item: pending, queueFilter: pending.type }
    }
    return {
      tab: 'overview',
      item: {
        id: feature.id,
        type: ITEM_TYPES.FEATURE,
        title: feature.title,
        parentLabel: '—',
        confidence: feature.confidence ?? null,
        status: feature.status,
        entity: feature,
      },
      queueFilter: null,
    }
  }

  if (resourceType === 'sub_feature') {
    const sf = subFeatures.find((s) => s.id === resourceId)
    if (!sf) return { tab: 'overview', item: null, queueFilter: null }
    const pending =
      reviewQueue.find((i) => i.type === ITEM_TYPES.SUB_FEATURE && i.entity?.id === resourceId) ||
      reviewQueue.find((i) => i.type === ITEM_TYPES.STORY && i.entity?.sub_feature_id === resourceId)
    if (pending) {
      return { tab: 'queue', item: pending, queueFilter: pending.type }
    }
    return {
      tab: 'overview',
      item: {
        id: sf.id,
        type: ITEM_TYPES.SUB_FEATURE,
        title: sf.title,
        parentLabel: 'Feature',
        confidence: sf.confidence ?? null,
        status: sf.status,
        entity: sf,
      },
      queueFilter: null,
    }
  }

  if (resourceType === 'story') {
    const story = stories.find((s) => s.id === resourceId)
    if (!story) return { tab: 'overview', item: null, queueFilter: null }

    if (operationType.includes('point')) {
      const pointsItem =
        reviewQueue.find((i) => i.type === ITEM_TYPES.POINTS && i.entity?.id === resourceId) || {
          id: `points-${story.id}`,
          type: ITEM_TYPES.POINTS,
          title: `${story.title} (points)`,
          parentLabel: 'Story',
          confidence: null,
          status: story.points_status,
          entity: story,
        }
      return {
        tab: story.points_status === 'pending_review' ? 'queue' : 'overview',
        item: pointsItem,
        queueFilter: story.points_status === 'pending_review' ? ITEM_TYPES.POINTS : null,
      }
    }

    if (operationType.includes('test')) {
      const pendingTc = reviewQueue.find(
        (i) => i.type === ITEM_TYPES.TEST_CASE && i.entity?.story_id === resourceId,
      )
      if (pendingTc) {
        return { tab: 'queue', item: pendingTc, queueFilter: ITEM_TYPES.TEST_CASE }
      }
      const firstTc = testCases.find((tc) => tc.story_id === resourceId)
      if (firstTc) {
        return {
          tab: 'overview',
          item: {
            id: firstTc.id,
            type: ITEM_TYPES.TEST_CASE,
            title: firstTc.title,
            parentLabel: story.title,
            confidence: firstTc.confidence ?? null,
            status: firstTc.status,
            entity: firstTc,
          },
          queueFilter: null,
        }
      }
    }

    const pendingStory = reviewQueue.find(
      (i) => i.type === ITEM_TYPES.STORY && i.entity?.id === resourceId,
    )
    if (pendingStory) {
      return { tab: 'queue', item: pendingStory, queueFilter: ITEM_TYPES.STORY }
    }
    return {
      tab: 'overview',
      item: {
        id: story.id,
        type: ITEM_TYPES.STORY,
        title: story.title,
        parentLabel: 'Sub-feature',
        confidence: story.confidence ?? null,
        status: story.status,
        entity: story,
      },
      queueFilter: null,
    }
  }

  // Fallback: try matching any queue item key
  const maybeKey = `${resourceType}:${resourceId}`
  const fromQueue = reviewQueue.find((i) => queueItemKey(i) === maybeKey)
  return { tab: fromQueue ? 'queue' : 'overview', item: fromQueue || null, queueFilter: null }
}

export function brdIdForJob(job) {
  if (job?.brdId != null) return job.brdId
  if (job?.resourceType === 'brd' && job.resourceId != null) return job.resourceId
  return null
}
