import { useMemo, useState } from 'react'
import { ITEM_TYPES } from '../utils/pipeline'
import { nodeToItem } from '../utils/lineage'

function StatusDot({ status }) {
  const cls =
    status === 'approved'
      ? 'tree-dot-approved'
      : status === 'pending_review'
        ? 'tree-dot-pending'
        : status === 'rejected'
          ? 'tree-dot-rejected'
          : 'tree-dot-neutral'
  return <span className={`tree-dot ${cls}`} aria-hidden="true" />
}

function toggleSet(setFn, id) {
  setFn((prev) => {
    const next = new Set(prev)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    return next
  })
}

export function TreeSidebar({ features, subFeatures, stories, testCases, selectedItem, onSelect, onClose }) {
  const [expandedFeatures, setExpandedFeatures] = useState(() => new Set())
  const [expandedSubFeatures, setExpandedSubFeatures] = useState(() => new Set())
  const [expandedStories, setExpandedStories] = useState(() => new Set())

  // Branch containing the currently selected item is always treated as open,
  // so the tree keeps showing the selection's place in the hierarchy even if
  // the user never manually expanded it.
  const requiredOpen = useMemo(() => {
    const featureIds = new Set()
    const subFeatureIds = new Set()
    const storyIds = new Set()

    if (selectedItem) {
      const entity = selectedItem.entity
      if (selectedItem.type === ITEM_TYPES.SUB_FEATURE) {
        featureIds.add(entity.feature_id)
      } else if (selectedItem.type === ITEM_TYPES.STORY || selectedItem.type === ITEM_TYPES.POINTS) {
        const sf = subFeatures.find((s) => s.id === entity.sub_feature_id)
        if (sf) {
          featureIds.add(sf.feature_id)
          subFeatureIds.add(sf.id)
        }
      } else if (selectedItem.type === ITEM_TYPES.TEST_CASE) {
        const story = stories.find((s) => s.id === entity.story_id)
        if (story) {
          const sf = subFeatures.find((s) => s.id === story.sub_feature_id)
          if (sf) {
            featureIds.add(sf.feature_id)
            subFeatureIds.add(sf.id)
          }
          storyIds.add(story.id)
        }
      }
    }

    return { featureIds, subFeatureIds, storyIds }
  }, [selectedItem, subFeatures, stories])

  function isSelected(type, id) {
    if (selectedItem?.type !== type) return false
    // Queue items may use composite ids (e.g. points-12); compare on entity id.
    return selectedItem.entity?.id === id || selectedItem.id === id
  }

  function select(type, entity) {
    onSelect(nodeToItem({ type, id: entity.id, title: entity.title, entity, status: type === ITEM_TYPES.POINTS ? entity.points_status : entity.status }))
  }

  return (
    <aside className="tree-sidebar">
      <div className="tree-sidebar-header">
        <h3>Structure</h3>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onClose} aria-label="Hide structure tree">
          ✕
        </button>
      </div>
      <div className="tree-sidebar-body">
        {features.length === 0 && <p className="empty-hint">No features yet.</p>}
        <ul className="tree-list">
          {features.map((feature) => {
            const childSubFeatures = subFeatures.filter((sf) => sf.feature_id === feature.id)
            const isOpen = expandedFeatures.has(feature.id) || requiredOpen.featureIds.has(feature.id)
            return (
              <li key={feature.id} className="tree-node">
                <div className={`tree-row ${isSelected(ITEM_TYPES.FEATURE, feature.id) ? 'tree-row-active' : ''}`}>
                  {childSubFeatures.length > 0 ? (
                    <button
                      type="button"
                      className="tree-toggle"
                      onClick={() => toggleSet(setExpandedFeatures, feature.id)}
                      aria-label={isOpen ? 'Collapse' : 'Expand'}
                    >
                      {isOpen ? '▾' : '▸'}
                    </button>
                  ) : (
                    <span className="tree-toggle-spacer" />
                  )}
                  <button type="button" className="tree-label" title={feature.title} onClick={() => select(ITEM_TYPES.FEATURE, feature)}>
                    <StatusDot status={feature.status} />
                    <span className="tree-title">{feature.title}</span>
                  </button>
                </div>

                {isOpen && childSubFeatures.length > 0 && (
                  <ul className="tree-list tree-list-nested">
                    {childSubFeatures.map((sf) => {
                      const childStories = stories.filter((s) => s.sub_feature_id === sf.id)
                      const sfOpen = expandedSubFeatures.has(sf.id) || requiredOpen.subFeatureIds.has(sf.id)
                      return (
                        <li key={sf.id} className="tree-node">
                          <div className={`tree-row ${isSelected(ITEM_TYPES.SUB_FEATURE, sf.id) ? 'tree-row-active' : ''}`}>
                            {childStories.length > 0 ? (
                              <button
                                type="button"
                                className="tree-toggle"
                                onClick={() => toggleSet(setExpandedSubFeatures, sf.id)}
                                aria-label={sfOpen ? 'Collapse' : 'Expand'}
                              >
                                {sfOpen ? '▾' : '▸'}
                              </button>
                            ) : (
                              <span className="tree-toggle-spacer" />
                            )}
                            <button type="button" className="tree-label" title={sf.title} onClick={() => select(ITEM_TYPES.SUB_FEATURE, sf)}>
                              <StatusDot status={sf.status} />
                              <span className="tree-title">{sf.title}</span>
                            </button>
                          </div>

                          {sfOpen && childStories.length > 0 && (
                            <ul className="tree-list tree-list-nested">
                              {childStories.map((story) => {
                                const childTestCases = testCases.filter((tc) => tc.story_id === story.id)
                                const storyOpen = expandedStories.has(story.id) || requiredOpen.storyIds.has(story.id)
                                return (
                                  <li key={story.id} className="tree-node">
                                    <div className={`tree-row ${isSelected(ITEM_TYPES.STORY, story.id) ? 'tree-row-active' : ''}`}>
                                      {childTestCases.length > 0 ? (
                                        <button
                                          type="button"
                                          className="tree-toggle"
                                          onClick={() => toggleSet(setExpandedStories, story.id)}
                                          aria-label={storyOpen ? 'Collapse' : 'Expand'}
                                        >
                                          {storyOpen ? '▾' : '▸'}
                                        </button>
                                      ) : (
                                        <span className="tree-toggle-spacer" />
                                      )}
                                      <button type="button" className="tree-label" title={story.title} onClick={() => select(ITEM_TYPES.STORY, story)}>
                                        <StatusDot status={story.status} />
                                        <span className="tree-title">{story.title}</span>
                                        {story.points_status && (
                                          <span className={`tree-points-badge tree-points-${story.points_status}`} title={`Points: ${story.points_status}`}>
                                            pts
                                          </span>
                                        )}
                                        {childTestCases.length > 0 && (
                                          <span className="tree-tests-badge" title={`${childTestCases.length} test case${childTestCases.length !== 1 ? 's' : ''}`}>
                                            {childTestCases.length}T
                                          </span>
                                        )}
                                      </button>
                                    </div>

                                    {storyOpen && childTestCases.length > 0 && (
                                      <ul className="tree-list tree-list-nested">
                                        {childTestCases.map((tc) => (
                                          <li key={tc.id} className="tree-node">
                                            <div className={`tree-row ${isSelected(ITEM_TYPES.TEST_CASE, tc.id) ? 'tree-row-active' : ''}`}>
                                              <span className="tree-toggle-spacer" />
                                              <button type="button" className="tree-label" title={tc.title} onClick={() => select(ITEM_TYPES.TEST_CASE, tc)}>
                                                <StatusDot status={tc.status} />
                                                <span className="tree-title">{tc.title}</span>
                                              </button>
                                            </div>
                                          </li>
                                        ))}
                                      </ul>
                                    )}
                                  </li>
                                )
                              })}
                            </ul>
                          )}
                        </li>
                      )
                    })}
                  </ul>
                )}
              </li>
            )
          })}
        </ul>
      </div>
    </aside>
  )
}
