import { api } from './client'

export function extractFeatures(brdId) {
  return api.post(`/features/extract/${brdId}`)
}

export function getFeatureStatus(operationId) {
  return api.get(`/features/status/${operationId}`)
}

export function getFeatureResult(operationId) {
  return api.get(`/features/result/${operationId}`)
}

export function updateFeature(id, payload) {
  return api.patch(`/features/${id}`, payload)
}

export function approveFeature(id) {
  return api.post(`/features/${id}/approve`)
}

export function rejectFeature(id) {
  return api.post(`/features/${id}/reject`)
}

export function reopenFeature(id) {
  return api.post(`/features/${id}/reopen`)
}

export function refineFeatureFromAnswers(id) {
  return api.post(`/features/${id}/refine-from-answers`)
}

export function listSubFeatures(featureId, status) {
  const qs = status ? `?status=${status}` : ''
  return api.get(`/features/${featureId}/sub-features${qs}`)
}
