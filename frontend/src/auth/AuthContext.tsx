import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import http, { tokenStore } from '../api/client'
import type { ApiResponse, CurrentUser } from '../api/types'

interface AuthState {
  user: CurrentUser | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  has: (perm: string) => boolean
}

const AuthContext = createContext<AuthState>(null as unknown as AuthState)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchMe = async () => {
    try {
      const { data } = await http.get<ApiResponse<CurrentUser>>('/auth/me')
      setUser(data.data)
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (tokenStore.get()) {
      fetchMe()
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (username: string, password: string) => {
    const { data } = await http.post<ApiResponse<{ access_token: string }>>('/auth/login', {
      username,
      password,
    })
    tokenStore.set(data.data.access_token)
    await fetchMe()
  }

  const logout = () => {
    tokenStore.clear()
    setUser(null)
    location.href = '/login'
  }

  const has = (perm: string) => {
    if (!user) return false
    return user.permissions.includes('*') || user.permissions.includes(perm)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, has }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
