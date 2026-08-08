import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import * as brdApi from '../api/brds'
import { BrdListProgress } from '../components/BrdListProgress'
import { ConfirmModal } from '../components/ConfirmModal'
import { StatusBadge } from '../components/StatusBadge'
import { useJobs } from '../context/JobsContext'
import { PipelineSettingsForm } from '../components/PipelineSettingsForm'
import {
  DEFAULT_PIPELINE_SETTINGS,
  serializePipelineSettings,
} from '../utils/pipelineSettings'

const ACCEPT =
  '.pdf,.docx,.xlsx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

const ACCEPTED_EXTENSIONS = ['.pdf', '.docx', '.xlsx']
const MAX_UPLOAD_MB = 20

function formatBytes(bytes) {
  if (!bytes) return ''
  const mb = bytes / (1024 * 1024)
  if (mb >= 1) return `${mb.toFixed(1)} MB`
  return `${Math.max(1, Math.round(bytes / 1024))} KB`
}

export function BrdListPage() {
  const [brds, setBrds] = useState([])
  const [trash, setTrash] = useState([])
  const [showTrash, setShowTrash] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [name, setName] = useState('')
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [confirmAction, setConfirmAction] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [settings, setSettings] = useState(DEFAULT_PIPELINE_SETTINGS)
  const { trackJob, runningCount } = useJobs()

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [active, trashed] = await Promise.all([
        brdApi.listBrds({ page_size: 50 }),
        brdApi.listBrds({ page_size: 50, trashed: true }),
      ])
      setBrds(active.items)
      setTrash(trashed.items)
    } catch (err) {
      setError(err.message || 'Failed to load BRDs')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  function pickFile(next) {
    if (!next) return
    const ext = `.${next.name.split('.').pop()?.toLowerCase()}`
    if (!ACCEPTED_EXTENSIONS.includes(ext)) {
      setError(`Unsupported file type "${ext}". Use PDF, DOCX, or XLSX.`)
      return
    }
    setError('')
    setFile(next)
    if (!name.trim()) {
      const base = next.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' ').trim()
      if (base) setName(base)
    }
  }

  function handleDragOver(e) {
    e.preventDefault()
    setDragOver(true)
  }

  function handleDragLeave() {
    setDragOver(false)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    pickFile(e.dataTransfer.files?.[0] ?? null)
  }

  async function handleUpload(e) {
    e.preventDefault()
    if (!file || !name.trim()) return
    setUploading(true)
    setError('')
    try {
      const op = await brdApi.uploadBrd(name.trim(), file, serializePipelineSettings(settings))
      await trackJob(op, {
        label: 'Parse BRD',
        brdId: op.resource_id ?? null,
      })
      setName('')
      setFile(null)
      setSettings(DEFAULT_PIPELINE_SETTINGS)
      setShowSettings(false)
      await load()
    } catch (err) {
      setError(err.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  async function runConfirm() {
    if (!confirmAction) return
    const { type, brd } = confirmAction
    setError('')
    try {
      if (type === 'trash') await brdApi.deleteBrd(brd.id)
      else if (type === 'restore') await brdApi.restoreBrd(brd.id)
      else if (type === 'purge') await brdApi.purgeBrd(brd.id)
      await load()
    } catch (err) {
      setError(err.message || 'Action failed')
    } finally {
      setConfirmAction(null)
    }
  }

  const busy = uploading || runningCount > 0

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>BRD documents</h1>
          <p>Upload a PDF, DOCX, or XLSX to start the pipeline.</p>
        </div>
      </div>

      <section className="panel">
        <h2>Upload BRD</h2>
        <div className="upload-panel-grid">
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
            <div className="field upload-form-dropzone-field">
              <span>File</span>
              <label
                htmlFor="brd-file-input"
                className={`file-dropzone ${dragOver ? 'file-dropzone-active' : ''} ${file ? 'file-dropzone-filled' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <input
                  id="brd-file-input"
                  type="file"
                  accept={ACCEPT}
                  onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
                  required={!file}
                />
                {file ? (
                  <span className="file-dropzone-selected">
                    <strong>{file.name}</strong>
                    <span className="meta">{formatBytes(file.size)} · click or drop to replace</span>
                  </span>
                ) : (
                  <span className="file-dropzone-hint">
                    <strong>Drag &amp; drop your BRD here</strong>
                    <span className="meta">or click to browse — PDF, DOCX, or XLSX, up to {MAX_UPLOAD_MB}MB</span>
                  </span>
                )}
              </label>
            </div>
            <div className="upload-settings-toggle">
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setShowSettings((v) => !v)}
              >
                {showSettings ? 'Hide generation preferences' : 'Generation preferences (optional)'}
              </button>
            </div>

            {showSettings && (
              <PipelineSettingsForm settings={settings} onChange={setSettings} />
            )}

            <div className="upload-form-actions">
              <button type="submit" className="btn btn-primary" disabled={busy || !file}>
                {busy ? 'Processing…' : 'Upload & parse'}
              </button>
            </div>
            {error && <p className="form-error">{error}</p>}
          </form>

          <aside className="upload-hints">
            <div className="upload-hints-block">
              <h3>Tips for better results</h3>
              <ul>
                <li>Use clear section headings — they map closely to extracted features.</li>
                <li>Include acceptance criteria or business rules if you have them.</li>
                <li>Tables and images in the document are parsed too; no need to flatten them.</li>
              </ul>
            </div>
            <div className="upload-hints-block">
              <h3>What happens next</h3>
              <ol className="upload-hints-steps">
                <li>Parse &amp; extract text</li>
                <li>Extract features (you review)</li>
                <li>Generate stories (you review)</li>
                <li>Estimate points (you review)</li>
                <li>Generate test cases (you review)</li>
                <li>Export CSV / Jira CSV</li>
              </ol>
            </div>
          </aside>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header-row">
          <h2>Your BRDs</h2>
          {trash.length > 0 && (
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => setShowTrash((v) => !v)}
            >
              {showTrash ? 'Hide trash' : `Trash (${trash.length})`}
            </button>
          )}
        </div>
        {loading && <p className="empty-hint">Loading…</p>}
        {!loading && brds.length === 0 && <p className="empty-hint">No BRDs uploaded yet.</p>}
        {!loading && brds.length > 0 && (
          <ul className="brd-list">
            {brds.map((brd) => (
              <li key={brd.id} className="brd-list-row">
                <Link to={`/brds/${brd.id}`} className="brd-list-item">
                  <div>
                    <strong>{brd.name}</strong>
                    <span className="meta">{brd.original_filename}</span>
                    <BrdListProgress brdId={brd.id} brdStatus={brd.status} />
                  </div>
                  <StatusBadge status={brd.status} />
                  <span className="brd-list-chevron" aria-hidden="true">
                    ›
                  </span>
                </Link>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm brd-row-action"
                  onClick={() =>
                    setConfirmAction({
                      type: 'trash',
                      brd,
                      title: 'Move to trash?',
                      message: `"${brd.name}" will be moved to trash. You can restore it later.`,
                      confirmLabel: 'Move to trash',
                      danger: true,
                    })
                  }
                >
                  Trash
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {showTrash && trash.length > 0 && (
        <section className="panel">
          <h2>Trash</h2>
          <ul className="brd-list">
            {trash.map((brd) => (
              <li key={brd.id} className="brd-list-row">
                <div className="brd-list-item brd-list-item-static">
                  <div>
                    <strong>{brd.name}</strong>
                    <span className="meta">{brd.original_filename}</span>
                  </div>
                  <StatusBadge status={brd.status} />
                </div>
                <div className="brd-row-actions">
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() =>
                      setConfirmAction({
                        type: 'restore',
                        brd,
                        title: 'Restore BRD?',
                        message: `"${brd.name}" will return to your active list.`,
                        confirmLabel: 'Restore',
                      })
                    }
                  >
                    Restore
                  </button>
                  <button
                    type="button"
                    className="btn btn-danger btn-sm"
                    onClick={() =>
                      setConfirmAction({
                        type: 'purge',
                        brd,
                        title: 'Delete permanently?',
                        message: `"${brd.name}" and its files will be removed forever.`,
                        confirmLabel: 'Delete forever',
                        danger: true,
                      })
                    }
                  >
                    Delete forever
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {confirmAction && (
        <ConfirmModal
          title={confirmAction.title}
          message={confirmAction.message}
          confirmLabel={confirmAction.confirmLabel}
          danger={confirmAction.danger}
          onConfirm={runConfirm}
          onClose={() => setConfirmAction(null)}
        />
      )}
    </div>
  )
}
