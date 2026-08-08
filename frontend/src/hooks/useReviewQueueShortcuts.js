import { useEffect } from 'react'
import { ITEM_TYPES } from '../utils/pipeline'
import { filterReviewQueue, queueItemKey } from '../utils/reviewActions'

/**
 * Queue tab shortcuts: j/k navigate, a approve, r reject, e edit.
 * Ignored while focus is in an editable field.
 */
export function useReviewQueueShortcuts({
  enabled,
  items,
  typeFilter,
  parentFilter,
  selectedItem,
  onSelect,
  onApprove,
  onReject,
  onEdit,
  busy,
}) {
  useEffect(() => {
    if (!enabled) return undefined

    function isEditableTarget(target) {
      if (!(target instanceof HTMLElement)) return false
      const tag = target.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true
      if (target.isContentEditable) return true
      return Boolean(target.closest('[contenteditable="true"]'))
    }

    function handleKeyDown(event) {
      if (busy) return
      if (event.metaKey || event.ctrlKey || event.altKey) return
      if (isEditableTarget(event.target)) return

      const filtered = filterReviewQueue(items, typeFilter, parentFilter)
      if (filtered.length === 0) return

      const key = event.key
      const currentKey = queueItemKey(selectedItem)
      const currentIndex = filtered.findIndex((item) => queueItemKey(item) === currentKey)

      if (key === 'j' || key === 'ArrowDown') {
        event.preventDefault()
        const nextIndex = currentIndex < 0 ? 0 : Math.min(currentIndex + 1, filtered.length - 1)
        onSelect(filtered[nextIndex])
        return
      }

      if (key === 'k' || key === 'ArrowUp') {
        event.preventDefault()
        const prevIndex = currentIndex < 0 ? 0 : Math.max(currentIndex - 1, 0)
        onSelect(filtered[prevIndex])
        return
      }

      if (key === 'a' || key === 'A') {
        if (!selectedItem || currentIndex < 0) return
        event.preventDefault()
        onApprove?.(selectedItem)
        return
      }

      if (key === 'r' || key === 'R') {
        if (!selectedItem || currentIndex < 0) return
        if (selectedItem.type === ITEM_TYPES.POINTS) return
        event.preventDefault()
        onReject?.(selectedItem)
        return
      }

      if (key === 'e' || key === 'E') {
        if (!selectedItem || currentIndex < 0) return
        if (selectedItem.type === ITEM_TYPES.POINTS) return
        event.preventDefault()
        onEdit?.(selectedItem)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [
    enabled,
    items,
    typeFilter,
    parentFilter,
    selectedItem,
    onSelect,
    onApprove,
    onReject,
    onEdit,
    busy,
  ])
}
