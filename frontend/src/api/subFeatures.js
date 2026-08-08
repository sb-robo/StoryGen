import { api } from './client'

export function getSubFeatureStatus(operationId) {
  return api.get(`/sub-features/status/${operationId}`)
}

export function getSubFeatureResult(operationId) {
  return api.get(`/sub-features/result/${operationId}`)
}

export function updateSubFeature(id, payload) {
  return api.patch(`/sub-features/${id}`, payload)
}

export function approveSubFeature(id) {
  return api.post(`/sub-features/${id}/approve`)
}

export function rejectSubFeature(id) {
  return api.post(`/sub-features/${id}/reject`)
}

export function reopenSubFeature(id) {
  return api.post(`/sub-features/${id}/reopen`)
}

export function generateStories(subFeatureId) {
  return api.post(`/sub-features/${subFeatureId}/stories/generate`)
}

export function listStories(subFeatureId, status) {
  const qs = status ? `?status=${status}` : ''
  return api.get(`/sub-features/${subFeatureId}/stories${qs}`)
}
