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
const PAGE_SIZE = 10

const STATUS_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'parsed', label: 'Parsed' },
  { value: 'parsing', label: 'Parsing' },
  { value: 'uploaded', label: 'Uploaded' },
  { value: 'parse_failed', label: 'Parse failed' },
]

const FILE_TYPE_OPTIONS = [
  { value: '', label: 'All types' },
  { value: '.pdf', label: 'PDF' },
  { value: '.docx', label: 'DOCX' },
  { value: '.xlsx', label: 'XLSX' },
]

const SORT_OPTIONS = [
  { value: 'created_at:desc', label: 'Newest first' },
  { value: 'created_at:asc', label: 'Oldest first' },
  { value: 'name:asc', label: 'Name A–Z' },
  { value: 'name:desc', label: 'Name Z–A' },
  { value: 'updated_at:desc', label: 'Recently updated' },
]

function formatBytes(bytes) {
  if (!bytes) return ''
  const mb = bytes / (1024 * 1024)
  if (mb >= 1) return `${mb.toFixed(1)} MB`
  return `${Math.max(1, Math.round(bytes / 1024))} KB`
}

function parseSort(value) {
  const [sort_by, sort_order] = value.split(':')
  return { sort_by, sort_order }
}

export function BrdListPage() {
  const [brds, setBrds] = useState([])
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [hasNext, setHasNext] = useState(false)
  const [hasPrev, setHasPrev] = useState(false)
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [fileExtension, setFileExtension] = useState('')
  const [sort, setSort] = useState('created_at:desc')
  const [trash, setTrash] = useState([])
  const [trashTotal, setTrashTotal] = useState(0)
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

  useEffect(() => {
    const handle = window.setTimeout(() => {
      const next = searchInput.trim()
      setSearch(next)
      setPage(1)
    }, 300)
    return () => window.clearTimeout(handle)
  }, [searchInput])

  const loadActive = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const { sort_by, sort_order } = parseSort(sort)
      const result = await brdApi.listBrds({
        page,
        page_size: PAGE_SIZE,
        status: status || undefined,
        search: search || undefined,
        file_extension: fileExtension || undefined,
        sort_by,
        sort_order,
      })
      setBrds(result.items)
      setTotal(result.total)
      setTotalPages(result.total_pages)
      setHasNext(result.has_next)
      setHasPrev(result.has_prev)
    } catch (err) {
      setError(err.message || 'Failed to load BRDs')
    } finally {
      setLoading(false)
    }
  }, [page, search, status, fileExtension, sort])

  const loadTrash = useCallback(async () => {
    try {
      const trashed = await brdApi.listBrds({ page_size: 50, trashed: true })
      setTrash(trashed.items)
      setTrashTotal(trashed.total)
    } catch {
      // Trash is secondary; keep the active list usable if this fails.
    }
  }, [])

  useEffect(() => {
    loadActive()
  }, [loadActive])

  useEffect(() => {
    loadTrash()
  }, [loadTrash])

  async function reloadAll() {
    await Promise.all([loadActive(), loadTrash()])
  }

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
      setPage(1)
      await reloadAll()
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
      await reloadAll()
    } catch (err) {
      setError(err.message || 'Action failed')
    } finally {
      setConfirmAction(null)
    }
  }

  const busy = uploading || runningCount > 0
  const rangeStart = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1
  const rangeEnd = Math.min(page * PAGE_SIZE, total)

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>BRD documents</h1>
          <p>Upload a PDF, DOCX, or XLSX to start the pipeline.</p>
        </div>
      </div>

      <div className="brd-home-layout">
        <section className="panel brd-home-upload">
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
                    <span className="meta">
                      or click to browse — PDF, DOCX, or XLSX, up to {MAX_UPLOAD_MB}MB
                    </span>
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

          <aside className="upload-hints upload-hints-stacked">
            <div className="upload-hints-block">
              <h3>Tips for better results</h3>
              <ul>
                <li>Use clear section headings — they map closely to extracted features.</li>
                <li>Include acceptance criteria or business rules if you have them.</li>
                <li>Tables and images are parsed too; no need to flatten them.</li>
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
        </section>

        <section className="panel brd-home-list">
          <div className="panel-header-row">
            <h2>Your BRDs</h2>
            {trashTotal > 0 && (
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setShowTrash((v) => !v)}
              >
                {showTrash ? 'Hide trash' : `Trash (${trashTotal})`}
              </button>
            )}
          </div>

          <div className="brd-list-filters">
            <label className="field brd-list-search">
              <span className="sr-only">Search BRDs</span>
              <input
                type="search"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search name or filename…"
              />
            </label>
            <label className="field">
              <span className="sr-only">Status</span>
              <select
                value={status}
                onChange={(e) => {
                  setStatus(e.target.value)
                  setPage(1)
                }}
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value || 'all-status'} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span className="sr-only">File type</span>
              <select
                value={fileExtension}
                onChange={(e) => {
                  setFileExtension(e.target.value)
                  setPage(1)
                }}
              >
                {FILE_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value || 'all-type'} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span className="sr-only">Sort</span>
              <select
                value={sort}
                onChange={(e) => {
                  setSort(e.target.value)
                  setPage(1)
                }}
              >
                {SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {loading && <p className="empty-hint">Loading…</p>}
          {!loading && brds.length === 0 && (
            <p className="empty-hint">
              {search || status || fileExtension
                ? 'No BRDs match these filters.'
                : 'No BRDs uploaded yet.'}
            </p>
          )}
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

          {!loading && total > 0 && (
            <div className="brd-list-pagination">
              <span className="meta">
                {rangeStart}–{rangeEnd} of {total}
              </span>
              <div className="brd-list-pagination-actions">
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  disabled={!hasPrev}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </button>
                <span className="brd-list-page-label">
                  Page {page}
                  {totalPages ? ` / ${totalPages}` : ''}
                </span>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  disabled={!hasNext}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          )}

          {showTrash && trash.length > 0 && (
            <div className="brd-trash-section">
              <h3>Trash</h3>
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
            </div>
          )}
        </section>
      </div>

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
