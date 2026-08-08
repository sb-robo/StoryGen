import { api } from './client'

export function cancelOperation(operationId) {
  return api.post(`/operations/${operationId}/cancel`)
}

export function retryOperation(operationId) {
  return api.post(`/operations/${operationId}/retry`)
}
