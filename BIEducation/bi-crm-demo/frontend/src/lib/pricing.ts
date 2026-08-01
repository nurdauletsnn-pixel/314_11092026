import type { Deal } from '../types'

export interface PricingPreview {
  total_amount: number;
  schedules: Array<{ title: string; amount: number; due_date: string; status: string }>;
}

/**
 * Расчёт потенциальной суммы сделки для отображения на карточке.
 *
 * Исправление бага «0 ₸»: если сделка в Waitlist или тариф ещё не финализирован —
 * НЕ показываем 0. Вместо этого возвращаем базовую стоимость группы/класса
 * или ориентировочный бюджет (B2B — сумма контракта).
 */
export function calculateDealTotal(deal: Deal): number {
  if (deal.b2b || deal.partnerType) {
    return deal.contractValue ?? deal.b2b?.budget ?? deal.totalAmount ?? 0
  }

  // Тариф финализирован — используем реальную сумму.
  if (deal.totalAmount && deal.totalAmount > 0) {
    return deal.totalAmount
  }
  if (deal.expectedRevenue && deal.expectedRevenue > 0) {
    return deal.expectedRevenue
  }

  // Waitlist / тариф не выбран: возвращаем базовую стоимость группы/класса
  // (ориентировочный бюджет), чтобы не показывать «0 ₸».
  if (deal.isWaitlisted || deal.status === 'WAITLIST' || !deal.tariffId) {
    return estimateWaitlistBudget(deal)
  }

  return deal.totalAmount ?? 0
}

/** Ориентировочный бюджет по группе/классу, если тариф ещё не финализирован. */
export function estimateWaitlistBudget(deal: Deal): number {
  const grade = deal.child?.gradeBand
  if (grade === 'PRESCHOOL') return 200_000 + 250_000 * 10 // взнос + 10 месяцев сада
  if (grade === 'SENIOR') return 5_500_000
  return 4_900_000 // PRIMARY_SECONDARY (Riviera «Стандарт»)
}

/** Является ли сделка B2B (категория или вкладка). */
export function isB2BDeal(deal: Deal): boolean {
  return deal.pipelineId === 'b2b' || Boolean(deal.b2b) || Boolean(deal.partnerType)
}

export function buildPricingPreview(
  branchCode: string, // Код филиала, например: 'RIVIERA', 'ALDI_CAPITAL', 'ALDI_FLAGMAN'
  tariff: string, // 'PROFITABLE', 'STANDARD', 'STANDARD_PLUS'
  hasFood: boolean,
  hasTransport: boolean,
  isSecondChild: boolean,
  gradeBand: 'PRESCHOOL' | 'PRIMARY_SECONDARY' | 'SENIOR', // 0 класс, 1-11 классы, 12 класс
): PricingPreview {
  const schedules: PricingPreview['schedules'] = [];
  let total = 0;

  // --- ЛОГИКА ШКОЛЫ RIVIERA ---
  if (branchCode === 'RIVIERA') {
    // Взнос: 0 класс = 200к, остальные = 350к[cite: 4]
    const entranceFee = gradeBand === 'PRESCHOOL' ? 200_000 : 350_000;
    schedules.push({ title: 'Вступительный взнос', amount: entranceFee, due_date: '', status: 'PENDING' });
    total += entranceFee;

    let mainFee = 0;

    // Сетка тарифов Riviera[cite: 4]
    if (gradeBand === 'PRESCHOOL') {
      if (tariff === 'PROFITABLE') mainFee = 3_500_000;
      if (tariff === 'STANDARD') mainFee = 3_650_000;
      if (tariff === 'STANDARD_PLUS') mainFee = 3_900_000;
    } else if (gradeBand === 'PRIMARY_SECONDARY') {
      if (tariff === 'PROFITABLE') mainFee = 4_500_000;
      if (tariff === 'STANDARD') mainFee = 4_900_000;
      if (tariff === 'STANDARD_PLUS') mainFee = 5_180_000;
    } else if (gradeBand === 'SENIOR') {
      if (tariff === 'PROFITABLE') mainFee = 4_700_000;
      if (tariff === 'STANDARD') mainFee = 5_100_000;
      if (tariff === 'STANDARD_PLUS') mainFee = 5_500_000;
    }

    schedules.push({ title: 'Стоимость обучения', amount: mainFee, due_date: '', status: 'PENDING' });
    total += mainFee;

    // Питание и развозка Riviera[cite: 4]
    if (hasFood) total += 752_400; 
    if (hasTransport) total += 513_000; // (57 000 * 9 месяцев)
    
    return { total_amount: total, schedules };
  }

  // --- ЛОГИКА ШКОЛ QUANTUM ---
  if (branchCode === 'QUANTUM_STEM' || branchCode === 'QUANTUM_TECH') {
    const entranceFee = 200_000;
    schedules.push({ title: 'Вступительный взнос', amount: entranceFee, due_date: '', status: 'PENDING' });
    total += entranceFee;

    // Тарифы Quantum[cite: 4]
    const mainFee = tariff === 'PROFITABLE' ? 4_200_000 : 4_410_000;
    schedules.push({ title: 'Стоимость обучения', amount: mainFee, due_date: '', status: 'PENDING' });
    total += mainFee;

    // Питание в Quantum зависит от класса: начальные = 630к, старшие = 684к[cite: 4]
    if (hasFood) total += gradeBand === 'PRIMARY_SECONDARY' ? 630_000 : 684_000; 
    
    return { total_amount: total, schedules };
  }

  // --- ЛОГИКА САДОВ ALDI BI ---
  if (branchCode.startsWith('ALDI')) {
    let entranceFee = 0;
    let monthlyFee = 0;

    // Привязка цен к локациям[cite: 4]
    if (branchCode === 'ALDI_CAPITAL') {
      entranceFee = 200_000;
      monthlyFee = 250_000;
    } else if (branchCode === 'ALDI_GREENLINE') {
      entranceFee = 150_000;
      monthlyFee = 165_000;
    } else if (branchCode === 'ALDI_FLAGMAN') {
      entranceFee = 100_000;
      monthlyFee = 115_000;
    }

    // Скидка 10% на 2-го ребенка в садах[cite: 4]
    if (isSecondChild) {
      monthlyFee = Math.round(monthlyFee * 0.9);
    }

    schedules.push({ title: 'Вступительный взнос', amount: entranceFee, due_date: '', status: 'PENDING' });
    schedules.push({ title: 'Ежемесячный платеж (1 месяц)', amount: monthlyFee, due_date: '', status: 'PENDING' });

    return {
      total_amount: entranceFee + monthlyFee,
      schedules,
    };
  }

  return { total_amount: 0, schedules: [] };
}