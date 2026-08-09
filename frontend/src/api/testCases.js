import { api } from './client'

export function generateTestCases(storyId) {
  return api.post(`/test-cases/generate/${storyId}`)
}

export function getTestCaseStatus(operationId) {
  return api.get(`/test-cases/status/${operationId}`)
}

export function getTestCaseResult(operationId) {
  return api.get(`/test-cases/result/${operationId}`)
}

export function updateTestCase(id, payload) {
  return api.patch(`/test-cases/${id}`, payload)
}

export function approveTestCase(id) {
  return api.post(`/test-cases/${id}/approve`)
}

export function rejectTestCase(id) {
  return api.post(`/test-cases/${id}/reject`)
}

export function reopenTestCase(id) {
  return api.post(`/test-cases/${id}/reopen`)
}
