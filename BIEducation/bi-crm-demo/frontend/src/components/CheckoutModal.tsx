import type { Deal, Tariff, Child, Parent } from '../types'

interface CheckoutModalProps {
  deal: Deal | null
  parent: Parent | null
  child: Child | null
  tariff: Tariff | null
  onCancel: () => void
  onConfirm: () => void
}

export function CheckoutModal({ deal, parent, child, tariff, onCancel, onConfirm }: CheckoutModalProps) {
  if (!deal || !parent || !child || !tariff) return null

  const finalTotal = deal.expectedRevenue + (deal.addons.food ? 25000 : 0) + (deal.addons.transport ? 15000 : 0) + tariff.entrance_fee

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/60 p-4">
      <div className="w-full max-w-2xl rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-slate-500">Enrollment flow</p>
            <h3 className="text-2xl font-semibold text-slate-900">Confirm contract generation</h3>
          </div>
        </div>

        <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <p className="text-sm font-semibold text-slate-700">Parent</p>
              <p className="mt-1 text-slate-900">{parent.name}</p>
              <p className="text-sm text-slate-500">{parent.phone}</p>
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-700">Child</p>
              <p className="mt-1 text-slate-900">{child.name}</p>
              <p className="text-sm text-slate-500">{child.gradeOrGroup}</p>
            </div>
          </div>
        </div>

        <div className="mt-6 grid gap-3 rounded-2xl border border-slate-200 p-4 text-sm text-slate-600">
          <div className="flex items-center justify-between">
            <span>Selected tariff</span>
            <span className="font-semibold text-slate-900">{tariff.name}</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Entrance fee</span>
            <span className="font-semibold text-slate-900">{tariff.entrance_fee.toLocaleString('ru-RU')} ₸</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Addons</span>
            <span className="font-semibold text-slate-900">{[deal.addons.food ? 'Food' : null, deal.addons.transport ? 'Transport' : null].filter(Boolean).join(', ') || 'None'}</span>
          </div>
          <div className="flex items-center justify-between border-t border-slate-200 pt-3 text-base">
            <span>Final total</span>
            <span className="font-semibold text-slate-900">{finalTotal.toLocaleString('ru-RU')} ₸</span>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button onClick={onCancel} className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700">Cancel drop</button>
          <button onClick={onConfirm} className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white">Confirm & generate contract</button>
        </div>
      </div>
    </div>
  )
}
