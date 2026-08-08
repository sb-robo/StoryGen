import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import * as operationsApi from '../api/operations'
import { useAuth } from '../auth/useAuth'
import { StatusBadge } from '../components/StatusBadge'

const STATUS_OPTIONS = [
  '',
  'pending',
  'running',
  'succeeded',
  'failed',
  'cancelled',
]

const TYPE_OPTIONS = [
  '',
  'brd_upload',
  'brd_reparse',
  'feature_extraction',
  'sub_feature_generation',
  'story_generation',
  'story_point_estimation',
  'test_case_generation',
]

function formatType(value) {
  return (value || '').replaceAll('_', ' ')
}

function formatWhen(value) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

const EMPTY_FILTERS = {
  status: '',
  operation_type: '',
  user_id: '',
  resource_id: '',
}

export function AdminOperationsPage() {
  const { user } = useAuth()
  const isAdmin = Boolean(user?.is_admin)
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [applied, setApplied] = useState(EMPTY_FILTERS)
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionId, setActionId] = useState(null)

  useEffect(() => {
    if (!isAdmin) return undefined
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const params = { page, page_size: 20 }
        if (applied.status) params.status = applied.status
        if (applied.operation_type) params.operation_type = applied.operation_type
        if (applied.user_id) params.user_id = Number(applied.user_id)
        if (applied.resource_id) params.resource_id = Number(applied.resource_id)
        const result = await operationsApi.listOperations(params)
        if (!cancelled) setData(result)
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load operations')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [page, applied, isAdmin])

  if (!isAdmin) {
    return <Navigate to="/" replace />
  }

  function applyFilters(e) {
    e.preventDefault()
    setPage(1)
    setApplied({ ...filters })
  }

  function resetFilters() {
    setFilters(EMPTY_FILTERS)
    setApplied(EMPTY_FILTERS)
    setPage(1)
  }

  async function handleCancel(operationId) {
    setActionId(operationId)
    setError('')
    try {
      await operationsApi.cancelOperation(operationId)
      setApplied((prev) => ({ ...prev }))
    } catch (err) {
      setError(err.message || 'Cancel failed')
    } finally {
      setActionId(null)
    }
  }

  async function handleRetry(operationId) {
    setActionId(operationId)
    setError('')
    try {
      await operationsApi.retryOperation(operationId)
      setApplied((prev) => ({ ...prev }))
    } catch (err) {
      setError(err.message || 'Retry failed')
    } finally {
      setActionId(null)
    }
  }

  const items = data?.items ?? []

  return (
    <div className="page">
      <div className="page-header">
        <h1>Operations</h1>
        <p>Admin view of async jobs across all users. Cancel stuck runs or retry failed ones.</p>
      </div>

      <section className="panel">
        <form className="admin-ops-filters" onSubmit={applyFilters}>
          <label className="field">
            <span>Status</span>
            <select
              value={filters.status}
              onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
            >
              {STATUS_OPTIONS.map((value) => (
                <option key={value || 'all'} value={value}>
                  {value ? formatType(value) : 'All'}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Type</span>
            <select
              value={filters.operation_type}
              onChange={(e) =>
                setFilters((f) => ({ ...f, operation_type: e.target.value }))
              }
            >
              {TYPE_OPTIONS.map((value) => (
                <option key={value || 'all'} value={value}>
                  {value ? formatType(value) : 'All'}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>User id</span>
            <input
              type="number"
              min={1}
              placeholder="Any"
              value={filters.user_id}
              onChange={(e) => setFilters((f) => ({ ...f, user_id: e.target.value }))}
            />
          </label>
          <label className="field">
            <span>Resource id (BRD)</span>
            <input
              type="number"
              min={1}
              placeholder="Any"
              value={filters.resource_id}
              onChange={(e) =>
                setFilters((f) => ({ ...f, resource_id: e.target.value }))
              }
            />
          </label>
          <div className="admin-ops-filter-actions">
            <button type="submit" className="btn btn-primary">
              Apply
            </button>
            <button type="button" className="btn btn-ghost" onClick={resetFilters}>
              Reset
            </button>
          </div>
        </form>
      </section>

      {error && <p className="form-error">{error}</p>}

      <section className="panel admin-ops-panel">
        {loading && <p className="empty-hint">Loading operations…</p>}
        {!loading && items.length === 0 && (
          <p className="empty-hint">No operations match these filters.</p>
        )}
        {!loading && items.length > 0 && (
          <div className="admin-ops-table-wrap">
            <table className="admin-ops-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Type</th>
                  <th>User</th>
                  <th>Resource</th>
                  <th>Created</th>
                  <th>Error</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((op) => {
                  const busy = actionId === op.operation_id
                  const canCancel = op.status === 'pending' || op.status === 'running'
                  const canRetry = op.status === 'failed' || op.status === 'cancelled'
                  const brdLink =
                    op.resource_type === 'brd' && op.resource_id != null
                      ? `/brds/${op.resource_id}`
                      : null
                  return (
                    <tr key={op.operation_id}>
                      <td>
                        <StatusBadge status={op.status} />
                      </td>
                      <td>
                        <span className="admin-ops-type">{formatType(op.operation_type)}</span>
                        <span className="meta admin-ops-id" title={op.operation_id}>
                          {op.operation_id.slice(0, 8)}…
                        </span>
                      </td>
                      <td>{op.user_id ?? '—'}</td>
                      <td>
                        {brdLink ? (
                          <Link to={brdLink}>
                            {op.resource_type} #{op.resource_id}
                          </Link>
                        ) : op.resource_id != null ? (
                          `${op.resource_type || 'resource'} #${op.resource_id}`
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="admin-ops-when">{formatWhen(op.created_at)}</td>
                      <td className="admin-ops-error" title={op.error_message || ''}>
                        {op.error_message || '—'}
                      </td>
                      <td className="admin-ops-actions">
                        {canCancel && (
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            disabled={busy}
                            onClick={() => handleCancel(op.operation_id)}
                          >
                            Cancel
                          </button>
                        )}
                        {canRetry && (
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            disabled={busy}
                            onClick={() => handleRetry(op.operation_id)}
                          >
                            Retry
                          </button>
                        )}
                        {!canCancel && !canRetry && <span className="meta">—</span>}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {data && data.total_pages > 1 && (
          <div className="admin-ops-pager">
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              disabled={!data.has_prev || loading}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Previous
            </button>
            <span className="meta">
              Page {data.page} of {data.total_pages} ({data.total} total)
            </span>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              disabled={!data.has_next || loading}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        )}
      </section>
    </div>
  )
}
