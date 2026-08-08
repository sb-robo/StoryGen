import * as featureApi from '../api/features'
import * as storyApi from '../api/stories'
import * as subFeatureApi from '../api/subFeatures'
import * as testCaseApi from '../api/testCases'
import { clarifyingApproveBlockMessage, ITEM_TYPES } from './pipeline'

/** Stable identity for a review-queue / selection item across types. */
export function queueItemKey(item) {
  if (!item?.entity) return null
  if (item.type === ITEM_TYPES.POINTS) return `${ITEM_TYPES.POINTS}:${item.entity.id}`
  return `${item.type}:${item.entity.id}`
}

export function filterReviewQueue(items, typeFilter = 'all', parentFilter = 'all') {
  let result = typeFilter === 'all' ? items : items.filter((item) => item.type === typeFilter)
  if (parentFilter && parentFilter !== 'all') {
    result = result.filter((item) => item.parentLabel === parentFilter)
  }
  return result
}

export function approveBlockReason(item) {
  if (item?.type === ITEM_TYPES.FEATURE) {
    return clarifyingApproveBlockMessage(item.entity)
  }
  return null
}

export async function approveQueueItem(item) {
  const block = approveBlockReason(item)
  if (block) throw new Error(block)

  const entity = item.entity
  switch (item.type) {
    case ITEM_TYPES.FEATURE:
      return featureApi.approveFeature(entity.id)
    case ITEM_TYPES.SUB_FEATURE:
      return subFeatureApi.approveSubFeature(entity.id)
    case ITEM_TYPES.STORY:
      return storyApi.approveStory(entity.id)
    case ITEM_TYPES.POINTS:
      return storyApi.approvePoints(entity.id)
    case ITEM_TYPES.TEST_CASE:
      return testCaseApi.approveTestCase(entity.id)
    default:
      throw new Error(`Unsupported review type: ${item.type}`)
  }
}

export async function rejectQueueItem(item) {
  if (item?.type === ITEM_TYPES.POINTS) {
    throw new Error('Story points cannot be rejected')
  }
  const entity = item.entity
  switch (item.type) {
    case ITEM_TYPES.FEATURE:
      return featureApi.rejectFeature(entity.id)
    case ITEM_TYPES.SUB_FEATURE:
      return subFeatureApi.rejectSubFeature(entity.id)
    case ITEM_TYPES.STORY:
      return storyApi.rejectStory(entity.id)
    case ITEM_TYPES.TEST_CASE:
      return testCaseApi.rejectTestCase(entity.id)
    default:
      throw new Error(`Unsupported review type: ${item.type}`)
  }
}

/** Next item after the current one in a filtered queue (prefer following, else previous). */
export function nextQueueItem(filtered, currentItem) {
  if (!filtered?.length || !currentItem) return null
  const currentKey = queueItemKey(currentItem)
  const index = filtered.findIndex((item) => queueItemKey(item) === currentKey)
  if (index < 0) return filtered[0] ?? null
  return filtered[index + 1] ?? filtered[index - 1] ?? null
}

/**
 * Approve items sequentially. Continues after individual failures.
 * @returns {{ ok: number, failed: Array<{ item: object, message: string }> }}
 */
export async function approveQueueItems(items) {
  const failed = []
  let ok = 0
  for (const item of items) {
    try {
      await approveQueueItem(item)
      ok += 1
    } catch (err) {
      failed.push({
        item,
        message: err?.message || 'Approve failed',
      })
    }
  }
  return { ok, failed }
}
