import { useState } from 'react'
import toast from 'react-hot-toast'
import { getPipelineStages, getStageName } from '../services/pipelineManager'
import type { Deal, PipelineId } from '../types'
import { normalizeDeal } from '../services/dealAdapter'
import { mockBranches, mockTariffs } from '../data/mockData'
import { apiClient } from '../api/client'
import { calculateDealTotal, isB2BDeal } from '../lib/pricing'

interface KanbanBoardProps {
  deals: Deal[];
  selectedPipeline: PipelineId;
  onDealClick: (deal: Deal) => void;
}

const KanbanBoard = ({ deals, selectedPipeline, onDealClick }: KanbanBoardProps) => {
  const pipelineStages = getPipelineStages(selectedPipeline);
  const [draggedDealId, setDraggedDealId] = useState<string | null>(null);
  const [dragOverStage, setDragOverStage] = useState<string | null>(null);

  // Позиция сделки в листе ожидания (раздел 7, Риск 2): порядок по created_at/id среди WAITLIST.
  const waitlistOrder = deals
    .filter((d) => d.isWaitlisted || d.status === 'WAITLIST')
    .sort((a, b) => (a.id < b.id ? -1 : 1));
  const waitlistPositions = new Map(waitlistOrder.map((d, i) => [d.id, i + 1]));

  const handleDragStart = (e: React.DragEvent, dealId: string) => {
    setDraggedDealId(dealId);
    e.dataTransfer.setData('text/plain', dealId);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent, stageId: string) => {
    e.preventDefault(); // Разрешаем drop на колонку
    e.dataTransfer.dropEffect = 'move';
    setDragOverStage(stageId);
  };

  const handleDragLeave = () => {
    setDragOverStage(null);
  };

  const handleDrop = async (e: React.DragEvent, targetStageId: string) => {
    e.preventDefault();
    setDragOverStage(null);

    const dealId = e.dataTransfer.getData('text/plain') || draggedDealId;
    if (!dealId) return;

    const deal = deals.find((d) => d.id === dealId);
    if (!deal || deal.stageId === targetStageId) return;

    // 1) Оптимистично обновляем локальное состояние: меняем stageId + status,
    //    не создавая дубликатов и не трогая другие сделки.
    const optimisticStatus =
      targetStageId === 'enrolled'
        ? ('WON' as const)
        : targetStageId === 'lost'
          ? ('LOST' as const)
          : ('ACTIVE' as const);
    window.dispatchEvent(
      new CustomEvent('deal:stage-changed', {
        detail: { dealId, stageId: targetStageId, status: optimisticStatus },
      })
    );

    try {
      // 2) PATCH /api/deals/{id}/ с СИСТЕМНЫМ slug стадии (например "entrance_fee")
      //    и СИНХРОНИЗИРОВАННЫМ status (WON/LOST/ACTIVE) — чтобы после F5
      //    метрики и карточка остались на том же месте.
      await apiClient.patch(`/deals/${dealId}/`, {
        stage: targetStageId,
        status: optimisticStatus,
      });

      toast.success(`Карточка перемещена в «${getStageName(selectedPipeline, targetStageId)}»`);
    } catch (err) {
      // 3) Сервер вернул ошибку — перезапрашиваем актуальный список с бэкенда,
      //    чтобы вернуть карточки в исходные состояния (rollback).
      console.error('Failed to move deal stage:', err);
      toast.error('Не удалось изменить статус');
      try {
        const response = await apiClient.get('/deals/');
        const rawList = Array.isArray(response.data) ? response.data : [];
        const refreshed = rawList.map((d: unknown) => normalizeDeal(d as Parameters<typeof normalizeDeal>[0]));
        window.dispatchEvent(
          new CustomEvent('deals:replaced', { detail: { deals: refreshed } })
        );
      } catch {
        // Если и refresh не удался — оставляем как есть.
      }
    } finally {
      setDraggedDealId(null);
    }
  };

  return (
    <div className="grid grid-flow-col auto-cols-[260px] gap-4 overflow-x-auto pb-4">
      {pipelineStages.map((stage) => {
        const stageDeals = deals.filter((d) => d.stageId === stage.id);
        const isDragOver = dragOverStage === stage.id;

        return (
          <div
            key={stage.id}
            onDragOver={(e) => handleDragOver(e, stage.id)}
            onDragLeave={handleDragLeave}
            onDrop={(e) => handleDrop(e, stage.id)}
            className={`rounded-2xl bg-slate-100 p-3 transition ${
              isDragOver ? 'bg-blue-50 ring-2 ring-blue-400' : ''
            }`}
          >
            <div className="mb-3 flex items-center justify-between px-1">
              <h3 className="text-sm font-semibold text-slate-700">{stage.name}</h3>
              <span className="text-xs font-medium text-slate-400">{stageDeals.length}</span>
            </div>

            <div className="space-y-3">
              {stageDeals.map((deal) => {
                const branch = deal.branchName
                  ? { id: deal.branchId, name: deal.branchName }
                  : mockBranches.find((b) => b.id === deal.branchId);
                const tariff = deal.tariffName
                  ? { id: deal.tariffId, name: deal.tariffName }
                  : mockTariffs.find((t) => t.id === deal.tariffId);

                const isB2b = isB2BDeal(deal);
                const total = calculateDealTotal(deal);

                return (
                  <div
                    key={deal.id}
                    draggable={true}
                    onDragStart={(e) => handleDragStart(e, deal.id)}
                    onClick={() => onDealClick(deal)}
                    className={`cursor-grab rounded-2xl bg-white p-4 shadow-sm transition hover:shadow-md active:cursor-grabbing ${
                      draggedDealId === deal.id ? 'opacity-50' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        {isB2b ? (
                          <>
                            <p className="text-sm font-semibold text-slate-900">
                              {deal.b2b?.companyName ?? deal.parent.name}
                            </p>
                            <p className="text-xs text-slate-500">
                              {deal.b2b?.contactPerson ?? ''}
                              {deal.b2b?.serviceType ? ` • ${deal.b2b.serviceType}` : ''}
                            </p>
                          </>
                        ) : (
                          <>
                            <p className="text-sm font-semibold text-slate-900">{deal.parent.name}</p>
                            <p className="text-xs text-slate-500">
                              {deal.child.name} • {deal.child.gradeOrGroup}
                            </p>
                          </>
                        )}
                      </div>
                      {deal.hasTransport && (
                        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
                          🚐 Transport
                        </span>
                      )}
                    </div>

                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {branch && (
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                          {branch.name}
                        </span>
                      )}
                      {!isB2b && tariff && (
                        <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
                          {tariff.name}
                        </span>
                      )}
                      {isB2b && deal.b2b?.serviceType && (
                        <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-700">
                          {deal.b2b.serviceType}
                        </span>
                      )}
                      {deal.isWaitlisted && (
                        <span className="rounded-full bg-sky-50 px-2 py-0.5 text-[11px] font-medium text-sky-700">
                          ⏱ Waitlist #{waitlistPositions.get(deal.id) ?? deal.waitlistPosition ?? '—'}
                        </span>
                      )}
                    </div>

                    <div className="mt-2 flex items-center justify-between">
                      <p className="text-xs text-slate-500">
                        {isB2b ? (deal.b2b?.email ?? '') : deal.hasFood ? 'Food included' : ''}
                      </p>
                      <p className="text-sm font-bold text-slate-900">
                        {total > 0 ? `${total.toLocaleString('ru-RU')} ₸` : 'Бюджет уточняется'}
                      </p>
                    </div>

                    {deal.tasks.length > 0 && (
                      <p className="mt-2 text-[11px] text-slate-400">✨ {deal.tasks.length} follow-ups</p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default KanbanBoard;