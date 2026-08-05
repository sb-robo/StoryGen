import * as brdApi from '../api/brds'
import * as featureApi from '../api/features'
import * as subFeatureApi from '../api/subFeatures'
import * as storyApi from '../api/stories'

export async function runBatchAction(actionId, { brdId, features, subFeatures, stories, runJob }) {
  switch (actionId) {
    case 'extract_features': {
      const label = features.length > 0 ? 'Regenerate features' : 'Extract features'
      await runJob(label, () => brdApi.extractFeatures(brdId))
      break
    }

    case 'batch_sub_features': {
      const approved = features.filter((f) => f.status === 'approved')
      for (const f of approved) {
        await runJob(`Generate sub-features: ${f.title}`, () => featureApi.generateSubFeatures(f.id))
      }
      break
    }

    case 'batch_stories': {
      const approved = subFeatures.filter((sf) => sf.status === 'approved')
      for (const sf of approved) {
        await runJob(`Generate stories: ${sf.title}`, () => subFeatureApi.generateStories(sf.id))
      }
      break
    }

    case 'batch_points': {
      const needsPoints = stories.filter((s) => s.status === 'approved' && !s.story_points && s.points_status !== 'approved')
      for (const s of needsPoints) {
        await runJob(`Estimate points: ${s.title}`, () => storyApi.estimatePoints(s.id))
      }
      break
    }

    case 'batch_tests': {
      const approved = stories.filter((s) => s.status === 'approved')
      for (const s of approved) {
        await runJob(`Generate test cases: ${s.title}`, () => storyApi.generateTestCases(s.id))
      }
      break
    }

    default:
      break
  }
}
