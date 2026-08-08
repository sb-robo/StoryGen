import { api } from './client'

function toQuery(params = {}) {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    search.set(key, String(value))
  })
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

export function listOperations(params = {}) {
  return api.get(`/operations${toQuery(params)}`)
}

export function cancelOperation(operationId) {
  return api.post(`/operations/${operationId}/cancel`)
}

export function retryOperation(operationId) {
  return api.post(`/operations/${operationId}/retry`)
}
