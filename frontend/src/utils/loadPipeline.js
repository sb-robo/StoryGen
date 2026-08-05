import * as brdApi from '../api/brds'
import * as featureApi from '../api/features'
import * as subFeatureApi from '../api/subFeatures'
import * as storyApi from '../api/stories'

export async function loadFullPipeline(brdId) {
  const featuresRes = await brdApi.listFeatures(brdId)
  const features = featuresRes.items

  const subFeaturesNested = await Promise.all(
    features.map(async (f) => {
      const res = await featureApi.listSubFeatures(f.id)
      return res.items.map((sf) => ({ ...sf, feature_id: f.id }))
    }),
  )
  const subFeatures = subFeaturesNested.flat()

  const storiesNested = await Promise.all(
    subFeatures.map(async (sf) => {
      const res = await subFeatureApi.listStories(sf.id)
      return res.items
    }),
  )
  const stories = storiesNested.flat()

  const testCasesNested = await Promise.all(
    stories.map(async (s) => {
      const res = await storyApi.listTestCases(s.id)
      return res.items.map((tc) => ({ ...tc, story_id: s.id }))
    }),
  )
  const testCases = testCasesNested.flat()

  const featureById = Object.fromEntries(features.map((f) => [f.id, f]))
  const subFeatureById = Object.fromEntries(subFeatures.map((sf) => [sf.id, sf]))
  const storyById = Object.fromEntries(stories.map((s) => [s.id, s]))

  return {
    features,
    subFeatures,
    stories,
    testCases,
    parents: { featureById, subFeatureById, storyById },
  }
}
