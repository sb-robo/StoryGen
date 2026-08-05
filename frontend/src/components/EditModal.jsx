import { useState } from 'react'

export function EditModal({ title, fields, onSave, onClose, layered = false }) {
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
    <div className={`modal-backdrop${layered ? ' modal-backdrop-layered' : ''}`} onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{title}</h3>
        <form onSubmit={handleSubmit}>
          {fields.map((field) => (
            <label key={field.name} className="field">
              <span>{field.label}</span>
              {field.type === 'textarea' || field.type === 'lines' ? (
                <textarea
                  rows={field.type === 'lines' ? 5 : 4}
                  value={values[field.name]}
                  onChange={(e) => setValues({ ...values, [field.name]: e.target.value })}
                  placeholder={field.placeholder}
                />
              ) : (
                <input
                  type={field.type || 'text'}
                  value={values[field.name]}
                  onChange={(e) => setValues({ ...values, [field.name]: e.target.value })}
                  min={field.min}
                  max={field.max}
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
