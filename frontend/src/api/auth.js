import { api, setTokens, clearTokens } from './client'

export async function login(email, password) {
  const data = await api.post('/auth/login', { email, password }, { auth: false })
  setTokens(data)
  return data
}

export async function register(name, email, password, confirm_password) {
  const data = await api.post(
    '/auth/register',
    { name, email, password, confirm_password },
    { auth: false },
  )
  setTokens(data)
  return data
}

export async function logout() {
  const refresh_token = localStorage.getItem('storygen_refresh_token')
  if (refresh_token) {
    try {
      await api.post('/auth/logout', { refresh_token }, { auth: false })
    } catch {
      // ignore
    }
  }
  clearTokens()
}

export async function getMe() {
  return api.get('/users/me')
}
