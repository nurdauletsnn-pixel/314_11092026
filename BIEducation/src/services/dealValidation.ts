import type { Deal } from '../types';

export function isValidStageTransition(deal: Deal, targetStage: { id: string }): boolean {
  if (!deal || !targetStage) return false;
  // Здесь можно добавить бизнес-логику ограничений переходов
  return true;
}