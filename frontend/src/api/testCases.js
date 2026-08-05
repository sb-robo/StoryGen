import { api } from './client'

export function updateTestCase(id, payload) {
  return api.patch(`/test-cases/${id}`, payload)
}

export function approveTestCase(id) {
  return api.post(`/test-cases/${id}/approve`)
}

export function rejectTestCase(id) {
  return api.post(`/test-cases/${id}/reject`)
}
