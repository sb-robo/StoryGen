import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import * as brdApi from '../api/brds'
import { FeaturePipeline } from '../components/FeaturePipeline'
import { StatusBadge } from '../components/StatusBadge'

export function BrdDetailPage() {
  const { id } = useParams()
  const [brd, setBrd] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showContent, setShowContent] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await brdApi.getBrd(id, showContent)
      setBrd(data)
    } catch (err) {
      setError(err.message || 'Failed to load BRD')
    } finally {
      setLoading(false)
    }
  }, [id, showContent])

  useEffect(() => {
    load()
  }, [load])

  if (loading && !brd) {
    return <div className="page-loading">Loading BRD…</div>
  }

  if (error && !brd) {
    return (
      <div className="page">
        <p className="form-error">{error}</p>
        <Link to="/">Back to list</Link>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <Link to="/" className="back-link">
            ← All BRDs
          </Link>
          <h1>{brd.name}</h1>
          <div className="brd-meta">
            <StatusBadge status={brd.status} />
            <span className="meta">{brd.original_filename}</span>
            {brd.page_count != null && <span className="meta">{brd.page_count} pages</span>}
            {brd.error_message && <span className="form-error">{brd.error_message}</span>}
          </div>
        </div>
      </div>

      {brd.preview && !showContent && (
        <section className="panel">
          <h2>Preview</h2>
          <pre className="content-preview">{brd.preview}</pre>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowContent(true)}>
            Load full parsed content
          </button>
        </section>
      )}

      {showContent && brd.parsed_text && (
        <section className="panel">
          <h2>Parsed content</h2>
          <pre className="content-preview">{brd.parsed_text}</pre>
        </section>
      )}

      <FeaturePipeline brdId={Number(id)} brdReady={brd.status === 'parsed'} />
    </div>
  )
}
