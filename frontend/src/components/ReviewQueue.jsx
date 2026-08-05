import { useMemo } from 'react'
import { typeLabel } from '../utils/pipeline'
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
  selectedId,
  onSelect,
  filter,
  onFilterChange,
  parentFilter,
  onParentFilterChange,
}) {
  const parentOptions = useMemo(() => {
    const labels = new Set(items.map((i) => i.parentLabel).filter((l) => l && l !== '—'))
    return ['all', ...Array.from(labels).sort()]
  }, [items])

  const filtered = useMemo(() => {
    let result = filter === 'all' ? items : items.filter((item) => item.type === filter)
    if (parentFilter && parentFilter !== 'all') {
      result = result.filter((item) => item.parentLabel === parentFilter)
    }
    return result
  }, [items, filter, parentFilter])

  return (
    <section className="review-queue">
      <div className="queue-header">
        <h2>Review queue</h2>
        <span className="meta">{filtered.length} item{filtered.length !== 1 ? 's' : ''}</span>
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
                <th>Item</th>
                <th>Type</th>
                <th>Parent</th>
                <th>Confidence</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr
                  key={item.id}
                  className={`queue-row ${selectedId === item.id ? 'queue-row-selected' : ''}`}
                  onClick={() => onSelect(item)}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      onSelect(item)
                    }
                  }}
                >
                  <td className="queue-title">{item.title}</td>
                  <td>{typeLabel(item.type)}</td>
                  <td className="queue-parent">{item.parentLabel}</td>
                  <td>{item.confidence != null ? `${(item.confidence * 100).toFixed(0)}%` : '—'}</td>
                  <td>
                    <StatusBadge status={item.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
