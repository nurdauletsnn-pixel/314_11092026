// Определения воронок и стадий с СТРОГИМИ системными slug-ключами.
// Ключи совпадают с Django Deal.Stage choices (см. STAGE_SLUG_TO_NAME в views.py).
import type { DealStageId } from '../types';

interface PipelineStage {
  id: DealStageId;
  name: string;
  order: number;
}

interface PipelineConfig {
  school: PipelineStage[];
  kindergarten: PipelineStage[];
  b2b: PipelineStage[];
}

const pipelineConfig: PipelineConfig = {
  school: [
    { id: 'new', name: 'Новый лид', order: 1 },
    { id: 'qualification', name: 'Квалификация', order: 2 },
    { id: 'tour_scheduled', name: 'Экскурсия по школе', order: 3 },
    { id: 'testing', name: 'Тестирование / Собеседование', order: 4 },
    { id: 'contract_signing', name: 'Заключение договора', order: 5 },
    { id: 'entrance_fee', name: 'Вступительный взнос', order: 6 },
    { id: 'enrolled', name: 'Ученик зачислен', order: 7 },
    { id: 'lost', name: 'Отказ / Закрыто', order: 8 },
  ],
  kindergarten: [
    { id: 'new', name: 'Новый лид', order: 1 },
    { id: 'qualification', name: 'Квалификация', order: 2 },
    { id: 'trial_scheduled', name: '1-й Пробный день', order: 3 },
    { id: 'adaptation', name: 'Адаптация', order: 4 },
    { id: 'contract_signing', name: 'Заключение договора', order: 5 },
    { id: 'entrance_fee', name: 'Вступительный взнос', order: 6 },
    { id: 'first_month_paid', name: 'Оплата 1-го месяца', order: 7 },
    { id: 'enrolled', name: 'Зачислен в группу', order: 8 },
    { id: 'lost', name: 'Отказ / Закрыто', order: 9 },
  ],
  b2b: [
    { id: 'new', name: 'Первичный контакт', order: 1 },
    { id: 'qualification', name: 'Квалификация партнера', order: 2 },
    { id: 'meeting', name: 'Встреча', order: 3 },
    { id: 'commercial_offer', name: 'Коммерческое предложение (КП)', order: 4 },
    { id: 'contract_negotiation', name: 'Переговоры / Согласование договора', order: 5 },
    { id: 'invoice_sent', name: 'Счет выставлен', order: 6 },
    { id: 'won', name: 'Сделка заключена', order: 7 },
    { id: 'lost', name: 'Отказ', order: 8 },
  ],
};

// Helper functions
export function getPipelineStages(pipelineId: 'school' | 'kindergarten' | 'b2b'): PipelineStage[] {
  return [...pipelineConfig[pipelineId]].sort((a, b) => a.order - b.order);
}

export function isValidStageTransition(
  pipelineId: string,
  currentStageId: string,
  targetStageId: string
): boolean {
  const stages = pipelineConfig[pipelineId as keyof PipelineConfig];
  const currentStage = stages.find((stage) => stage.id === currentStageId);
  const targetStage = stages.find((stage) => stage.id === targetStageId);

  if (!currentStage || !targetStage) return false;

  // Allow moving to 'lost' from any stage
  if (targetStageId === 'lost') return true;

  // Allow moving to adjacent stages
  return (
    Math.abs(currentStage.order - targetStage.order) === 1
  );
}

export function getStageName(pipelineId: string, stageId: string): string {
  const stages = pipelineConfig[pipelineId as keyof PipelineConfig];
  const stage = stages.find((s) => s.id === stageId);
  return stage ? stage.name : '';
}

/** Проверяет, является ли переданный id системным slug стадии. */
export function isSystemStageId(stageId: string): boolean {
  return Object.values(pipelineConfig).some((stages: PipelineStage[]) =>
    stages.some((s: PipelineStage) => s.id === stageId)
  );
}
