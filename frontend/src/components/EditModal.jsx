import { useState } from 'react'
import { useDialogA11y } from '../hooks/useDialogA11y'

export function EditModal({ title, fields, onSave, onClose }) {
  const dialogRef = useDialogA11y({ onClose })
  const [values, setValues] = useState(() =>
    Object.fromEntries(fields.map((f) => [f.name, f.value ?? ''])),
  )
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const payload = {}
      for (const field of fields) {
        const val = values[field.name]
        if (field.type === 'number') {
          payload[field.name] = val === '' ? null : Number(val)
        } else if (field.type === 'lines') {
          payload[field.name] = val.split('\n').map((l) => l.trim()).filter(Boolean)
        } else if (val !== '') {
          payload[field.name] = val
        }
      }
      await onSave(payload)
      onClose()
    } catch (err) {
      setError(err.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        ref={dialogRef}
        className="modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-modal-title"
      >
        <h3 id="edit-modal-title">{title}</h3>
        <form onSubmit={handleSubmit}>
          {fields.map((field, index) => (
            <label key={field.name} className="field">
              <span>{field.label}</span>
              {field.type === 'textarea' || field.type === 'lines' ? (
                <textarea
                  rows={field.type === 'lines' ? 5 : 4}
                  value={values[field.name]}
                  onChange={(e) => setValues({ ...values, [field.name]: e.target.value })}
                  placeholder={field.placeholder}
                  data-initial-focus={index === 0 ? true : undefined}
                />
              ) : (
                <input
                  type={field.type || 'text'}
                  value={values[field.name]}
                  onChange={(e) => setValues({ ...values, [field.name]: e.target.value })}
                  min={field.min}
                  max={field.max}
                  data-initial-focus={index === 0 ? true : undefined}
                />
              )}
            </label>
          ))}
          {error && <p className="form-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
