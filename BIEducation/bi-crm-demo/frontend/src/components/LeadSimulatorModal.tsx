import { useState } from 'react'
import toast from 'react-hot-toast'
import { X } from 'lucide-react'
import { mockBranches } from '../data/mockData'
import { apiClient } from '../api/client'
import { normalizeDeal } from '../services/dealAdapter'
import type { Deal } from '../types'

export type SimulatorScenario = 'standard' | 'cross_branch' | 'duplicate' | 'waitlist'

interface LeadSimulatorModalProps {
  currentBranchId: string | null
  onClose: () => void
  onSimulated: (deal: Deal) => void
}

const scenarios: Array<{ id: SimulatorScenario; title: string; description: string; icon: string }> = [
  {
    id: 'standard',
    title: 'Стандартный лид (Riviera)',
    description: 'Чистая сделка на текущий филиал (без кросс-филиала и дублей).',
    icon: '🎯',
  },
  {
    id: 'cross_branch',
    title: 'Кросс-филиальный лид',
    description: 'Лид из другого города/филиала — плашка гео-роутинга (раздел 8.5).',
    icon: '🌍',
  },
  {
    id: 'duplicate',
    title: 'Дубликат контакта',
    description: 'Телефон/ИИН, уже существующий в системе — плашка анти-дубля (раздел 7, Риск 4).',
    icon: '🔁',
  },
  {
    id: 'waitlist',
    title: 'Переполнение и Waitlist',
    description: 'Сделка в переполненную группу — статус WAITLIST #N (раздел 7, Риск 2).',
    icon: '⏳',
  },
]

export function LeadSimulatorModal({ currentBranchId, onClose, onSimulated }: LeadSimulatorModalProps) {
  const [selected, setSelected] = useState<SimulatorScenario>('standard')
  const [isRunning, setIsRunning] = useState(false)

  const handleRun = async () => {
    setIsRunning(true)
    try {
      const currentBranch = mockBranches.find((b) => b.id === currentBranchId) ?? mockBranches[0]
      const otherBranch = mockBranches.find((b) => b.id !== currentBranch?.id) ?? mockBranches[1]

      let payload: Record<string, unknown> = {
        pipeline: 'b2c_schools',
        branch: currentBranch?.code,
        grade_band: 'PRIMARY_SECONDARY',
      }

      // Сценарий 1: стандартный (Riviera)
      if (selected === 'standard') {
        payload = { ...payload, tariff: 'Стандарт' }
      }

      // Сценарий 2: кросс-филиальный (гео-роутинг)
      if (selected === 'cross_branch') {
        payload = {
          ...payload,
          branch: otherBranch?.code,
          source_city: otherBranch?.city,
          source_branch_requested: otherBranch?.code,
        }
      }

      // Сценарий 3: дубликат контакта — берём существующий контакт из системы.
      // Телефоны из generate_mock_data НЕ содержат '+77011112233' (там +7701100001 и т.д.),
      // поэтому жёстко зашитый номер не находился бы, и сценарий не срабатывал.
      if (selected === 'duplicate') {
        const contactsResponse = await apiClient.get('/contacts/')
        const contactsList: Array<{ id: string; phone: string; full_name: string }> = Array.isArray(contactsResponse.data)
          ? contactsResponse.data
          : []
        const existingContact = contactsList.find((c) => c.phone) ?? contactsList[0]
        if (!existingContact) {
          toast.error('Нет существующих контактов для сценария «Дубликат» — сначала создайте сделку')
          setIsRunning(false)
          return
        }
        payload = {
          ...payload,
          phone: existingContact.phone,
          // Плашка анти-дубля покажется если контакт существует
          contact_id: existingContact.id,
        }
      }

      // Сценарий 4: переполнение и waitlist
      if (selected === 'waitlist') {
        payload = { ...payload, grade_or_group: '1 класс' } // напрямую заполняем класс
      }

      // Отправляем запрос в API simulate-lead
      const response = await apiClient.post('/deals/simulate-lead/', payload)
      const deal = response.data?.deal ?? response.data

      // Мгновенное обновление UI (добавляем нормализованную сделку в локальный список)
      if (deal) {
        onSimulated(normalizeDeal(deal))
      }

      toast.success('⚡ Лид успешно симулирован и добавлен на доску', { icon: '⚡' })
      onClose()
    } catch (err: any) {
      const msg = err?.response?.data?.error || err?.message || 'Не удалось симулировать лид'
      toast.error(`Ошибка: ${msg}`)
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-slate-950/50 p-4">
      <div className="w-full max-w-2xl rounded-3xl bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-slate-400">Demо simulator</p>
            <h2 className="text-2xl font-bold text-slate-900">⚡ Симулировать лид</h2>
            <p className="mt-1 text-sm text-slate-500">
              Выберите сценарий для быстрой проверки бизнес-логики CRM.
            </p>
          </div>
          <button onClick={onClose} className="rounded-full p-2 hover:bg-slate-100">
            <X size={18} />
          </button>
        </div>

        <div className="mt-6 space-y-2">
          {scenarios.map((scenario) => (
            <button
              key={scenario.id}
              onClick={() => setSelected(scenario.id)}
              className={`w-full rounded-2xl border p-4 text-left transition ${
                selected === scenario.id
                  ? 'border-slate-900 bg-slate-50 shadow-sm'
                  : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="flex items-start gap-3">
                <span className="text-2xl">{scenario.icon}</span>
                <div>
                  <p className="text-sm font-semibold text-slate-900">{scenario.title}</p>
                  <p className="mt-0.5 text-xs text-slate-500">{scenario.description}</p>
                </div>
              </div>
            </button>
          ))}
        </div>

        <div className="mt-6 flex justify-end gap-3 border-t pt-4">
          <button onClick={onClose} className="rounded-xl border px-4 py-2 text-sm font-medium">
            Отмена
          </button>
          <button
            onClick={handleRun}
            disabled={isRunning}
            className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isRunning ? 'Запуск...' : '🚀 Запустить сценарий'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default LeadSimulatorModal