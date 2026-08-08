import { nodeToItem } from '../utils/lineage'

export function Breadcrumb({ path, onNavigate }) {
  if (!path || path.length <= 1) return null

  return (
    <nav className="breadcrumb" aria-label="Item lineage">
      {path.map((node, index) => {
        const isLast = index === path.length - 1
        return (
          <span key={`${node.type}-${node.id}`} className="breadcrumb-segment">
            {index > 0 && <span className="breadcrumb-sep">/</span>}
            {isLast ? (
              <span className="breadcrumb-current">{node.title}</span>
            ) : (
              <button type="button" className="breadcrumb-link" onClick={() => onNavigate(nodeToItem(node))}>
                {node.title}
              </button>
            )}
          </span>
        )
      })}
    </nav>
  )
}
