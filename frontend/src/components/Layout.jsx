import { Link } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { JobsButton, JobsDrawer } from './JobsDrawer'
import { ToastStack } from './ToastStack'
import { ThemeToggle } from '../theme/ThemeToggle'

export function Layout({ children }) {
  const { user, logout } = useAuth()

  return (
    <div className="layout">
      <header className="app-header">
        <Link to="/" className="brand">
          StoryGen
        </Link>
        <div className="header-actions">
          <ThemeToggle />
          {user && (
            <>
              {user.is_admin && (
                <Link to="/admin/operations" className="btn btn-ghost">
                  Ops
                </Link>
              )}
              <JobsButton />
              <Link to="/profile" className="user-label" title="Profile">
                {user.name}
              </Link>
              <button type="button" className="btn btn-ghost" onClick={logout}>
                Log out
              </button>
            </>
          )}
        </div>
      </header>
      <main className="app-main app-main-wide">{children}</main>
      <JobsDrawer />
      <ToastStack />
    </div>
  )
}
