export const API_ORIGIN = import.meta.env.VITE_API_ORIGIN ?? ''
export const API_BASE = `${API_ORIGIN}/api/v1`

export function resolveUrl(path) {
  if (!path) return API_BASE
  if (path.startsWith('http')) return path
  if (path.startsWith('/api/v1')) return `${API_ORIGIN}${path}`
  return `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`
}
