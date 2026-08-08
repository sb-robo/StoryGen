export const PIPELINE_STAGES = [
  { id: 'parse', label: 'Parse' },
  { id: 'features', label: 'Features' },
  { id: 'sub_features', label: 'Sub-features' },
  { id: 'stories', label: 'Stories' },
  { id: 'points', label: 'Points' },
  { id: 'tests', label: 'Tests' },
  { id: 'export', label: 'Export' },
]

export const ITEM_TYPES = {
  FEATURE: 'feature',
  SUB_FEATURE: 'sub_feature',
  STORY: 'story',
  POINTS: 'points',
  TEST_CASE: 'test_case',
}

function countByStatus(items) {
  const counts = { total: items.length, approved: 0, pending_review: 0, rejected: 0, other: 0 }
  for (const item of items) {
    if (item.status === 'approved') counts.approved += 1
    else if (item.status === 'pending_review') counts.pending_review += 1
    else if (item.status === 'rejected') counts.rejected += 1
    else counts.other += 1
  }
  return counts
}

function stageStatus(counts, { requiresItems = true, pendingField = 'pending_review' } = {}) {
  if (requiresItems && counts.total === 0) return 'not_started'
  if (counts[pendingField] > 0) return 'needs_review'
  if (counts.approved === counts.total && counts.total > 0) return 'complete'
  if (counts.total > 0) return 'in_progress'
  return 'not_started'
}

export function computePipelineState({ brdStatus, features, subFeatures, stories, testCases }) {
  const featureCounts = countByStatus(features)
  const subFeatureCounts = countByStatus(subFeatures)
  const storyCounts = countByStatus(stories)

  const pointsItems = stories.filter((s) => s.story_points != null || s.points_status)
  const pointsPending = stories.filter((s) => s.points_status === 'pending_review')
  const pointsCounts = {
    total: pointsItems.length,
    approved: pointsItems.filter((s) => s.points_status === 'approved').length,
    pending_review: pointsPending.length,
    rejected: 0,
    other: pointsItems.filter((s) => !s.points_status || (s.points_status !== 'approved' && s.points_status !== 'pending_review')).length,
  }

  const testCaseCounts = countByStatus(testCases)

  const parseComplete = brdStatus === 'parsed'
  const parseFailed = brdStatus === 'parse_failed'

  const stages = {
    parse: {
      id: 'parse',
      status: parseFailed ? 'failed' : parseComplete ? 'complete' : brdStatus === 'parsing' ? 'in_progress' : 'not_started',
      counts: null,
      pending: 0,
    },
    features: {
      id: 'features',
      status: !parseComplete ? 'locked' : stageStatus(featureCounts),
      counts: featureCounts,
      pending: featureCounts.pending_review,
    },
    sub_features: {
      id: 'sub_features',
      status:
        featureCounts.approved === 0
          ? 'locked'
          : subFeatureCounts.total === 0
            ? 'not_started'
            : stageStatus(subFeatureCounts),
      counts: subFeatureCounts,
      pending: subFeatureCounts.pending_review,
      lockReason: featureCounts.approved === 0 ? 'Approve at least one feature first' : null,
    },
    stories: {
      id: 'stories',
      status:
        subFeatureCounts.approved === 0
          ? 'locked'
          : storyCounts.total === 0
            ? 'not_started'
            : stageStatus(storyCounts),
      counts: storyCounts,
      pending: storyCounts.pending_review,
      lockReason: subFeatureCounts.approved === 0 ? 'Approve sub-features first' : null,
    },
    points: {
      id: 'points',
      status:
        storyCounts.approved === 0
          ? 'locked'
          : pointsCounts.total === 0
            ? 'not_started'
            : pointsCounts.pending_review > 0
              ? 'needs_review'
              : pointsCounts.approved === pointsCounts.total
                ? 'complete'
                : 'in_progress',
      counts: pointsCounts,
      pending: pointsCounts.pending_review,
      lockReason: storyCounts.approved === 0 ? 'Approve stories first' : null,
    },
    tests: {
      id: 'tests',
      status:
        storyCounts.approved === 0
          ? 'locked'
          : testCaseCounts.total === 0
            ? 'not_started'
            : stageStatus(testCaseCounts),
      counts: testCaseCounts,
      pending: testCaseCounts.pending_review,
      lockReason: storyCounts.approved === 0 ? 'Approve stories first' : null,
    },
    export: {
      id: 'export',
      status: storyCounts.approved === 0 ? 'locked' : 'ready',
      counts: { total: storyCounts.approved, approved: storyCounts.approved },
      pending: 0,
      lockReason: storyCounts.approved === 0 ? 'Approve at least one story first' : null,
    },
  }

  return { stages, featureCounts, subFeatureCounts, storyCounts, testCaseCounts, pointsCounts }
}

