export type PipelineId = 'school' | 'kindergarten' | 'b2b';

export type DealStageId =
  | 'new-lead'
  | 'qualification'
  | 'tour'
  | 'trial-day'
  | 'decision'
  | 'offer'
  | 'negotiation'
  | 'contract'
  | 'entrance-fee-paid'
  | 'paid'
  | 'enrolled'
  | 'lost'
  | string;

export interface Branch {
  id: string;
  code?: string;
  name: string;
  city?: string;
  segment?: string;
}

export interface Parent {
  id: string;
  fullName: string;
  phone: string;
  email?: string;
  iin?: string;
}

export interface Child {
  id: string;
  parentId?: string;
  fullName: string;
  birthDate?: string;
  gradeOrGroup?: string;
  medicalNotes?: string;
}

export interface DealAddons {
  food?: boolean;
  transport?: boolean;
}

export interface Tariff {
  id: string;
  name: string;
  basePrice: number;
  entranceFee?: number;
  installmentType?: 'FULL' | 'TRANCHE_3' | 'TRANCHE_8';
}

export type UserRole = 'hq_admin' | 'sales_head' | 'manager' | 'sales';

export interface User {
  id: string;
  name: string;
  role: UserRole;
  allowedBranchIds: string[];
}

export interface Deal {
  id: string;
  title?: string;
  parentId?: string;
  childId?: string;
  branchId?: string;
  tariffId?: string;
  pipelineId?: PipelineId;
  stageId?: DealStageId;
  status?: string;
  totalAmount?: number;
  amount?: number;
  addons?: DealAddons;
  isWaitlisted?: boolean;
  parent?: Parent | null;
  child?: Child | null;
  branch?: Branch | null;
  tariff?: Tariff | null;
}