import { Link } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'

export function Layout({ children }) {
  const { user, logout } = useAuth()

  return (
    <div className="layout">
      <header className="app-header">
        <Link to="/" className="brand">
          StoryGen
        </Link>
        {user && (
          <div className="header-actions">
            <span className="user-label">{user.name}</span>
            <button type="button" className="btn btn-ghost" onClick={logout}>
              Log out
            </button>
          </div>
        )}
      </header>
      <main className="app-main">{children}</main>
    </div>
  )
}
