import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import * as brdApi from '../api/brds'
import { BrdWorkspace } from '../components/BrdWorkspace'

export function BrdDetailPage() {
  const { id } = useParams()
  const [brd, setBrd] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await brdApi.getBrd(id, false)
      setBrd(data)
    } catch (err) {
      setError(err.message || 'Failed to load BRD')
    } finally {
      setLoading(false)
    }
  }, [id])

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

  if (!brd) {
    return (
      <div className="page">
        <p className="form-error">BRD not found.</p>
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
        </div>
      </div>

      <BrdWorkspace brd={brd} onRefreshBrd={load} />
    </div>
  )
}
