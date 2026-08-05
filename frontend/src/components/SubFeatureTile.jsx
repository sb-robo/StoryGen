import { StatusBadge } from './StatusBadge'
import { previewText } from '../utils/previewText'

export function SubFeatureTile({ subFeature, onClick }) {
  return (
    <button type="button" className="feature-tile" onClick={() => onClick(subFeature)}>
      <div className="feature-tile-top">
        <StatusBadge status={subFeature.status} />
        {subFeature.confidence != null && (
          <span className="feature-tile-confidence">{(subFeature.confidence * 100).toFixed(0)}%</span>
        )}
      </div>
      <h4 className="feature-tile-title">{subFeature.title}</h4>
      <p className="feature-tile-preview">{previewText(subFeature.description)}</p>
      <div className="feature-tile-footer">
        <span className="feature-tile-cta">View details →</span>
      </div>
    </button>
  )
}
