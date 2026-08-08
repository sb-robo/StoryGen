import { api } from './client'

export function getMe() {
  return api.get('/users/me')
}

export function updateMe(data) {
  return api.patch('/users/me', data)
}

export function changePassword(current_password, password, confirm_password) {
  return api.post('/auth/change-password', { current_password, password, confirm_password })
}
