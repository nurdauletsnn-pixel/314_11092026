// Define the pipeline configurations
import type { PipelineId, DealStageId } from '../../bi-crm-demo/frontend/src/types';

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
    { id: 'new-lead', name: 'Новый лид', order: 1 },
    { id: 'qualification', name: 'Квалификация', order: 2 },
    { id: 'tour', name: 'Экскурсия по школе', order: 3 },
    { id: 'testing', name: 'Тестирование / Собеседование', order: 4 },
    { id: 'contract', name: 'Заключение договора', order: 5 },
    { id: 'entrance-fee', name: 'Вступительный взнос', order: 6 },
    { id: 'enrolled', name: 'Ученик зачислен', order: 7 },
    { id: 'lost', name: 'Отказ / Закрыто', order: 8 },
  ],
  kindergarten: [
    { id: 'new-lead', name: 'Новый лид', order: 1 },
    { id: 'qualification', name: 'Квалификация', order: 2 },
    { id: 'tour', name: 'Экскурсия по саду', order: 3 },
    { id: 'trial-day', name: '1-й Пробный день', order: 4 },
    { id: 'decision', name: 'Принятие решения', order: 5 },
    { id: 'contract', name: 'Заключение договора', order: 6 },
    { id: 'enrolled', name: 'Зачислен в группу', order: 7 },
    { id: 'lost', name: 'Отказ / Закрыто', order: 8 },
  ],
  b2b: [
    { id: 'new-lead', name: 'Первичный контакт', order: 1 },
    { id: 'qualification', name: 'Квалификация партнера', order: 2 },
    { id: 'presentation', name: 'Презентация / КП', order: 3 },
    { id: 'negotiation', name: 'Переговоры', order: 4 },
    { id: 'contract', name: 'Согласование договора', order: 5 },
    { id: 'won', name: 'Сделка заключена', order: 6 },
    { id: 'lost', name: 'Отказ', order: 7 },
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
