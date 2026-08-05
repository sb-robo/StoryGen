import { useCallback, useEffect, useMemo, useState } from 'react'
import { buildReviewQueue, computePipelineState } from '../utils/pipeline'
import { loadFullPipeline } from '../utils/loadPipeline'

export function useBrdPipeline(brdId, brdStatus) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const reload = useCallback(async () => {
    if (!brdId) return
    setLoading(true)
    setError(null)
    try {
      const result = await loadFullPipeline(brdId)
      setData(result)
    } catch (err) {
      setError(err.message || 'Failed to load pipeline data')
    } finally {
      setLoading(false)
    }
  }, [brdId])

  useEffect(() => {
    reload()
  }, [reload])

  const pipeline = useMemo(() => {
    if (!data) return null
    return computePipelineState({
      brdStatus,
      features: data.features,
      subFeatures: data.subFeatures,
      stories: data.stories,
      testCases: data.testCases,
    })
  }, [data, brdStatus])

  const reviewQueue = useMemo(() => {
    if (!data) return []
    return buildReviewQueue({
      features: data.features,
      subFeatures: data.subFeatures,
      stories: data.stories,
      testCases: data.testCases,
      parents: data.parents,
    })
  }, [data])

  return {
    ...data,
    pipeline,
    reviewQueue,
    loading,
    error,
    reload,
  }
}
