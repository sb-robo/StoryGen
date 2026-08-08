import { API_BASE, resolveUrl } from './config'

const TOKEN_KEY = 'storygen_access_token'
const REFRESH_KEY = 'storygen_refresh_token'

export function getAccessToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY)
}

export function setTokens({ access_token, refresh_token }) {
  localStorage.setItem(TOKEN_KEY, access_token)
  localStorage.setItem(REFRESH_KEY, refresh_token)
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

function formatDetail(detail) {
  if (!detail) return 'Request failed'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join('; ')
  }
  return JSON.stringify(detail)
}

let refreshPromise = null

async function refreshAccessToken() {
  const refresh_token = getRefreshToken()
  if (!refresh_token) throw new ApiError('Session expired', 401)

  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token }),
  })

  if (!response.ok) {
    clearTokens()
    throw new ApiError('Session expired', 401)
  }

  const data = await response.json()
  setTokens(data)
  return data.access_token
}

async function getValidToken() {
  const token = getAccessToken()
  if (token) return token
  if (getRefreshToken()) return refreshAccessToken()
  return null
}

async function authorizedFetch(path, options = {}) {
  const { auth = true, body, headers = {}, ...rest } = options
  const url = resolveUrl(path)
  const requestHeaders = { ...headers }

  if (auth) {
    const token = await getValidToken()
    if (!token) throw new ApiError('Not authenticated', 401)
    requestHeaders.Authorization = `Bearer ${token}`
  }

  const isFormData = body instanceof FormData
  if (body && !isFormData && !requestHeaders['Content-Type']) {
    requestHeaders['Content-Type'] = 'application/json'
  }

  let response = await fetch(url, {
    ...rest,
    headers: requestHeaders,
    body: isFormData ? body : body ? JSON.stringify(body) : undefined,
  })

  if (auth && response.status === 401 && getRefreshToken()) {
    if (!refreshPromise) {
      refreshPromise = refreshAccessToken().finally(() => {
        refreshPromise = null
      })
    }
    try {
      const newToken = await refreshPromise
      requestHeaders.Authorization = `Bearer ${newToken}`
      response = await fetch(url, {
        ...rest,
        headers: requestHeaders,
        body: isFormData ? body : body ? JSON.stringify(body) : undefined,
      })
    } catch {
      throw new ApiError('Session expired', 401)
    }
  }

  return response
}

export async function apiRequest(path, options = {}) {
  const response = await authorizedFetch(path, options)

  if (response.status === 204) return null

  const data = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(
      formatDetail(data?.detail) || response.statusText,
      response.status,
      data?.detail,
    )
  }
  return data
}

/** Fetch a binary/file response (e.g. CSV export). Returns { blob, filename }. */
export async function apiDownload(path, options = {}) {
  const response = await authorizedFetch(path, options)
  if (!response.ok) {
    const data = await response.json().catch(() => null)
    throw new ApiError(
      formatDetail(data?.detail) || response.statusText,
      response.status,
      data?.detail,
    )
  }

  const disposition = response.headers.get('content-disposition') || ''
  const match = disposition.match(/filename="?([^"]+)"?/i)
  const filename = match?.[1] || 'download'
  const blob = await response.blob()
  return { blob, filename }
}

/** Low-level authenticated fetch for streams (SSE) and non-JSON bodies. */
export function apiFetch(path, options = {}) {
  return authorizedFetch(path, options)
}

export const api = {
  get: (path, options) => apiRequest(path, { ...options, method: 'GET' }),
  post: (path, body, options) => apiRequest(path, { ...options, method: 'POST', body }),
  patch: (path, body, options) => apiRequest(path, { ...options, method: 'PATCH', body }),
  delete: (path, options) => apiRequest(path, { ...options, method: 'DELETE' }),
}