export function buildReviewQueue({ features, subFeatures, stories, testCases, parents }) {
  const queue = []
  const { featureById, subFeatureById, storyById } = parents

  for (const feature of features) {
    if (feature.status === 'pending_review') {
      queue.push({
        id: feature.id,
        type: ITEM_TYPES.FEATURE,
        title: feature.title,
        parentLabel: '—',
        pathLabel: null,
        confidence: feature.confidence,
        status: feature.status,
        entity: feature,
      })
    }
  }

  for (const sf of subFeatures) {
    if (sf.status === 'pending_review') {
      const parent = featureById[sf.feature_id]
      queue.push({
        id: sf.id,
        type: ITEM_TYPES.SUB_FEATURE,
        title: sf.title,
        parentLabel: parent?.title ?? 'Feature',
        pathLabel: parent?.title ?? null,
        confidence: sf.confidence,
        status: sf.status,
        entity: sf,
      })
    }
  }

  for (const story of stories) {
    const subFeature = subFeatureById[story.sub_feature_id]
    const feature = subFeature ? featureById[subFeature.feature_id] : null
    const storyPath = [feature?.title, subFeature?.title].filter(Boolean).join(' › ')

    if (story.status === 'pending_review') {
      queue.push({
        id: story.id,
        type: ITEM_TYPES.STORY,
        title: story.title,
        parentLabel: subFeature?.title ?? 'Sub-feature',
        pathLabel: storyPath || null,
        confidence: story.confidence,
        status: story.status,
        entity: story,
      })
    }
    if (story.points_status === 'pending_review') {
      queue.push({
        id: `points-${story.id}`,
        type: ITEM_TYPES.POINTS,
        title: `${story.title} (points)`,
        parentLabel: subFeature?.title ?? 'Sub-feature',
        pathLabel: storyPath || null,
        confidence: null,
        status: story.points_status,
        entity: story,
      })
    }
  }

  for (const tc of testCases) {
    if (tc.status === 'pending_review') {
      const story = storyById[tc.story_id]
      const subFeature = story ? subFeatureById[story.sub_feature_id] : null
      const feature = subFeature ? featureById[subFeature.feature_id] : null
      const tcPath = [feature?.title, subFeature?.title, story?.title].filter(Boolean).join(' › ')

      queue.push({
        id: tc.id,
        type: ITEM_TYPES.TEST_CASE,
        title: tc.title,
        parentLabel: story?.title ?? 'Story',
        pathLabel: tcPath || null,
        confidence: tc.confidence,
        status: tc.status,
        entity: tc,
      })
    }
  }

  return queue
}

export function typeLabel(type) {
  switch (type) {
    case ITEM_TYPES.FEATURE:
      return 'Feature'
    case ITEM_TYPES.SUB_FEATURE:
      return 'Sub-feature'
    case ITEM_TYPES.STORY:
      return 'Story'
    case ITEM_TYPES.POINTS:
      return 'Points'
    case ITEM_TYPES.TEST_CASE:
      return 'Test case'
    default:
      return type
  }
}

function pct(approved, total) {
  if (!total) return 0
  return Math.round((approved / total) * 100)
}

export function getProgressLabel(pipeline) {
  if (!pipeline?.stages) return null
  const { stages } = pipeline
  const parts = []

  if (stages.features.counts?.total > 0) {
    parts.push(`Features ${pct(stages.features.counts.approved, stages.features.counts.total)}%`)
  }
  if (stages.stories.counts?.total > 0) {
    parts.push(`Stories ${pct(stages.stories.counts.approved, stages.stories.counts.total)}%`)
  }
  if (stages.tests.counts?.total > 0) {
    parts.push(`Tests ${pct(stages.tests.counts.approved, stages.tests.counts.total)}%`)
  }

  return parts.length > 0 ? parts.join(' · ') : null
}

export function getTotalPending(pipeline) {
  if (!pipeline?.stages) return 0
  const { stages } = pipeline
  return (
    (stages.features.pending ?? 0) +
    (stages.sub_features.pending ?? 0) +
    (stages.stories.pending ?? 0) +
    (stages.points.pending ?? 0) +
    (stages.tests.pending ?? 0)
  )
}

export function unansweredClarifyingCount(feature) {
  if (!feature) return 0
  const questionCount = feature.clarifying_questions?.length ?? 0
  const answerCount = feature.clarifying_answers?.length ?? 0
  return Math.max(0, questionCount - answerCount)
}

export function clarifyingApproveBlockMessage(feature) {
  const unanswered = unansweredClarifyingCount(feature)
  if (unanswered <= 0) return null
  return `Answer clarifying questions before approving (${unanswered} unanswered).`
}

