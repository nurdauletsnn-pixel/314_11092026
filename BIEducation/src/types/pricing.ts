import { Parent, Tariff, Branch } from './common-types';

export interface CalculationInput {
  parent: Parent;
  tariff: Tariff;
  branch: Branch;
  childrenCount: number;
  isSecondChild: boolean;
  isUrban: boolean;
  paymentSchedule: 'full' | '3_installments' | '8_installments';
}

export interface CalculationResult {
  totalAmount: number;
  breakdown: {
    basePrice: number;
    discount: number;
    transport: number;
    food: number;
  };
  paymentSchedule: PaymentScheduleItem[];
}

export interface PaymentScheduleItem {
  amount: number;
  dueDate: string;
}

export interface TariffWithAddons extends Tariff {
  addons: {
    food: boolean;
    transport: boolean;
  };
}
