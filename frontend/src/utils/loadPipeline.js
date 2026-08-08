import * as brdApi from '../api/brds'

export async function loadFullPipeline(brdId) {
  const tree = await brdApi.getPipeline(brdId)
  const features = tree.features ?? []
  const subFeatures = tree.sub_features ?? []
  const stories = tree.stories ?? []
  const testCases = tree.test_cases ?? []

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
