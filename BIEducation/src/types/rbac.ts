export type UserRole = 'hq_admin' | 'sales_head' | 'manager' | 'sales';

export interface CurrentUser {
  id: string;
  name: string;
  role: UserRole;
  allowedBranchIds: string[];
}

export function isHQAdmin(user: CurrentUser): boolean {
  return user.role === 'hq_admin';
}

export function hasBranchAccess(user: CurrentUser, branchId: string): boolean {
  if (isHQAdmin(user)) return true;
  return user.allowedBranchIds.includes(branchId);
}

export function canManageAllBranches(user: CurrentUser): boolean {
  return user.role === 'hq_admin' || user.role === 'sales_head';
}

export function canViewDeal(user: CurrentUser, dealBranchId: string): boolean {
  return hasBranchAccess(user, dealBranchId);
}

export function canEditDeal(user: CurrentUser, dealBranchId: string): boolean {
  if (isHQAdmin(user)) return true;
  if (user.role === 'sales_head') return hasBranchAccess(user, dealBranchId);
  if (user.role === 'manager') return hasBranchAccess(user, dealBranchId);
  if (user.role === 'sales') return hasBranchAccess(user, dealBranchId);
  return false;
}