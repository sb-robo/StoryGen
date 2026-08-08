import { useEffect, useMemo, useState } from 'react'
import { ITEM_TYPES, typeLabel, unansweredClarifyingCount } from '../utils/pipeline'
import { filterReviewQueue, queueItemKey } from '../utils/reviewActions'
import { StatusBadge } from './StatusBadge'

const TYPE_FILTERS = [
  { id: 'all', label: 'All pending' },
  { id: 'feature', label: 'Features' },
  { id: 'sub_feature', label: 'Sub-features' },
  { id: 'story', label: 'Stories' },
  { id: 'points', label: 'Points' },
  { id: 'test_case', label: 'Test cases' },
]

export function ReviewQueue({
  items,
  selectedItem,
  onSelect,
  filter,
  onFilterChange,
  parentFilter,
  onParentFilterChange,
  busy,
  onBulkApprove,
  bulkStatus,
}) {
  const [checkedKeys, setCheckedKeys] = useState(() => new Set())

  const parentOptions = useMemo(() => {
    const labels = new Set(items.map((i) => i.parentLabel).filter((l) => l && l !== '—'))
    return ['all', ...Array.from(labels).sort()]
  }, [items])

  const filtered = useMemo(
    () => filterReviewQueue(items, filter, parentFilter),
    [items, filter, parentFilter],
  )

  const filteredKeys = useMemo(() => filtered.map((item) => queueItemKey(item)), [filtered])
  const selectedKey = queueItemKey(selectedItem)

  // Drop checked keys that are no longer in the queue (e.g. after approve/refresh).
  useEffect(() => {
    const valid = new Set(items.map((item) => queueItemKey(item)))
    setCheckedKeys((prev) => {
      let changed = false
      const next = new Set()
      for (const key of prev) {
        if (valid.has(key)) next.add(key)
        else changed = true
      }
      return changed ? next : prev
    })
  }, [items])

  const allFilteredChecked =
    filteredKeys.length > 0 && filteredKeys.every((key) => checkedKeys.has(key))
  const someFilteredChecked = filteredKeys.some((key) => checkedKeys.has(key))
  const checkedCount = filteredKeys.filter((key) => checkedKeys.has(key)).length

  function toggleKey(key, checked) {
    setCheckedKeys((prev) => {
      const next = new Set(prev)
      if (checked) next.add(key)
      else next.delete(key)
      return next
    })
  }

  function toggleAllFiltered(checked) {
    setCheckedKeys((prev) => {
      const next = new Set(prev)
      for (const key of filteredKeys) {
        if (checked) next.add(key)
        else next.delete(key)
      }
      return next
    })
  }

  function handleBulkApprove() {
    const selected = filtered.filter((item) => checkedKeys.has(queueItemKey(item)))
    if (selected.length === 0) return
    onBulkApprove?.(selected)
  }

  return (
    <section className="review-queue">
      <div className="queue-header">
        <div>
          <h2>Review queue</h2>
          <p className="queue-shortcuts-hint meta">
            Shortcuts: <kbd>j</kbd>/<kbd>k</kbd> navigate · <kbd>a</kbd> approve
          </p>
        </div>
        <span className="meta">
          {filtered.length} item{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="queue-filters">
        <div className="filter-chips" role="tablist" aria-label="Filter by type">
          {TYPE_FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              role="tab"
              aria-selected={filter === f.id}
              className={`filter-chip ${filter === f.id ? 'filter-chip-active' : ''}`}
              onClick={() => onFilterChange(f.id)}
            >
              {f.label}
              {f.id === 'all' && items.length > 0 && <span className="chip-count">{items.length}</span>}
            </button>
          ))}
        </div>

        {parentOptions.length > 1 && (
          <label className="parent-filter">
            <span className="meta">Parent</span>
            <select value={parentFilter} onChange={(e) => onParentFilterChange(e.target.value)}>
              <option value="all">All parents</option>
              {parentOptions
                .filter((p) => p !== 'all')
                .map((parent) => (
                  <option key={parent} value={parent}>
                    {parent}
                  </option>
                ))}
            </select>
          </label>
        )}
      </div>

      {filtered.length > 0 && (
        <div className="queue-bulk-bar">
          <label className="queue-select-all">
            <input
              type="checkbox"
              checked={allFilteredChecked}
              ref={(el) => {
                if (el) el.indeterminate = someFilteredChecked && !allFilteredChecked
              }}
              onChange={(e) => toggleAllFiltered(e.target.checked)}
              disabled={busy}
            />
            <span>
              {checkedCount > 0
                ? `${checkedCount} selected`
                : 'Select all'}
            </span>
          </label>
          <button
            type="button"
            className="btn btn-success btn-sm"
            disabled={busy || checkedCount === 0}
            onClick={handleBulkApprove}
          >
            Approve selected{checkedCount > 0 ? ` (${checkedCount})` : ''}
          </button>
        </div>
      )}

      {bulkStatus && (
        <p className={`queue-bulk-status ${bulkStatus.failed > 0 ? 'form-error' : 'meta'}`}>
          {bulkStatus.message}
        </p>
      )}

      {filtered.length === 0 && (
        <p className="empty-hint queue-empty">
          {items.length === 0 ? 'Nothing pending review — you are caught up!' : 'No items match this filter.'}
        </p>
      )}

      {filtered.length > 0 && (
        <div className="queue-table-wrap">
          <table className="queue-table">
            <thead>
              <tr>
                <th className="queue-check-col" scope="col">
                  <span className="sr-only">Select</span>
                </th>
                <th>Item</th>
                <th>Type</th>
                <th>Path</th>
                <th>Confidence</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => {
                const key = queueItemKey(item)
                const isSelected = selectedKey === key
                const isChecked = checkedKeys.has(key)
                const unanswered =
                  item.type === ITEM_TYPES.FEATURE ? unansweredClarifyingCount(item.entity) : 0
                return (
                  <tr
                    key={key}
                    className={[
                      'queue-row',
                      isSelected ? 'queue-row-selected' : '',
                      isChecked ? 'queue-row-checked' : '',
                      unanswered > 0 ? 'queue-row-blocked' : '',
                    ]
                      .filter(Boolean)
                      .join(' ')}
                    onClick={() => onSelect(item)}
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        onSelect(item)
                      }
                    }}
                  >
                    <td className="queue-check-col" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        disabled={busy}
                        aria-label={`Select ${item.title}`}
                        onChange={(e) => toggleKey(key, e.target.checked)}
                      />
                    </td>
                    <td className="queue-title">
                      {item.title}
                      {unanswered > 0 && (
                        <span className="queue-blocker-hint meta">
                          {unanswered} clarifying Q unanswered — approve blocked
                        </span>
                      )}
                    </td>
                    <td>{typeLabel(item.type)}</td>
                    <td className="queue-parent" title={item.pathLabel || item.parentLabel}>
                      {item.pathLabel || item.parentLabel}
                    </td>
                    <td>{item.confidence != null ? `${(item.confidence * 100).toFixed(0)}%` : '—'}</td>
                    <td>
                      <StatusBadge status={item.status} />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
