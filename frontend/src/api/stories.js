import { api } from './client'

export function getStoryStatus(operationId) {
  return api.get(`/stories/status/${operationId}`)
}

export function getStoryResult(operationId) {
  return api.get(`/stories/result/${operationId}`)
}

export function updateStory(id, payload) {
  return api.patch(`/stories/${id}`, payload)
}

export function approveStory(id) {
  return api.post(`/stories/${id}/approve`)
}

export function rejectStory(id) {
  return api.post(`/stories/${id}/reject`)
}

export function estimatePoints(storyId) {
  return api.post(`/stories/${storyId}/points/estimate`)
}

export function updatePoints(storyId, payload) {
  return api.patch(`/stories/${storyId}/points`, payload)
}

export function approvePoints(storyId) {
  return api.post(`/stories/${storyId}/points/approve`)
}

export function generateTestCases(storyId) {
  return api.post(`/stories/${storyId}/test-cases/generate`)
}

export function listTestCases(storyId, status) {
  const qs = status ? `?status=${status}` : ''
  return api.get(`/stories/${storyId}/test-cases${qs}`)
}
