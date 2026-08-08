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
  const [refining, setRefining] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [refined, setRefined] = useState(false)

  useEffect(() => {
    setAnswers(buildInitialAnswers(feature))
    setSaved(false)
    setRefined(false)
    setError('')
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset when feature answers/questions change
  }, [feature.id, JSON.stringify(feature.clarifying_answers), JSON.stringify(feature.clarifying_questions)])

  const answeredCount = answers.filter((item) => item.answer.trim()).length
  const allAnswered = answers.length > 0 && answeredCount === answers.length
  const busy = disabled || saving || refining

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    setSaved(false)
    setRefined(false)
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

  async function handleRefine() {
    setRefining(true)
    setError('')
    setRefined(false)
    try {
      const payload = answers
        .filter((item) => item.answer.trim())
        .map((item) => ({
          question: item.question,
          answer: item.answer.trim(),
        }))
      if (payload.length > 0) {
        await featureApi.updateFeature(feature.id, { clarifying_answers: payload })
      }
      await featureApi.refineFeatureFromAnswers(feature.id)
      setRefined(true)
      setSaved(true)
      await onSaved?.()
    } catch (err) {
      setError(err.message || 'Failed to refine feature from answers')
    } finally {
      setRefining(false)
    }
  }

  return (
    <form className="clarifying-answers-form" onSubmit={handleSave}>
      <div className="clarifying-answers-header">
        <p className="meta">
          {answeredCount} of {answers.length} answered — save answers, then refine the feature
          (or generate sub-features).
        </p>
      </div>
      {answers.map((item, index) => (
        <label key={item.question} className="field clarifying-answer-field">
          <span>{item.question}</span>
          <textarea
            rows={3}
            value={item.answer}
            onChange={(e) => {
              setAnswers((current) =>
                current.map((row, i) => (i === index ? { ...row, answer: e.target.value } : row)),
              )
              setSaved(false)
              setRefined(false)
            }}
            placeholder="Your answer…"
            disabled={busy}
          />
        </label>
      ))}
      {error && <p className="form-error">{error}</p>}
      {saved && !refined && <p className="form-success">Answers saved.</p>}
      {refined && <p className="form-success">Feature refined from your answers.</p>}
      <div className="clarifying-answers-actions">
        <button type="submit" className="btn btn-primary btn-sm" disabled={busy}>
          {saving ? 'Saving…' : 'Save answers'}
        </button>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={busy || !allAnswered}
          onClick={handleRefine}
          title={
            allAnswered
              ? 'Rewrite this feature using your answers'
              : 'Answer all questions before refining'
          }
        >
          {refining ? 'Refining…' : 'Refine feature from answers'}
        </button>
      </div>
    </form>
  )
}
