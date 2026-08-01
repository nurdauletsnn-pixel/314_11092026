// import { useState } from 'react';
// import { BarChart3, Filter, PlusCircle, Sparkles } from 'lucide-react';
// import { mockDeals } from '../data/mockData';
// import type { Deal } from '../types';
// import KanbanBoard from './KanbanBoard'; // Импортируем KanbanBoard сверху

// function Dashboard() {
//   const deals = mockDeals;

//   return (
//     <div className="p-6">
//       <h1 className="text-2xl font-bold mb-4">CRM Dashboard</h1>
//       {/* Передаем сделки в компонент KanbanBoard */}
//       <KanbanBoard deals={deals} />
//     </div>
//   );
// }

// export default Dashboard;

import { useEffect, useMemo, useRef, useState } from 'react';
import { PlusCircle } from 'lucide-react';
import { mockBranches } from '../data/mockData';
import type { Deal, PipelineId, Task, PaymentScheduleEntry } from '../types';
import { useAuthStore } from '../store/authStore';
import { apiClient } from '../api/client';
import { canSwitchBranch, getFixedBranchId } from '../services/accessControl';
import { normalizeDeal } from '../services/dealAdapter';
import KanbanBoard from './KanbanBoard';
import DealModal from './DealModal';
import LeadSimulatorModal from './LeadSimulatorModal';
import AnalyticsWidget from './AnalyticsWidget';

const pipelineTabs: { id: PipelineId; label: string }[] = [
  { id: 'school', label: 'B2C School' },
  { id: 'kindergarten', label: 'B2C Kindergarten' },
  { id: 'b2b', label: 'B2B' },
];

