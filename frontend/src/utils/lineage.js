import { ITEM_TYPES } from './pipeline'

function toNode(type, entity) {
  return {
    type,
    id: entity.id,
    title: entity.title,
    status: type === ITEM_TYPES.POINTS ? entity.points_status : entity.status,
    entity,
  }
}

/**
 * Full ancestor chain for an item, ending with the item itself.
 * e.g. Test case -> [Feature, Sub-feature, Story, Test case]
 */
export function buildAncestorPath(item, parents) {
  if (!item || !parents) return []
  const { featureById, subFeatureById, storyById } = parents
  const entity = item.entity
  const path = []

  switch (item.type) {
    case ITEM_TYPES.FEATURE:
      path.push(toNode(ITEM_TYPES.FEATURE, entity))
      break

    case ITEM_TYPES.SUB_FEATURE: {
      const feature = featureById[entity.feature_id]
      if (feature) path.push(toNode(ITEM_TYPES.FEATURE, feature))
      path.push(toNode(ITEM_TYPES.SUB_FEATURE, entity))
      break
    }

    case ITEM_TYPES.STORY:
    case ITEM_TYPES.POINTS: {
      const subFeature = subFeatureById[entity.sub_feature_id]
      const feature = subFeature ? featureById[subFeature.feature_id] : null
      if (feature) path.push(toNode(ITEM_TYPES.FEATURE, feature))
      if (subFeature) path.push(toNode(ITEM_TYPES.SUB_FEATURE, subFeature))
      path.push(toNode(ITEM_TYPES.STORY, entity))
      break
    }

    case ITEM_TYPES.TEST_CASE: {
      const story = storyById[entity.story_id]
      const subFeature = story ? subFeatureById[story.sub_feature_id] : null
      const feature = subFeature ? featureById[subFeature.feature_id] : null
      if (feature) path.push(toNode(ITEM_TYPES.FEATURE, feature))
      if (subFeature) path.push(toNode(ITEM_TYPES.SUB_FEATURE, subFeature))
      if (story) path.push(toNode(ITEM_TYPES.STORY, story))
      path.push(toNode(ITEM_TYPES.TEST_CASE, entity))
      break
    }

    default:
      break
  }

  return path
}

/** Human-readable "Feature › Sub-feature › Story" string, excluding the item itself. */
export function buildPathLabel(item, parents) {
  const path = buildAncestorPath(item, parents)
  return path
    .slice(0, -1)
    .map((n) => n.title)
    .join(' › ')
}

export function nodeToItem(node) {
  return {
    id: node.id,
    type: node.type,
    title: node.title,
    parentLabel: '—',
    confidence: node.entity.confidence ?? null,
    status: node.status,
    entity: node.entity,
  }
}
