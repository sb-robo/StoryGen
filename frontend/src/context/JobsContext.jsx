import { createContext, useCallback, useContext, useState } from 'react'
import { api } from '../api/client'
import { resolveUrl } from '../api/config'
import { pollOperation } from '../hooks/useOperationPoll'

const JobsContext = createContext(null)

let jobCounter = 0

function makeJobId() {
  jobCounter += 1
  return `job-${Date.now()}-${jobCounter}`
}

export function JobsProvider({ children }) {
  const [jobs, setJobs] = useState([])
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [toasts, setToasts] = useState([])

  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const addToast = useCallback(
    (toast) => {
      const id = makeJobId()
      setToasts((prev) => [...prev, { id, ...toast }])
      setTimeout(() => dismissToast(id), toast.duration ?? 5000)
      return id
    },
    [dismissToast],
  )

  const updateJob = useCallback((jobId, patch) => {
    setJobs((prev) => prev.map((j) => (j.id === jobId ? { ...j, ...patch } : j)))
  }, [])

  const trackJob = useCallback(
    async (op, { label, brdId, onComplete } = {}) => {
      const jobId = makeJobId()
      const job = {
        id: jobId,
        operationId: op.operation_id,
        label: label || 'Background job',
        brdId: brdId ?? null,
        status: 'running',
        error: null,
        startedAt: Date.now(),
        statusUrl: op.status_url,
        resultUrl: op.result_url,
      }
      setJobs((prev) => [job, ...prev])

      try {
        const finalStatus = await pollOperation(op.status_url, {
          onUpdate: (status) => {
            updateJob(jobId, {
              status: status.done ? (status.status === 'failed' ? 'failed' : 'succeeded') : 'running',
              error: status.error_message ?? null,
            })
          },
        })

        updateJob(jobId, { status: 'succeeded', error: null })
        addToast({ type: 'success', message: `${label || 'Job'} completed` })

        let result = null
        if (finalStatus.result_url) {
          result = await api.get(resolveUrl(finalStatus.result_url))
        }
        onComplete?.(result)
        return result
      } catch (err) {
        const message = err.message || 'Operation failed'
        updateJob(jobId, { status: 'failed', error: message })
        addToast({ type: 'error', message: `${label || 'Job'} failed: ${message}` })
        throw err
      }
    },
    [addToast, updateJob],
  )

  const clearFinished = useCallback(() => {
    setJobs((prev) => prev.filter((j) => j.status === 'running'))
  }, [])

  const runningCount = jobs.filter((j) => j.status === 'running').length

  return (
    <JobsContext.Provider
      value={{
        jobs,
        runningCount,
        drawerOpen,
        setDrawerOpen,
        trackJob,
        clearFinished,
        toasts,
        dismissToast,
      }}
    >
      {children}
    </JobsContext.Provider>
  )
}

export function useJobs() {
  const ctx = useContext(JobsContext)
  if (!ctx) throw new Error('useJobs must be used within JobsProvider')
  return ctx
}
