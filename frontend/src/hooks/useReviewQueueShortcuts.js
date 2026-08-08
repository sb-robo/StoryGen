import { useEffect } from 'react'
import { filterReviewQueue, queueItemKey } from '../utils/reviewActions'

/**
 * Queue tab shortcuts: j/k (or arrows) navigate, a approve current item.
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
        if (!selectedItem) return
        // Only approve when the selected item is still in the filtered queue
        if (currentIndex < 0) return
        event.preventDefault()
        onApprove(selectedItem)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [enabled, items, typeFilter, parentFilter, selectedItem, onSelect, onApprove, busy])
}
