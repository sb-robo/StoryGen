import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './useAuth'

export function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <div className="page-loading">Loading…</div>
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return children
}

export function GuestRoute({ children }) {
  const { user, loading } = useAuth()

  if (loading) {
    return <div className="page-loading">Loading…</div>
  }

  if (user) {
    return <Navigate to="/" replace />
  }

  return children
}
