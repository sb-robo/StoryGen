import { PIPELINE_STAGES } from '../utils/pipeline'

function StepIndicator({ status, pending }) {
  if (status === 'complete') return <span className="step-icon step-complete">✓</span>
  if (status === 'failed') return <span className="step-icon step-failed">✕</span>
  if (status === 'running' || status === 'in_progress') return <span className="step-icon step-progress">◐</span>
  if (status === 'needs_review') return <span className="step-icon step-review">{pending}</span>
  if (status === 'locked') return <span className="step-icon step-locked">○</span>
  return <span className="step-icon step-empty">○</span>
}

function stepLabel(stage, stageData) {
  if (stageData.status === 'needs_review') return `${stage.label} (${stageData.pending})`
  if (stageData.status === 'complete') return `${stage.label} ✓`
  if (stageData.status === 'locked') return stage.label
  if (stageData.counts?.total > 0) {
    return `${stage.label} (${stageData.counts.approved}/${stageData.counts.total})`
  }
  return stage.label
}

export function PipelineStepper({ stages, activeStage, onStageClick, onPrimaryAction, busy }) {
  if (!stages) return null

  return (
    <nav className="pipeline-stepper" aria-label="Pipeline progress">
      <ol className="stepper-list">
        {PIPELINE_STAGES.map((stage, index) => {
          const stageData = stages[stage.id]
          const isActive = activeStage === stage.id
          const isLocked = stageData.status === 'locked'
          const showRegenerateFeatures = stage.id === 'features' && stageData.counts?.total > 0 && stageData.pending === 0
          const showCta =
            stage.id !== 'parse' &&
            !isLocked &&
            (stageData.status === 'not_started' ||
              stageData.status === 'needs_review' ||
              stageData.status === 'in_progress' ||
              showRegenerateFeatures)

          let ctaLabel = null
          if (stage.id === 'features' && stageData.counts?.total === 0) ctaLabel = 'Extract features'
          else if (stage.id === 'features' && stageData.pending > 0) ctaLabel = `Review ${stageData.pending}`
          else if (stage.id === 'features' && stageData.counts?.total > 0) ctaLabel = 'Regenerate'
          else if (stage.id === 'sub_features' && stageData.counts?.total === 0) ctaLabel = 'Generate sub-features'
          else if (stage.id === 'sub_features' && stageData.pending > 0) ctaLabel = `Review ${stageData.pending}`
          else if (stage.id === 'stories' && stageData.counts?.total === 0) ctaLabel = 'Generate stories'
          else if (stage.id === 'stories' && stageData.pending > 0) ctaLabel = `Review ${stageData.pending}`
          else if (stage.id === 'points' && stageData.pending > 0) ctaLabel = `Review ${stageData.pending} points`
          else if (stage.id === 'tests' && stageData.counts?.total === 0) ctaLabel = 'Generate test cases'
          else if (stage.id === 'tests' && stageData.pending > 0) ctaLabel = `Review ${stageData.pending}`

          return (
            <li key={stage.id} className="stepper-item">
              {index > 0 && <span className="stepper-connector" aria-hidden="true" />}
              <button
                type="button"
                className={`stepper-step ${isActive ? 'step-active' : ''} step-${stageData.status}`}
                onClick={() => onStageClick?.(stage.id)}
                title={stageData.lockReason || undefined}
                disabled={isLocked && stage.id !== 'parse'}
              >
                <StepIndicator status={stageData.status} pending={stageData.pending} />
                <span className="stepper-label">{stepLabel(stage, stageData)}</span>
              </button>
              {showCta && ctaLabel && (
                <button
                  type="button"
                  className="btn btn-primary btn-sm stepper-cta"
                  onClick={() => onPrimaryAction?.(stage.id)}
                  disabled={busy}
                >
                  {ctaLabel}
                </button>
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
