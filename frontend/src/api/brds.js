import { api } from './client'

export function listBrds(params = {}) {
  const query = new URLSearchParams()
  if (params.page) query.set('page', params.page)
  if (params.page_size) query.set('page_size', params.page_size)
  if (params.status) query.set('status', params.status)
  const qs = query.toString()
  return api.get(`/brds${qs ? `?${qs}` : ''}`)
}

export function getBrd(id, includeText = false) {
  return api.get(`/brds/${id}?include_text=${includeText}`)
}

export function uploadBrd(name, file) {
  const form = new FormData()
  form.append('name', name)
  form.append('file', file)
  return api.post('/brds/upload', form)
}

export function extractFeatures(brdId) {
  return api.post(`/brds/${brdId}/features/extract`)
}

export function listFeatures(brdId, status) {
  const qs = status ? `?status=${status}` : ''
  return api.get(`/brds/${brdId}/features${qs}`)
}

export function reparseBrd(id) {
  return api.post(`/brds/${id}/reparse`)
}

export function deleteBrd(id) {
  return api.delete(`/brds/${id}`)
}
