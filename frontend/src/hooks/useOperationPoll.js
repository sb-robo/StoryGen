import { useCallback, useEffect, useRef, useState } from 'react'
import { api, apiFetch } from '../api/client'
import { resolveUrl } from '../api/config'

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

/**
 * Watch a single operation via SSE (`GET /operations/stream`), falling back to HTTP polling.
 */
export async function watchOperation(operationId, statusUrl, { onUpdate } = {}) {
  try {
    return await watchOperationSse(operationId, { onUpdate })
  } catch {
    return pollOperation(statusUrl, { onUpdate })
  }
}

async function watchOperationSse(operationId, { onUpdate } = {}) {
  const response = await apiFetch(`/operations/stream?operation_ids=${encodeURIComponent(operationId)}`, {
    method: 'GET',
    headers: { Accept: 'text/event-stream' },
  })

  if (!response.ok || !response.body) {
    throw new Error('SSE unavailable')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let sawReady = false

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      let boundary = buffer.indexOf('\n\n')
      while (boundary !== -1) {
        const rawEvent = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)
        boundary = buffer.indexOf('\n\n')

        if (!rawEvent || rawEvent.startsWith(':')) continue

        let eventName = 'message'
        const dataLines = []
        for (const line of rawEvent.split('\n')) {
          if (line.startsWith('event:')) eventName = line.slice(6).trim()
          else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
        }
        if (dataLines.length === 0) continue

        let data
        try {
          data = JSON.parse(dataLines.join('\n'))
        } catch {
          continue
        }

        if (eventName === 'ready') {
          sawReady = true
          continue
        }
        if (eventName === 'timeout') {
          throw new Error('SSE idle timeout')
        }
        if (eventName !== 'operation' || data.operation_id !== operationId) continue

        onUpdate?.(data)
        if (data.done) {
          if (data.status === 'failed') {
            throw new Error(data.error_message || 'Operation failed')
          }
          return data
        }
      }
    }
  } finally {
    try {
      await reader.cancel()
    } catch {
      /* ignore */
    }
  }

  if (!sawReady) throw new Error('SSE stream closed unexpectedly')
  throw new Error('SSE ended before operation completed')
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
      const finalStatus = await watchOperation(op.operation_id, op.status_url, {
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
