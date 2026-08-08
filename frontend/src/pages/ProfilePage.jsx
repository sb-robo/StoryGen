import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import * as usersApi from '../api/users'
import { useAuth } from '../auth/useAuth'

export function ProfilePage() {
  const { user, setUser, logout } = useAuth()
  const navigate = useNavigate()

  const [name, setName] = useState(user?.name ?? '')
  const [email, setEmail] = useState(user?.email ?? '')
  const [profileError, setProfileError] = useState('')
  const [profileSuccess, setProfileSuccess] = useState('')
  const [savingProfile, setSavingProfile] = useState(false)

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [changingPassword, setChangingPassword] = useState(false)

  async function handleProfileSubmit(e) {
    e.preventDefault()
    setProfileError('')
    setProfileSuccess('')
    const payload = {}
    if (name.trim() && name.trim() !== user?.name) payload.name = name.trim()
    if (email.trim() && email.trim() !== user?.email) payload.email = email.trim()
    if (Object.keys(payload).length === 0) {
      setProfileSuccess('Nothing to update.')
      return
    }
    setSavingProfile(true)
    try {
      const updated = await usersApi.updateMe(payload)
      setUser(updated)
      setProfileSuccess('Profile updated.')
    } catch (err) {
      setProfileError(err.message || 'Update failed')
    } finally {
      setSavingProfile(false)
    }
  }

  async function handlePasswordSubmit(e) {
    e.preventDefault()
    setPasswordError('')
    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match')
      return
    }
    setChangingPassword(true)
    try {
      await usersApi.changePassword(currentPassword, newPassword, confirmPassword)
      await logout()
      navigate('/login', { replace: true, state: { passwordChanged: true } })
    } catch (err) {
      setPasswordError(err.message || 'Password change failed')
    } finally {
      setChangingPassword(false)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Profile</h1>
        <p>Update your account details or change your password.</p>
      </div>

      <section className="panel">
        <h2>Account details</h2>
        <form className="profile-form" onSubmit={handleProfileSubmit}>
          <label className="field">
            <span>Display name</span>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              minLength={3}
              maxLength={100}
              required
            />
          </label>
          <label className="field">
            <span>Email</span>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          {profileError && <p className="form-error">{profileError}</p>}
          {profileSuccess && <p className="form-success">{profileSuccess}</p>}
          <div className="profile-form-actions">
            <button type="submit" className="btn btn-primary" disabled={savingProfile}>
              {savingProfile ? 'Saving…' : 'Save changes'}
            </button>
          </div>
        </form>
      </section>

      <section className="panel">
        <h2>Change password</h2>
        <p className="empty-hint">Changing your password will sign you out of all sessions.</p>
        <form className="profile-form" onSubmit={handlePasswordSubmit}>
          <label className="field">
            <span>Current password</span>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          <label className="field">
            <span>New password</span>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
              required
            />
          </label>
          <label className="field">
            <span>Confirm new password</span>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              required
            />
          </label>
          {passwordError && <p className="form-error">{passwordError}</p>}
          <div className="profile-form-actions">
            <button type="submit" className="btn btn-primary" disabled={changingPassword}>
              {changingPassword ? 'Changing…' : 'Change password'}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}
