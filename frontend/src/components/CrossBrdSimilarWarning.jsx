export function CrossBrdSimilarWarning({ matches, label = 'features' }) {
  if (!matches?.length) return null
  return (
    <section className="detail-block cross-brd-warning" aria-label={`Similar ${label} from other BRDs`}>
      <h4>Similar from other BRDs</h4>
      <p className="cross-brd-warning-lead">
        Near-duplicates found across your other BRDs. Prefer reusing or narrowing scope unless this
        document needs a distinct capability.
      </p>
      <ul className="cross-brd-warning-list">
        {matches.map((m) => (
          <li key={`${m.kind}-${m.id ?? m.title}-${m.brd_id}`}>
            <strong>{m.title}</strong>
            <span className="meta">
              {' '}
              · {m.brd_name}
              {m.similarity != null ? ` · ${(m.similarity * 100).toFixed(0)}% similar` : ''}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
