import { useCallback, useEffect, useMemo, useState } from 'react'
import { getAccessToken, clearTokens } from '../api/client'
import * as authApi from '../api/auth'
import { AuthContext } from './useAuth'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadUser = useCallback(async () => {
    if (!getAccessToken()) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const me = await authApi.getMe()
      setUser(me)
    } catch {
      clearTokens()
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadUser()
  }, [loadUser])

  const login = useCallback(async (email, password) => {
    const data = await authApi.login(email, password)
    setUser(data.user)
    return data
  }, [])

  const register = useCallback(async (name, email, password, confirmPassword) => {
    const data = await authApi.register(name, email, password, confirmPassword)
    setUser(data.user)
    return data
  }, [])

  const logout = useCallback(async () => {
    await authApi.logout()
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, register, logout, refreshUser: loadUser }),
    [user, loading, login, register, logout, loadUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
