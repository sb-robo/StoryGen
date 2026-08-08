import { useEffect, useRef } from 'react'

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

/**
 * Focus trap + Escape-to-close + restore focus for modal dialogs.
 * Attach the returned ref to the dialog element (role="dialog").
 */
export function useDialogA11y({ onClose, isOpen = true }) {
  const dialogRef = useRef(null)

  useEffect(() => {
    if (!isOpen) return undefined

    const dialog = dialogRef.current
    if (!dialog) return undefined

    const previouslyFocused = document.activeElement
    const focusables = () => Array.from(dialog.querySelectorAll(FOCUSABLE))

    const initial = focusables()
    const preferred =
      dialog.querySelector('[data-initial-focus]') ||
      initial.find((el) => el.tagName !== 'BUTTON' || el.type === 'submit') ||
      initial[0]
    preferred?.focus()

    function onKeyDown(e) {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose?.()
        return
      }
      if (e.key !== 'Tab') return

      const nodes = focusables()
      if (nodes.length === 0) {
        e.preventDefault()
        return
      }
      const first = nodes[0]
      const last = nodes[nodes.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }

    dialog.addEventListener('keydown', onKeyDown)
    return () => {
      dialog.removeEventListener('keydown', onKeyDown)
      if (previouslyFocused && typeof previouslyFocused.focus === 'function') {
        previouslyFocused.focus()
      }
    }
  }, [isOpen, onClose])

  return dialogRef
}
