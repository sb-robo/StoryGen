import * as brdApi from '../api/brds'
import * as featureApi from '../api/features'

async function trackBatchOps(batch, labelPrefix, runJob) {
  const ops = batch?.operations ?? []
  if (ops.length === 0) return
  await Promise.all(
    ops.map((op, index) =>
      runJob(`${labelPrefix} (${index + 1}/${ops.length})`, async () => op),
    ),
  )
}

export async function runBatchAction(actionId, { brdId, features, runJob }) {
  switch (actionId) {
    case 'extract_features': {
      const label = features.length > 0 ? 'Regenerate features' : 'Extract features'
      await runJob(label, () => featureApi.extractFeatures(brdId))
      break
    }

    case 'batch_sub_features': {
      const batch = await brdApi.generateAllSubFeatures(brdId)
      await trackBatchOps(batch, 'Generate sub-features', runJob)
      break
    }

    case 'batch_stories': {
      const batch = await brdApi.generateAllStories(brdId)
      await trackBatchOps(batch, 'Generate stories', runJob)
      break
    }

    case 'batch_points': {
      const batch = await brdApi.estimateAllPoints(brdId)
      await trackBatchOps(batch, 'Estimate points', runJob)
      break
    }

    case 'batch_tests': {
      const batch = await brdApi.generateAllTestCases(brdId)
      await trackBatchOps(batch, 'Generate test cases', runJob)
      break
    }

    default:
      break
  }
}
