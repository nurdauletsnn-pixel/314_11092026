import type { PaymentScheduleEntry, Task } from '../types'

interface PaymentScheduleListProps {
  schedules: PaymentScheduleEntry[] | undefined
  canMarkPaid: boolean
  onMarkPaid: (scheduleId: string) => void
  tasks?: Task[]
}

const statusStyles: Record<PaymentScheduleEntry['status'], string> = {
  PAID: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  PENDING: 'bg-slate-50 text-slate-600 border-slate-200',
  OVERDUE: 'bg-rose-50 text-rose-700 border-rose-200',
}

const statusLabels: Record<PaymentScheduleEntry['status'], string> = {
  PAID: 'Оплачен',
  PENDING: 'Ожидает',
  OVERDUE: 'Просрочен',
}

export function PaymentScheduleList({ schedules, canMarkPaid, onMarkPaid, tasks = [] }: PaymentScheduleListProps) {
  if (!schedules || schedules.length === 0) {
    return (
      <div className="rounded-2xl bg-slate-50 p-6 text-center text-sm text-slate-500">
        График платежей ещё не сгенерирован.
        <br />
        <span className="text-xs text-slate-400">Выберите тариф на вкладке «Тариф и доп. услуги»</span>
      </div>
    )
  }

  const today = new Date()
  today.setHours(0, 0, 0, 0)

  return (
    <div className="space-y-2">
      {schedules.map((schedule) => {
        const dueDate = new Date(schedule.due_date + 'T00:00:00')
        const isOverdue = schedule.status === 'PENDING' && dueDate < today
        const effectiveStatus: PaymentScheduleEntry['status'] = isOverdue ? 'OVERDUE' : schedule.status

        // Связанные задачи для этого платежа (D-3 напоминание/просрочка)
        const relatedTasks = tasks.filter((t) =>
          t.title.includes(schedule.title) ||
          (effectiveStatus === 'OVERDUE' && (t.title.includes('Просрочен платёж') || t.title.includes('напоминание об оплате')))
        )

        return (
          <div key={schedule.id}>
            <div
              className={`flex items-center justify-between rounded-2xl border p-3 ${statusStyles[effectiveStatus]}`}
            >
              <div>
                <p className="text-sm font-semibold">{schedule.title}</p>
                <p className="text-xs opacity-70">
                  {new Date(schedule.due_date).toLocaleDateString('ru-RU')}
                  {isOverdue && ' • просрочено'}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-bold">
                  {Number(schedule.amount).toLocaleString('ru-RU')} ₸
                </span>
                <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${statusStyles[effectiveStatus]}`}>
                  {statusLabels[effectiveStatus]}
                </span>
                {canMarkPaid && schedule.status !== 'PAID' && (
                  <button
                    onClick={() => onMarkPaid(schedule.id)}
                    className="flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                  >
                    ✓ Отметить оплаченным
                  </button>
                )}
              </div>
            </div>

            {/* Связанные задачи (раздел 6 п.4): напоминание D-3 / просрочка D+2 */}
            {relatedTasks.length > 0 && (
              <div className="mt-1 space-y-1 pl-4">
                {relatedTasks.map((task) => (
                  <div key={task.id} className="flex items-center gap-2 text-xs text-slate-500">
                    <span className="text-slate-400">→</span>
                    <span className={task.priority === 'HIGH' ? 'text-rose-600 font-semibold' : ''}>
                      {task.priority === 'HIGH' && '🔴 '}
                      {task.title}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default PaymentScheduleList