export interface TireSpec {
  tire?: string;
  rim?: string;
  cold_pressure_kpa?: number;
  cold_pressure_psi?: number;
  dual?: boolean;
}

export interface ScaleTicketData {
  source_image?: string;
  ticket_number?: string;
  weigh_number?: string;
  date?: string;
  time?: string;
  scale_number?: string;
  location_name?: string;
  location_address?: string;
  city?: string;
  state?: string;
  steer_axle_lb?: number;
  drive_axle_lb?: number;
  trailer_axle_lb?: number;
  gross_weight_lb?: number;
  company?: string;
  commodity?: string;
  tractor_number?: string;
  trailer_number?: string;
}

export interface TruckTagData {
  vehicle_name?: string;
  source_image?: string;
  manufacturer?: string;
  date?: string;
  vin?: string;
  vehicle_type?: string;
  gvwr_kg?: number;
  gvwr_lb?: number;
  front_gawr_kg?: number;
  front_gawr_lb?: number;
  rear_gawr_kg?: number;
  rear_gawr_lb?: number;
  standalone_weight_lb?: number;
  front_tire?: TireSpec;
  rear_tire?: TireSpec;
}

export interface TrailerTagData {
  vehicle_name?: string;
  source_image?: string;
  manufacturer?: string;
  date?: string;
  vin?: string;
  vehicle_type?: string;
  gvwr_kg?: number;
  gvwr_lb?: number;
  gawr_per_axle_kg?: number;
  gawr_per_axle_lb?: number;
  uvw_kg?: number;
  uvw_lb?: number;
  axle_count?: number;
  tire?: TireSpec;
}

export interface Rig {
  id: string;
  truckName: string;
  trailerName: string;
}

export type Verdict = 'pass' | 'fail';

export interface HistoryEntry {
  id: string;
  date: string;
  truckName: string;
  trailerName: string;
  verdict: Verdict;
}

export type Screen = 'home' | 'history' | 'wizard';
export type WizardSubStep = 'upload' | 'processing' | 'review' | 'error' | 'finalizing';

export interface WizardState {
  step: number; // 0 = select rig, 1 = truck, 2 = trailer, 3 = scale, 4 = results
  subStep: WizardSubStep;
  rigChoice: string;
  truck: TruckTagData;
  trailer: TrailerTagData;
  scale: ScaleTicketData;
  pendingFile: File | null;
  uploadError: string | null;
}

export interface BreakdownItem {
  label: string;
  tone: 'success' | 'warning';
  badgeLabel: string;
  pct: number;
  barColor: string;
  actualLabel: string;
  limitLabel: string;
  note: string | null;
}

export interface VerdictInfo {
  headline: string;
  subline: string;
  bandBg: string;
  icon: 'alert-triangle' | 'check-circle-2';
}
