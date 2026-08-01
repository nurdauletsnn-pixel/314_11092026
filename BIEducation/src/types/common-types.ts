export type CalculationInput = {
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
  id?: string;
  branch?: string;
  tariff_name?: string;
  is_waitlisted?: boolean;
  total_amount?: number;
  parent_profile?: {
    full_name: string;
    phone: string;
  };
  child_profile?: {
    full_name: string;
    grade_or_group: string;
    grade_band: string;
  };
  paymentSchedule?: any[];
};