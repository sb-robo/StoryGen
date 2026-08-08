import { createContext, useCallback, useContext, useState } from 'react'
import { api } from '../api/client'
import { resolveUrl } from '../api/config'
import * as operationsApi from '../api/operations'
import { watchOperation } from '../hooks/useOperationPoll'

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
  const [jobFocus, setJobFocus] = useState(null)

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

  const clearJobFocus = useCallback(() => setJobFocus(null), [])

  const trackJob = useCallback(
    async (op, { label, brdId, onComplete } = {}) => {
      const jobId = makeJobId()
      const resolvedBrdId =
        brdId ??
        (op.resource_type === 'brd' ? op.resource_id : null) ??
        null
      const job = {
        id: jobId,
        operationId: op.operation_id,
        operationType: op.operation_type ?? null,
        resourceType: op.resource_type ?? null,
        resourceId: op.resource_id ?? null,
        label: label || 'Background job',
        brdId: resolvedBrdId,
        status: 'running',
        progress: op.progress || 'Queued…',
        error: null,
        startedAt: Date.now(),
        statusUrl: op.status_url,
        resultUrl: op.result_url,
      }
      setJobs((prev) => [job, ...prev])

      try {
        const finalStatus = await watchOperation(op.operation_id, op.status_url, {
          onUpdate: (status) => {
            let mapped = 'running'
            if (status.done) {
              if (status.status === 'failed') mapped = 'failed'
              else if (status.status === 'cancelled') mapped = 'cancelled'
              else mapped = 'succeeded'
            }
            const patch = {
              status: mapped,
              error: status.error_message ?? null,
              progress: status.progress ?? null,
            }
            if (status.resource_type != null) patch.resourceType = status.resource_type
            if (status.resource_id != null) patch.resourceId = status.resource_id
            if (status.operation_type != null) patch.operationType = status.operation_type
            if (resolvedBrdId != null) patch.brdId = resolvedBrdId
            else if (status.resource_type === 'brd' && status.resource_id != null) {
              patch.brdId = status.resource_id
            }
            updateJob(jobId, patch)
          },
        })

        if (finalStatus.status === 'cancelled') {
          updateJob(jobId, { status: 'cancelled', error: null })
          addToast({ type: 'info', message: `${label || 'Job'} cancelled` })
          return null
        }

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

  const cancelJob = useCallback(
    async (job) => {
      if (!job?.operationId) return
      try {
        await operationsApi.cancelOperation(job.operationId)
        // Status toast comes from the in-flight watchOperation when it sees cancelled.
        updateJob(job.id, { status: 'cancelled', error: null })
      } catch (err) {
        addToast({ type: 'error', message: err.message || 'Cancel failed' })
      }
    },
    [addToast, updateJob],
  )

  const retryJob = useCallback(
    async (job, { onComplete } = {}) => {
      if (!job?.operationId) return
      try {
        const op = await operationsApi.retryOperation(job.operationId)
        return await trackJob(op, {
          label: `Retry: ${job.label || 'Job'}`,
          brdId: job.brdId ?? (op.resource_type === 'brd' ? op.resource_id : null),
          onComplete,
        })
      } catch (err) {
        addToast({ type: 'error', message: err.message || 'Retry failed' })
        throw err
      }
    },
    [addToast, trackJob],
  )

  const clearFinished = useCallback(() => {
    setJobs((prev) => prev.filter((j) => j.status === 'running'))
  }, [])

  const runningCount = jobs.filter((j) => j.status === 'running').length

  const isJobRunningFor = useCallback(
    (resourceType, resourceId, operationType = null) => {
      if (resourceType == null || resourceId == null) return false
      const rid = Number(resourceId)
      return jobs.some(
        (j) =>
          j.status === 'running' &&
          j.resourceType === resourceType &&
          Number(j.resourceId) === rid &&
          (operationType == null || j.operationType === operationType),
      )
    },
    [jobs],
  )

  return (
    <JobsContext.Provider
      value={{
        jobs,
        runningCount,
        isJobRunningFor,
        drawerOpen,
        setDrawerOpen,
        trackJob,
        cancelJob,
        retryJob,
        clearFinished,
        jobFocus,
        setJobFocus,
        clearJobFocus,
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