function Dashboard() {
  const user = useAuthStore((s) => s.user)
  const [deals, setDeals] = useState<Deal[]>([]);
  // Симулятор демо-лидов (Фаза 6)
  const [isSimulating, setIsSimulating] = useState(false);
  const [selectedPipeline, setSelectedPipeline] = useState<PipelineId>('school');
  // Селектор филиалов доступен только HQ_ADMIN; для остальных филиал зафиксирован (раздел 8.2/8.5).
  const fixedBranchId = getFixedBranchId(user);
  const [selectedBranchId, setSelectedBranchId] = useState<string>(fixedBranchId ?? 'all');
  const [branchMenuOpen, setBranchMenuOpen] = useState(false);
  const [editingDeal, setEditingDeal] = useState<Deal | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  // Виджет задач и просрочек (раздел 6 п.4 + раздел 7 Риск 2)
  const [tasks, setTasks] = useState<Task[]>([]);
  const [overduePayments, setOverduePayments] = useState<PaymentScheduleEntry[]>([]);
  const [showWidget, setShowWidget] = useState(false);

  // Автозакрытие выпадающих окон: клик вне области (mousedown на document) + уход курсора.
  const branchMenuRef = useRef<HTMLDivElement | null>(null);
  const widgetRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleGlobalMouseDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if (branchMenuRef.current && !branchMenuRef.current.contains(target)) {
        setBranchMenuOpen(false);
      }
      if (widgetRef.current && !widgetRef.current.contains(target)) {
        setShowWidget(false);
      }
    };
    document.addEventListener('mousedown', handleGlobalMouseDown);
    return () => document.removeEventListener('mousedown', handleGlobalMouseDown);
  }, []);

  useEffect(() => {
    // Сделки, доступные текущему пользователю (бэкенд фильтрует по роли/филиалу).
    apiClient.get('/deals/')
      .then((response) => {
        const rawList = Array.isArray(response.data) ? response.data : [];
        setDeals(rawList.map((d) => normalizeDeal(d)));
      })
      .catch(() => {});

    // Задачи, доступные текущему пользователю (с фильтрацией по роли на бэкенде).
    apiClient.get('/tasks/').then((response) => setTasks(response.data)).catch(() => {});

    // Просроченные платежи.
    apiClient.get('/payment-schedules/', { params: { status: 'OVERDUE' } })
      .then((response) => setOverduePayments(response.data))
      .catch(() => {});
  }, []);

  // Если у пользователя зафиксирован филиал — всегда фильтруем по нему.
  useEffect(() => {
    if (fixedBranchId) {
      setSelectedBranchId(fixedBranchId);
    }
  }, [fixedBranchId]);

  // Drag-and-Drop: оптимистичное перемещение карточки между колонками канбана.
  useEffect(() => {
    const handleStageChanged = (event: Event) => {
      const detail = (event as CustomEvent<{ dealId: string; stageId: string; status?: Deal['status'] }>).detail;
      if (!detail) return;
      // Меняем stageId И синхронизируем status, чтобы метрики
      // (Closed / won, Waitlisted, Projected) пересчитались мгновенно.
      // status приходит из KanbanBoard (enrolled → WON, lost → LOST, иначе ACTIVE).
      setDeals((prev) =>
        prev.map((d) => {
          if (d.id !== detail.dealId) return d;
          const newStatus: Deal['status'] = detail.status ?? 'ACTIVE';
          return {
            ...d,
            stageId: detail.stageId,
            status: newStatus,
            // Waitlist-флаг сбрасывается при перетаскивании (активные/won/lost).
            isWaitlisted: false,
          } as Deal;
        })
      );
    };
    // Rollback: сервер вернул ошибку — перезаписываем весь список актуальными данными.
    const handleDealsReplaced = (event: Event) => {
      const detail = (event as CustomEvent<{ deals: Deal[] }>).detail;
      if (!detail?.deals) return;
      setDeals(detail.deals);
    };
    window.addEventListener('deal:stage-changed', handleStageChanged);
    window.addEventListener('deals:replaced', handleDealsReplaced);
    return () => {
      window.removeEventListener('deal:stage-changed', handleStageChanged);
      window.removeEventListener('deals:replaced', handleDealsReplaced);
    };
  }, []);

  const filteredDeals = useMemo(() => {
    return deals.filter((d) => {
      if (d.pipelineId !== selectedPipeline) return false;
      if (selectedBranchId !== 'all' && d.branchId !== selectedBranchId) return false;
      return true;
    });
  }, [deals, selectedPipeline, selectedBranchId]);

  const stats = useMemo(() => {
    const visible = filteredDeals.length;
    const closedWon = filteredDeals.filter((d) => d.status === 'WON').length;
    const waitlisted = filteredDeals.filter((d) => d.isWaitlisted).length;
    const projectedValue = filteredDeals
      .filter((d) => d.status !== 'LOST')
      .reduce((sum, d) => sum + (d.expectedRevenue || 0), 0);
    return { visible, closedWon, waitlisted, projectedValue };
  }, [filteredDeals]);

  const selectedBranchName =
    selectedBranchId === 'all'
      ? 'All branches'
      : mockBranches.find((b) => b.id === selectedBranchId)?.name ?? 'All branches';

  const handleSaveDeal = (payload: Partial<Deal> & { id?: string }) => {
    if (payload.id) {
      setDeals((prev) => prev.map((d) => (d.id === payload.id ? { ...d, ...payload } as Deal : d)));
    }
    setEditingDeal(null);
  };

  const handleCreateDeal = (payload: Partial<Deal>) => {
    const newDeal: Deal = {
      id: `d${Date.now()}`,
      status: 'ACTIVE',
      pipelineId: selectedPipeline,
      stageId: 'new',
      hasFood: false,
      hasTransport: false,
      addons: { food: false, transport: false },
      isWaitlisted: false,
      totalAmount: 0,
      expectedRevenue: 0,
      tasks: [],
      history: [],
      ...payload,
    } as Deal;
    setDeals((prev) => [newDeal, ...prev]);
    setIsCreating(false);
  };

  const handleDeleteDeal = (dealId: string) => {
    setDeals((prev) => prev.filter((d) => d.id !== dealId));
    setEditingDeal(null);
  };

  // Симулятор: LeadSimulatorModal уже возвращает нормализованный Deal (Фаза 6).
  const handleSimulatedDeal = (simulated: Deal) => {
    setDeals((prev) => [simulated, ...prev]);
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-7xl space-y-4">
        {/* Header card */}
        <div className="rounded-3xl bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">BI Education CRM</p>
              <h1 className="mt-1 text-2xl font-bold text-slate-900">BI Education — Управление продажами</h1>
              <p className="mt-1 text-sm text-slate-500">
                CRM для школ Riviera, Quantum и садов ALDI BI с воронками и автоматизацией.
              </p>
            </div>
            <div className="flex items-center gap-3">
              {/* Селектор филиалов доступен ТОЛЬКО HQ_ADMIN (раздел 8.2 «Просмотр сделок»). Для
                  остальных филиал зафиксирован и показан как статичный бейдж. */}
              {canSwitchBranch(user) ? (
                <div
                  ref={branchMenuRef}
                  className="relative"
                  onMouseLeave={() => setBranchMenuOpen(false)}
                >
                  <button
                    onClick={() => setBranchMenuOpen((v) => !v)}
                    className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm"
                  >
                    {selectedBranchName}
                    <span className="text-slate-400">▾</span>
                  </button>
                  {branchMenuOpen && (
                    <div className="absolute right-0 z-10 mt-2 w-52 rounded-2xl border border-slate-100 bg-white p-1 shadow-lg">
                      <button
                        onClick={() => { setSelectedBranchId('all'); setBranchMenuOpen(false); }}
                        className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm ${selectedBranchId === 'all' ? 'bg-blue-500 text-white' : 'text-slate-700 hover:bg-slate-50'}`}
                      >
                        All branches {selectedBranchId === 'all' && '✓'}
                      </button>
                      {mockBranches.map((b) => (
                        <button
                          key={b.id}
                          onClick={() => { setSelectedBranchId(b.id); setBranchMenuOpen(false); }}
                          className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm ${selectedBranchId === b.id ? 'bg-blue-500 text-white' : 'text-slate-700 hover:bg-slate-50'}`}
                        >
                          {b.name}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-700">
                  <span className="text-xs text-slate-400">Branch:</span> {selectedBranchName}
                </div>
              )}
              {/* Виджет задач и просрочек (раздел 6 п.4 + раздел 7 Риск 2) */}
              <div
                ref={widgetRef}
                className="relative"
                onMouseLeave={() => setShowWidget(false)}
              >
                <button
                  onClick={() => setShowWidget((v) => !v)}
                  className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm"
                >
                  <span className={overduePayments.length > 0 ? 'text-rose-600' : 'text-slate-400'}>
                    ⚠ {overduePayments.length}
                  </span>
                  <span className="text-slate-400">|</span>
                  <span className={tasks.filter((t) => !t.isDone && !t.isCompleted).length > 0 ? 'text-sky-600' : 'text-slate-400'}>
                    📋 {tasks.filter((t) => !t.isDone && !t.isCompleted).length}
                  </span>
                </button>
                {showWidget && (
                  <div className="absolute right-0 z-20 mt-2 w-72 rounded-2xl border border-slate-100 bg-white p-3 shadow-lg">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2">Просрочки</p>
                    {overduePayments.length === 0 ? (
                      <p className="text-sm text-slate-500">Нет просроченных платежей ✅</p>
                    ) : (
                      <div className="space-y-1 max-h-28 overflow-y-auto">
                        {overduePayments.map((p) => (
                          <p key={p.id} className="text-xs text-rose-600">
                            {p.title} • {Number(p.amount).toLocaleString('ru-RU')} ₸
                          </p>
                        ))}
                      </div>
                    )}
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mt-3 mb-2">Активные задачи</p>
                    {tasks.filter((t) => !t.isDone && !t.isCompleted).length === 0 ? (
                      <p className="text-sm text-slate-500">Нет активных задач ✅</p>
                    ) : (
                      <div className="space-y-1 max-h-28 overflow-y-auto">
                        {tasks.filter((t) => !t.isDone && !t.isCompleted).slice(0, 6).map((t) => (
                          <p key={t.id} className={`text-xs ${t.priority === 'HIGH' ? 'text-rose-600 font-semibold' : 'text-slate-600'}`}>
                            {t.priority === 'HIGH' && '🔴 '}
                            {t.title}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
              <button
                onClick={() => setIsSimulating(true)}
                className="flex items-center gap-2 rounded-full bg-amber-500 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-amber-600"
              >
                ⚡ Симулировать лид
              </button>
              <button
                onClick={() => setIsCreating(true)}
                className="flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm"
              >
                <PlusCircle size={16} /> New deal
              </button>
            </div>
          </div>

          {/* Pipeline tabs */}
          <div className="mt-4 flex gap-2 rounded-full bg-slate-100 p-1 w-fit">
            {pipelineTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setSelectedPipeline(tab.id)}
                className={`rounded-full px-4 py-1.5 text-sm font-semibold transition ${
                  selectedPipeline === tab.id
                    ? 'bg-slate-900 text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* KPI row — 4 колонки (видимые сделки / выигранные / waitlist / forecast) */}
          <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
            <div className="rounded-2xl bg-slate-50 p-4">
              <p className="text-xs font-medium text-slate-500">Visible deals</p>
              <p className="mt-1 text-2xl font-bold text-slate-900">{stats.visible}</p>
            </div>
            <div className="rounded-2xl bg-slate-50 p-4">
              <p className="text-xs font-medium text-slate-500">Closed / won</p>
              <p className="mt-1 text-2xl font-bold text-slate-900">{stats.closedWon}</p>
            </div>
            <div className="rounded-2xl bg-slate-50 p-4">
              <p className="text-xs font-medium text-slate-500">Waitlisted</p>
              <p className="mt-1 text-2xl font-bold text-slate-900">{stats.waitlisted}</p>
            </div>
            <div className="rounded-2xl bg-emerald-50 p-4">
              <p className="text-xs font-medium text-emerald-600">Projected pipeline value</p>
              <p className="mt-1 text-2xl font-bold text-emerald-700">
                {stats.projectedValue.toLocaleString('ru-RU')} ₸
              </p>
            </div>
          </div>
        </div>

        {/* Аналитика — только HQ_ADMIN (раздел 8.2 «Кросс-филиальная аналитика» + Фаза 6) */}
        <AnalyticsWidget user={user} />

        {/* Kanban board */}
        <KanbanBoard
          deals={filteredDeals}
          selectedPipeline={selectedPipeline}
          onDealClick={(deal) => setEditingDeal(deal)}
        />
      </div>

      {editingDeal && (
        <DealModal
          deal={editingDeal}
          mode="edit"
          currentUser={user}
          onClose={() => setEditingDeal(null)}
          onSaveDeal={handleSaveDeal}
          onDeleteDeal={handleDeleteDeal}
        />
      )}

      {isCreating && (
        <DealModal
          deal={null}
          mode="create"
          currentUser={user}
          fixedBranchId={fixedBranchId}
          pipelineId={selectedPipeline}
          onClose={() => setIsCreating(false)}
          onCreateDeal={handleCreateDeal}
        />
      )}

      {isSimulating && (
        <LeadSimulatorModal
          currentBranchId={selectedBranchId === 'all' ? null : selectedBranchId}
          onClose={() => setIsSimulating(false)}
          onSimulated={handleSimulatedDeal}
        />
      )}
    </div>
  );
}

export default Dashboard;