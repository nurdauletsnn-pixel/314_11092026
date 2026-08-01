import { useEffect } from 'react'
import { Toaster } from 'react-hot-toast'
import Dashboard from './components/Dashboard';
import LoginView from './components/LoginView';
import { useAuthStore } from './store/authStore';

function App() {
  const { isAuthenticated, isLoading, user, fetchMe, logout } = useAuthStore()

  // При старте проверяем сессию (если токен сохранён в localStorage).
  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    if (token && !isAuthenticated) {
      fetchMe()
    }
  }, [isAuthenticated, fetchMe])

  // Пока проверяем токен / грузим /me — показываем спиннер.
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="text-sm font-medium text-slate-500">Загрузка...</div>
      </div>
    )
  }

  if (!isAuthenticated || !user) {
    return <LoginView />
  }

  return (
    <>
      <Toaster position="top-right" toastOptions={{ className: 'rounded-2xl border border-slate-200 shadow-lg' }} />
      <div className="fixed right-4 top-4 z-50 flex items-center gap-3 rounded-full border border-slate-200 bg-white/90 px-3 py-1.5 text-xs shadow-sm backdrop-blur">
        <span className="font-semibold text-slate-700">{user.username}</span>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-600">
          {user.role}
        </span>
        <button
          onClick={logout}
          className="rounded-full px-2.5 py-1 font-medium text-rose-600 transition hover:bg-rose-50"
        >
          Выйти
        </button>
      </div>
      <Dashboard />
    </>
  )
}

export default App