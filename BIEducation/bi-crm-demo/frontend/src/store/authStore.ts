import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { apiClient } from '../api/client'
import type { CurrentUser } from '../types'

interface AuthState {
  token: string | null
  user: CurrentUser | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  login: (username: string, password: string) => Promise<boolean>
  fetchMe: () => Promise<void>
  logout: () => void
  setError: (message: string | null) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (username, password) => {
        set({ isLoading: true, error: null })
        try {
          const response = await apiClient.post('/auth/token/', { username, password })
          const { token, user } = response.data
          localStorage.setItem('auth_token', token)
          set({ token, user, isAuthenticated: true, isLoading: false })
          return true
        } catch (err: any) {
          const message =
            err?.response?.data?.non_field_errors?.[0] ||
            err?.response?.data?.detail ||
            'Неверный логин или пароль'
          set({ error: message, isLoading: false })
          return false
        }
      },

      fetchMe: async () => {
        const token = get().token || localStorage.getItem('auth_token')
        if (!token) return
        set({ isLoading: true })
        try {
          const response = await apiClient.get('/me/')
          set({ user: response.data, isAuthenticated: true, isLoading: false })
        } catch {
          get().logout()
        }
      },

      logout: () => {
        localStorage.removeItem('auth_token')
        set({ token: null, user: null, isAuthenticated: false, isLoading: false, error: null })
      },

      setError: (message) => set({ error: message }),
    }),
    {
      name: 'bi-crm-auth',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)