/** Copy for regenerate confirmations — approved/rejected children are kept. */
export function regenerateConfirmMessage(childLabel = 'items') {
  return (
    `This replaces draft and pending_review ${childLabel}. ` +
    `Approved and rejected ${childLabel} are kept.`
  )
}

export function getBlockers(features) {
  const blockers = []
  for (const feature of features) {
    const unanswered = unansweredClarifyingCount(feature)
    if (unanswered > 0) {
      blockers.push({
        id: feature.id,
        featureTitle: feature.title,
        unanswered,
      })
    }
  }
  return blockers
}

export function getSuggestedStep({ brdStatus, pipeline, reviewQueue }) {
  if (brdStatus === 'parsing') {
    return { label: 'Parsing document…', action: null, stageId: 'parse' }
  }
  if (brdStatus === 'parse_failed') {
    return { label: 'Parse failed — re-upload or reparse', action: null, stageId: 'parse' }
  }
  if (brdStatus !== 'parsed') {
    return { label: 'Waiting for parse to complete', action: null, stageId: 'parse' }
  }

  if (reviewQueue.length > 0) {
    return {
      label: `Review ${reviewQueue.length} pending item${reviewQueue.length !== 1 ? 's' : ''}`,
      action: 'review',
      stageId: stageForQueueItem(reviewQueue[0].type),
    }
  }

  if (!pipeline?.stages) {
    return { label: 'Loading pipeline…', action: null, stageId: 'features' }
  }

  const { stages } = pipeline

  if (stages.features.counts?.total === 0) {
    return { label: 'Extract features from BRD', action: 'extract_features', stageId: 'features' }
  }

  if (stages.sub_features.counts?.total === 0 && stages.sub_features.status !== 'locked') {
    return { label: 'Generate sub-features for approved features', action: 'batch_sub_features', stageId: 'sub_features' }
  }

  if (stages.stories.counts?.total === 0 && stages.stories.status !== 'locked') {
    return { label: 'Generate stories for approved sub-features', action: 'batch_stories', stageId: 'stories' }
  }

  if (stages.points.status === 'not_started' && stages.stories.counts?.approved > 0) {
    return { label: 'Estimate story points for approved stories', action: 'batch_points', stageId: 'points' }
  }

  if (stages.tests.counts?.total === 0 && stages.tests.status !== 'locked') {
    return { label: 'Generate test cases for approved stories', action: 'batch_tests', stageId: 'tests' }
  }

  if (stages.export.status !== 'locked') {
    return {
      label: 'Export approved stories as CSV',
      action: 'export_csv',
      stageId: 'export',
    }
  }

  return { label: 'Pipeline complete — ready for export', action: null, stageId: 'export' }
}

function stageForQueueItem(type) {
  switch (type) {
    case ITEM_TYPES.FEATURE:
      return 'features'
    case ITEM_TYPES.SUB_FEATURE:
      return 'sub_features'
    case ITEM_TYPES.STORY:
      return 'stories'
    case ITEM_TYPES.POINTS:
      return 'points'
    case ITEM_TYPES.TEST_CASE:
      return 'tests'
    default:
      return 'features'
  }
}

export function getBatchActions({ pipeline, features, subFeatures, stories }) {
  const actions = []
  const { stages } = pipeline

  if (stages.features.counts?.total === 0) {
    actions.push({ id: 'extract_features', label: 'Extract features', count: null })
    return actions
  }

  const approvedFeatures = features.filter((f) => f.status === 'approved')
  if (approvedFeatures.length > 0 && stages.sub_features.counts?.total === 0) {
    actions.push({
      id: 'batch_sub_features',
      label: 'Generate sub-features',
      count: approvedFeatures.length,
    })
  }

  const approvedSubFeatures = subFeatures.filter((sf) => sf.status === 'approved')
  if (approvedSubFeatures.length > 0 && stages.stories.counts?.total === 0) {
    actions.push({
      id: 'batch_stories',
      label: 'Generate stories',
      count: approvedSubFeatures.length,
    })
  }

  const needsPoints = stories.filter((s) => s.status === 'approved' && !s.story_points && s.points_status !== 'approved')
  if (needsPoints.length > 0) {
    actions.push({
      id: 'batch_points',
      label: 'Estimate points',
      count: needsPoints.length,
    })
  }

  const approvedStories = stories.filter((s) => s.status === 'approved')
  if (approvedStories.length > 0 && stages.tests.counts?.total === 0) {
    actions.push({
      id: 'batch_tests',
      label: 'Generate test cases',
      count: approvedStories.length,
    })
  }

  if (approvedStories.length > 0 && stages.export?.status !== 'locked') {
    actions.push({
      id: 'export_csv',
      label: 'Export CSV',
      count: approvedStories.length,
    })
    actions.push({
      id: 'export_jira',
      label: 'Export Jira CSV',
      count: approvedStories.length,
    })
  }

  return actions
}
