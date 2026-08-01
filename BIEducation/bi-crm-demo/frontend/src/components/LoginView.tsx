import { useState, type FormEvent } from 'react'
import { useAuthStore } from '../store/authStore'

export function LoginView() {
  const { login, isLoading, error } = useAuthStore()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    await login(username, password)
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-md rounded-3xl bg-white p-8 shadow-sm">
        <div className="text-center">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">BI Education CRM</p>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">Вход в систему</h1>
          <p className="mt-1 text-sm text-slate-500">
            Демо-доступ: HQ_ADMIN / BRANCH_DIRECTOR / SALES_MANAGER
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-600">Имя пользователя</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              className="mt-1 w-full rounded-xl border border-slate-200 p-2.5 text-sm focus:border-slate-400 focus:outline-none"
              placeholder="hq_admin"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600">Пароль</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              className="mt-1 w-full rounded-xl border border-slate-200 p-2.5 text-sm focus:border-slate-400 focus:outline-none"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700 border border-rose-200">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading || !username || !password}
            className="w-full rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading ? 'Вход...' : 'Войти'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default LoginView