import { api } from './client'

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

export function generateSubFeatures(featureId) {
  return api.post(`/features/${featureId}/sub-features/generate`)
}

export function listSubFeatures(featureId, status) {
  const qs = status ? `?status=${status}` : ''
  return api.get(`/features/${featureId}/sub-features${qs}`)
}
