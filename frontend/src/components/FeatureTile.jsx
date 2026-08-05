import { StatusBadge } from './StatusBadge'
import { previewText } from '../utils/previewText'

export function FeatureTile({ feature, onClick }) {
  const questionCount = feature.clarifying_questions?.length ?? 0
  const answeredCount = feature.clarifying_answers?.length ?? 0

  return (
    <button type="button" className="feature-tile" onClick={() => onClick(feature)}>
      <div className="feature-tile-top">
        <StatusBadge status={feature.status} />
        {feature.confidence != null && (
          <span className="feature-tile-confidence">{(feature.confidence * 100).toFixed(0)}%</span>
        )}
      </div>
      <h4 className="feature-tile-title">{feature.title}</h4>
      <p className="feature-tile-preview">{previewText(feature.description)}</p>
      <div className="feature-tile-footer">
        {questionCount > 0 && (
          <span className="meta">
            {answeredCount}/{questionCount} answered
          </span>
        )}
        <span className="feature-tile-cta">View details →</span>
      </div>
    </button>
  )
}
