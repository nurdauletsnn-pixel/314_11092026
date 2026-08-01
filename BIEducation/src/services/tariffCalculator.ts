// src/services/tariffCalculator.ts

type CalculationInput = {
  tariff: {
    basePrice: number;
    entranceFee?: number;
  };
  childrenCount: number;
  pipelineId: 'school' | 'kindergarten' | 'b2b';
  addons: {
    food?: boolean;
    transport?: boolean;
    transportZone?: 'city' | 'suburb';
  };
  installmentType: 'FULL' | 'TRANCHE_3' | 'TRANCHE_8';
};

type PaymentScheduleItem = {
  title: string;
  amount: number;
  dueDate?: string;
};

type CalculationResult = {
  totalAmount: number;
  monthlyPayment: number;
  discountApplied: boolean;
  schedule: PaymentScheduleItem[];
};

export function calculateTariff(input: CalculationInput): CalculationResult {
  const { tariff, childrenCount, pipelineId, addons, installmentType } = input;
  let totalAmount = tariff.basePrice;
  let discountApplied = false;

  // ALDI BI Discount
  if (pipelineId === 'kindergarten' && childrenCount >= 2) {
    totalAmount *= 0.9;
    discountApplied = true;
  }

  // UVU Transport
  if (addons.transport) {
    const transportCost = addons.transportZone === 'city' ? 57000 : 72000;
    totalAmount += transportCost;
  }

  // Food
  if (addons.food) {
    // Assuming a fixed food cost (adjust as needed)
    totalAmount += 30000; // Example value
  }

  // Entrance Fee
  if (tariff.entranceFee) {
    totalAmount += tariff.entranceFee;
  }

  // Payment Schedule
  const schedule: PaymentScheduleItem[] = [];
  let monthlyPayment = totalAmount;

  switch (installmentType) {
    case 'FULL':
      schedule.push({
        title: 'Full Payment',
        amount: totalAmount,
      });
      break;
    case 'TRANCHE_3':
      monthlyPayment = totalAmount / 3;
      for (let i = 1; i <= 3; i++) {
        schedule.push({
          title: `Payment ${i} of 3`,
          amount: monthlyPayment,
        });
      }
      break;
    case 'TRANCHE_8':
      monthlyPayment = totalAmount / 8;
      for (let i = 1; i <= 8; i++) {
        schedule.push({
          title: `Payment ${i} of 8`,
          amount: monthlyPayment,
        });
      }
      break;
  }

  return {
    totalAmount,
    monthlyPayment,
    discountApplied,
    schedule,
  };
}
