import { useEffect, useMemo, useState } from 'react'
import { TrendingUp, Users, Clock } from 'lucide-react'
import { isHQAdmin } from '../services/accessControl'
import { apiClient } from '../api/client'
import { normalizeDeal } from '../services/dealAdapter'
import type { CurrentUser, Deal } from '../types'

interface AnalyticsWidgetProps {
  user: CurrentUser | null
}

export function AnalyticsWidget({ user }: AnalyticsWidgetProps) {
  const [serverDeals, setServerDeals] = useState<Deal[]>([])

  // Подтягиваем сделки с бэкенда для HQ_ADMIN и нормализуем их
  useEffect(() => {
    if (!isHQAdmin(user)) return
    apiClient.get('/deals/').then((response) => {
      const data = response.data
      if (Array.isArray(data)) {
        setServerDeals(data.map((d) => normalizeDeal(d)))
      }
    }).catch(() => {})
  }, [user])

  const deals: Deal[] = useMemo(() => serverDeals, [serverDeals])

  // Forecast Revenue — сумма активных сделок
  const forecastRevenue = useMemo(() => {
    return deals
      .filter((d) => d.status !== 'LOST' && d.status !== 'WAITLIST')
      .reduce((sum, d) => sum + (d.expectedRevenue || d.totalAmount || 0), 0)
  }, [deals])

  // Реальные филиалы из сделок (id + название из бэкенда)
  const branchesFromDeals = useMemo(() => {
    const map = new Map<string, { id: string; name: string }>()
    for (const d of deals) {
      if (!map.has(d.branchId)) {
        map.set(d.branchId, { id: d.branchId, name: d.branchName ?? mockBranchNameById(d.branchId) })
      }
    }
    return Array.from(map.values())
  }, [deals])

  // Branch Conversion — конверсия по каждому филиалу
  const branchConversion = useMemo(() => {
    return branchesFromDeals.map((branch) => {
      const branchDeals = deals.filter((d) => d.branchId === branch.id)
      const won = branchDeals.filter((d) => d.status === 'WON').length
      const conversion = branchDeals.length > 0 ? Math.round((won / branchDeals.length) * 100) : 0
      return { branch, total: branchDeals.length, won, conversion }
    })
  }, [deals, branchesFromDeals])

  // Waitlist Bottleneck — кол-во в очереди по филиалам
  const waitlistByBranch = useMemo(() => {
    return branchesFromDeals.map((branch) => ({
      branch,
      count: deals.filter((d) => d.branchId === branch.id && (d.isWaitlisted || d.status === 'WAITLIST')).length,
    }))
  }, [deals, branchesFromDeals])

  // Fallback-имя филиала (если бэкенд не вернул branchName)
  function mockBranchNameById(id: string): string {
    return `Филиал #${id}`
  }

  if (!isHQAdmin(user)) {
    return null
  }

  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">HQ Analytics</p>
          <h2 className="mt-1 text-lg font-bold text-slate-900">Сквозная аналитика по всем филиалам</h2>
        </div>
        <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-500">
          Только HQ_ADMIN
        </span>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-3 md:divide-x md:divide-slate-100">
        {/* Forecast Revenue */}
        <div className="md:pr-6">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
              <TrendingUp size={16} />
            </span>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Forecast Revenue</p>
          </div>
          <p className="mt-3 text-2xl font-bold text-emerald-600">
            {forecastRevenue.toLocaleString('ru-RU')} ₸
          </p>
          <p className="mt-1 text-sm font-medium text-slate-500">
            Активные сделки (не LOST / WAITLIST)
          </p>
        </div>

        {/* Branch Conversion */}
        <div className="md:px-6">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-sky-50 text-sky-600">
              <Users size={16} />
            </span>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Branch Conversion</p>
          </div>
          <div className="mt-3 space-y-2.5">
            {branchConversion.map(({ branch, total, won, conversion }) => (
              <div key={branch.id}>
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium text-slate-700 truncate">{branch.name}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                    conversion >= 50 ? 'bg-emerald-50 text-emerald-700' : conversion > 0 ? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-500'
                  }`}>
                    {won}/{total} · {conversion}%
                  </span>
                </div>
                <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full rounded-full ${conversion >= 50 ? 'bg-emerald-500' : conversion > 0 ? 'bg-amber-500' : 'bg-slate-300'}`}
                    style={{ width: `${Math.max(conversion, 4)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Waitlist Bottleneck */}
        <div className="md:pl-6">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-amber-50 text-amber-600">
              <Clock size={16} />
            </span>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Waitlist Bottleneck</p>
          </div>
          <div className="mt-3 space-y-2.5">
            {waitlistByBranch.map(({ branch, count }) => (
              <div key={branch.id} className="flex items-center justify-between text-sm">
                <span className="font-medium text-slate-700 truncate">{branch.name}</span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                  count > 0 ? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-500'
                }`}>
                  ⏳ {count}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default AnalyticsWidget