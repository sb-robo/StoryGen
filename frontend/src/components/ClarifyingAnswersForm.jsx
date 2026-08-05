import { useEffect, useState } from 'react'
import * as featureApi from '../api/features'

function buildInitialAnswers(feature) {
  const existing = Object.fromEntries(
    (feature.clarifying_answers ?? []).map((item) => [item.question, item.answer]),
  )
  return (feature.clarifying_questions ?? []).map((question) => ({
    question,
    answer: existing[question] ?? '',
  }))
}

export function ClarifyingAnswersForm({ feature, onSaved, disabled }) {
  const [answers, setAnswers] = useState(() => buildInitialAnswers(feature))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    setAnswers(buildInitialAnswers(feature))
    setSaved(false)
    setError('')
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset when feature answers/questions change
  }, [feature.id, JSON.stringify(feature.clarifying_answers), JSON.stringify(feature.clarifying_questions)])

  const answeredCount = answers.filter((item) => item.answer.trim()).length

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    setSaved(false)
    try {
      const payload = answers
        .filter((item) => item.answer.trim())
        .map((item) => ({
          question: item.question,
          answer: item.answer.trim(),
        }))
      await featureApi.updateFeature(feature.id, { clarifying_answers: payload })
      setSaved(true)
      await onSaved?.()
    } catch (err) {
      setError(err.message || 'Failed to save answers')
    } finally {
      setSaving(false)
    }
  }

  function updateAnswer(index, value) {
    setAnswers((current) =>
      current.map((item, i) => (i === index ? { ...item, answer: value } : item)),
    )
    setSaved(false)
  }

  return (
    <form className="clarifying-answers-form" onSubmit={handleSave}>
      <div className="clarifying-answers-header">
        <p className="meta">
          {answeredCount} of {answers.length} answered — saved answers are sent to the LLM when
          generating sub-features.
        </p>
      </div>
      {answers.map((item, index) => (
        <label key={item.question} className="field clarifying-answer-field">
          <span>{item.question}</span>
          <textarea
            rows={3}
            value={item.answer}
            onChange={(e) => updateAnswer(index, e.target.value)}
            placeholder="Your answer…"
            disabled={disabled || saving}
          />
        </label>
      ))}
      {error && <p className="form-error">{error}</p>}
      {saved && <p className="form-success">Answers saved.</p>}
      <button type="submit" className="btn btn-primary btn-sm" disabled={disabled || saving}>
        {saving ? 'Saving…' : 'Save answers'}
      </button>
    </form>
  )
}
