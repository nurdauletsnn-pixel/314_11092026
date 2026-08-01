import axios from 'axios'

export const apiClient = axios.create({
  // VITE_API_URL задаётся в .env (локально) или в Environment Variables на Vercel (продакшен)
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Автоматически подставляем токен из localStorage/zustand во все запросы.
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Token ${token}`
  }
  return config
})

// На 401 — сбрасываем сессию и перенаправляем на экран входа.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem('auth_token')
      sessionStorage.removeItem('bi-crm-auth')
      window.location.href = '/'
    }
    return Promise.reject(error)
  }
)
