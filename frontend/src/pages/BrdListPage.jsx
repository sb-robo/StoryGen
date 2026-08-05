import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import * as brdApi from '../api/brds'
import { OperationBanner } from '../components/OperationBanner'
import { StatusBadge } from '../components/StatusBadge'
import { useOperationPoll } from '../hooks/useOperationPoll'

export function BrdListPage() {
  const [brds, setBrds] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [name, setName] = useState('')
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const { operation, error: pollError, loading: polling, startPoll } = useOperationPoll()

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await brdApi.listBrds({ page_size: 50 })
      setBrds(data.items)
    } catch (err) {
      setError(err.message || 'Failed to load BRDs')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function handleUpload(e) {
    e.preventDefault()
    if (!file || !name.trim()) return
    setUploading(true)
    setError('')
    try {
      const op = await brdApi.uploadBrd(name.trim(), file)
      await startPoll(op)
      setName('')
      setFile(null)
      e.target.reset()
      await load()
    } catch (err) {
      setError(err.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>BRD documents</h1>
          <p>Upload a PDF, DOCX, or XLSX to start the pipeline.</p>
        </div>
      </div>

      <section className="panel upload-panel">
        <h2>Upload BRD</h2>
        <form className="upload-form" onSubmit={handleUpload}>
          <label className="field">
            <span>Display name</span>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Payments Platform BRD"
              required
            />
          </label>
          <label className="field">
            <span>File</span>
            <input
              type="file"
              accept=".pdf,.docx,.xlsx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              required
            />
          </label>
          <button type="submit" className="btn btn-primary" disabled={uploading || polling}>
            {uploading || polling ? 'Processing…' : 'Upload & parse'}
          </button>
        </form>
        <OperationBanner operation={operation} error={pollError} loading={polling} />
        {error && <p className="form-error">{error}</p>}
      </section>

      <section className="panel">
        <h2>Your BRDs</h2>
        {loading && <p>Loading…</p>}
        {!loading && brds.length === 0 && <p className="empty-hint">No BRDs uploaded yet.</p>}
        {!loading && brds.length > 0 && (
          <ul className="brd-list">
            {brds.map((brd) => (
              <li key={brd.id}>
                <Link to={`/brds/${brd.id}`} className="brd-list-item">
                  <div>
                    <strong>{brd.name}</strong>
                    <span className="meta">{brd.original_filename}</span>
                  </div>
                  <StatusBadge status={brd.status} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
