// src/services/accessControl.ts

import type { Deal, CurrentUser as User, UserRole } from '../types';

export function canAccessBranch(user: User, branchId: string): boolean {
  if (user.role === 'admin' || user.role === 'hq_admin') {
    return true;
  }
  return user.allowedBranchIds?.includes(branchId) ?? false;
}

export function filterDealsByAccess(deals: Deal[], user: User): Deal[] {
  return deals.filter(deal => {
    if (user.role === 'admin' || user.role === 'hq_admin') {
      return true;
    }
    if (!deal.branchId) {
      return false;
    }
    return canAccessBranch(user, deal.branchId);
  });
}

export function canEditDeal(user: User, deal: Deal): boolean {
  if (user.role === 'admin' || user.role === 'hq_admin') {
    return true;
  }
  return deal.branchId ? canAccessBranch(user, deal.branchId) : false;
}