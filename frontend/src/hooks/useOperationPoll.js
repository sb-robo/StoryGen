import { useCallback, useEffect, useRef, useState } from 'react'
import { resolveUrl } from '../api/config'
import { api } from '../api/client'

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function pollOperation(statusUrl, { interval = 2000, onUpdate } = {}) {
  while (true) {
    const status = await api.get(resolveUrl(statusUrl))
    onUpdate?.(status)
    if (status.done) {
      if (status.status === 'failed') {
        throw new Error(status.error_message || 'Operation failed')
      }
      return status
    }
    await sleep(interval)
  }
}

export function useOperationPoll() {
  const [operation, setOperation] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const cancelledRef = useRef(false)

  const reset = useCallback(() => {
    cancelledRef.current = true
    setOperation(null)
    setError(null)
    setLoading(false)
  }, [])

  const startPoll = useCallback(async (op) => {
    cancelledRef.current = false
    setLoading(true)
    setError(null)
    setOperation(op)

    try {
      const finalStatus = await pollOperation(op.status_url, {
        onUpdate: (status) => {
          if (!cancelledRef.current) setOperation(status)
        },
      })
      if (cancelledRef.current) return null

      const result = await api.get(resolveUrl(finalStatus.result_url))
      setLoading(false)
      return result
    } catch (err) {
      if (!cancelledRef.current) {
        setError(err.message || 'Operation failed')
        setLoading(false)
      }
      return null
    }
  }, [])

  useEffect(() => () => {
    cancelledRef.current = true
  }, [])

  return { operation, error, loading, startPoll, reset }
}
