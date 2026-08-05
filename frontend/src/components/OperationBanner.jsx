export function OperationBanner({ operation, error, loading }) {
  if (!operation && !error && !loading) return null

  return (
    <div className={`operation-banner ${error ? 'error' : loading ? 'running' : ''}`}>
      {error && <p>{error}</p>}
      {!error && operation && (
        <p>
          {loading ? 'Working…' : 'Done:'} {operation.operation_type.replace(/_/g, ' ')}
          {' — '}
          <strong>{operation.status}</strong>
        </p>
      )}
    </div>
  )
}
