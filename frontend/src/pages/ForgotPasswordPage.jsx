import { useState } from 'react'
import { Link } from 'react-router-dom'
import * as authApi from '../api/auth'
import { ThemeToggle } from '../theme/ThemeToggle'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [debugToken, setDebugToken] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setMessage('')
    setDebugToken(null)
    setLoading(true)
    try {
      const data = await authApi.forgotPassword(email)
      setMessage(data.message || 'If that email exists, a reset link has been sent.')
      if (data.reset_token) setDebugToken(data.reset_token)
    } catch (err) {
      setError(err.message || 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <ThemeToggle className="theme-toggle-corner" />
      <div className="auth-card">
        <h1>Forgot password</h1>
        <p className="auth-subtitle">
          If an account exists for that email, we send a reset link (when email is configured).
        </p>
        <form onSubmit={handleSubmit}>
          <label className="field">
            <span>Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </label>
          {error && <p className="form-error">{error}</p>}
          {message && <p className="form-success">{message}</p>}
          {debugToken && (
            <p className="auth-debug-token">
              DEBUG token (local only):{' '}
              <Link to={`/reset-password?token=${encodeURIComponent(debugToken)}`}>
                Continue to reset
              </Link>
            </p>
          )}
          <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
            {loading ? 'Sending…' : 'Send reset link'}
          </button>
        </form>
        <p className="auth-footer">
          <Link to="/login">Back to sign in</Link>
        </p>
      </div>
    </div>
  )
}
