// src/services/accessControl.ts
// Реализует матрицу прав из раздела 8.2 спецификации.
// ВАЖНО: это только скрытие UI-элементов. Реальная защита — всегда на бэкенде (раздел 8.4).

import type { Deal, CurrentUser as User } from '../types';

// --- Роли (раздел 8.1) ---
export function isHQAdmin(user: User | null): boolean {
  return user?.role === 'HQ_ADMIN';
}

export function isBranchDirector(user: User | null): boolean {
  return user?.role === 'BRANCH_DIRECTOR';
}

export function isSalesManager(user: User | null): boolean {
  return user?.role === 'SALES_MANAGER';
}

/**
 * Кнопка «Удалить сделку» — видна ТОЛЬКО для HQ_ADMIN и BRANCH_DIRECTOR.
 * (раздел 8.2, строка «Удаление/архивация сделки»)
 */
export function canDeleteDeal(user: User | null): boolean {
  return isHQAdmin(user) || isBranchDirector(user);
}

/**
 * Действие «Отметить платёж оплаченным» — ТОЛЬКО HQ_ADMIN и BRANCH_DIRECTOR.
 * (раздел 8.2, строка «Отметить платёж оплаченным»)
 */
export function canMarkPaymentPaid(user: User | null): boolean {
  return isHQAdmin(user) || isBranchDirector(user);
}

/**
 * Редактирование глобального прайс-листа/тарифов — ТОЛЬКО HQ_ADMIN.
 * Скрыто от SALES_MANAGER и BRANCH_DIRECTOR.
 * (раздел 8.2, строка «Редактирование глобального прайс-листа/тарифов»)
 */
export function canEditPricing(user: User | null): boolean {
  return isHQAdmin(user);
}

/**
 * Селектор переключения филиалов в шапке/фильтрах — доступен ТОЛЬКО HQ_ADMIN.
 * Для остальных филиал зафиксирован их `branch`.
 * (раздел 8.2, строка «Просмотр сделок» + раздел 8.5)
 */
export function canSwitchBranch(user: User | null): boolean {
  return isHQAdmin(user);
}

/**
 * Филиал, зафиксированный для не-HQ пользователя.
 * Если у пользователя нет филиала (или он HQ_ADMIN) — null.
 */
export function getFixedBranchId(user: User | null): string | null {
  if (isHQAdmin(user)) return null;
  const id = user?.branch?.id;
  return id === null || id === undefined ? null : String(id);
}

/**
 * Доступ к конкретному филиалу (для фильтрации списков).
 * HQ_ADMIN видит всё; остальные — только свой филиал.
 */
export function canAccessBranch(user: User | null, branchId: string): boolean {
  if (isHQAdmin(user)) return true;
  const id = user?.branch?.id;
  return id === null || id === undefined ? false : String(id) === branchId;
}

export function filterDealsByAccess(deals: Deal[], user: User | null): Deal[] {
  if (isHQAdmin(user)) return deals;
  const branchId = user?.branch?.id;
  return deals.filter((deal) => branchId !== null && branchId !== undefined ? deal.branchId === String(branchId) : false);
}

export function canEditDeal(user: User | null, deal: Deal): boolean {
  if (!user) return false;
  if (isHQAdmin(user)) return true;
  const id = user.branch?.id;
  return id === null || id === undefined ? false : deal.branchId === String(id);
}

/**
 * Ручная скидка / перенос дедлайна взноса — только HQ_ADMIN и BRANCH_DIRECTOR.
 * (раздел 8.2, строка «Ручная скидка/перенос дедлайна взноса»)
 */
export function canGiveManualDiscount(user: User | null): boolean {
  return isHQAdmin(user) || isBranchDirector(user);
}

/**
 * Управление пользователями — HQ_ADMIN (все), BRANCH_DIRECTOR (только создание
 * SALES_MANAGER своего филиала), SALES_MANAGER — нет.
 * (раздел 8.2, строка «Управление пользователями»)
 */
export function canManageUsers(user: User | null): boolean {
  return isHQAdmin(user) || isBranchDirector(user);
}

/**
 * Merge дублей контактов между филиалами — HQ_ADMIN.
 * BRANCH_DIRECTOR видит кандидатов своего филиала, финальный merge — нет.
 * (раздел 8.2, строка «Merge дублей контактов между филиалами»)
 */
export function canMergeDuplicates(user: User | null): boolean {
  return isHQAdmin(user);
}

/**
 * Кросс-филиальная аналитика — только HQ_ADMIN.
 * (раздел 8.2, строка «Кросс-филиальная аналитика»)
 */
export function canViewCrossBranchAnalytics(user: User | null): boolean {
  return isHQAdmin(user);
}