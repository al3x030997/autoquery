'use client'

import { createContext, useCallback, useEffect, useState, type ReactNode } from 'react'
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from '@/lib/auth'
import * as api from '@/lib/api'

interface AuthUser {
  email: string
}

interface AuthContextValue {
  user: AuthUser | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  login: async () => {},
  register: async () => {},
  logout: () => {},
})

function decodePayload(token: string): { sub: string; exp: number } | null {
  try {
    const payload = token.split('.')[1]
    return JSON.parse(atob(payload))
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  const setUserFromToken = useCallback((accessToken: string) => {
    const payload = decodePayload(accessToken)
    if (payload) {
      setUser({ email: payload.sub })
    }
  }, [])

  // Try to restore session on mount
  useEffect(() => {
    async function restore() {
      const access = getAccessToken()
      if (access) {
        const payload = decodePayload(access)
        if (payload && payload.exp * 1000 > Date.now()) {
          setUser({ email: payload.sub })
          setLoading(false)
          return
        }
      }
      // Try refresh
      const refresh = getRefreshToken()
      if (refresh) {
        try {
          const res = await api.refreshToken(refresh)
          setTokens(res.access_token, res.refresh_token)
          setUserFromToken(res.access_token)
        } catch {
          clearTokens()
        }
      }
      setLoading(false)
    }
    restore()
  }, [setUserFromToken])

  const loginFn = useCallback(async (email: string, password: string) => {
    const res = await api.login(email, password)
    setTokens(res.access_token, res.refresh_token)
    setUserFromToken(res.access_token)
  }, [setUserFromToken])

  const registerFn = useCallback(async (email: string, password: string) => {
    const res = await api.register(email, password)
    setTokens(res.access_token, res.refresh_token)
    setUserFromToken(res.access_token)
  }, [setUserFromToken])

  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login: loginFn, register: registerFn, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
