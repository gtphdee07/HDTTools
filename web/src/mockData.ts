import type { HistoryEntry, Rig, WizardState } from './types';

export const initialRigs: Rig[] = [
  { id: 'r1', truckName: 'Big Blue (Ford F-350)', trailerName: 'The Nest (Grand Design 2930RL)' },
];

export const initialHistory: HistoryEntry[] = [
  { id: 'h1', date: 'Jul 28, 2026', truckName: 'Big Blue (Ford F-350)', trailerName: 'The Nest (Grand Design 2930RL)', verdict: 'fail' },
  { id: 'h2', date: 'Jun 14, 2026', truckName: 'Big Blue (Ford F-350)', trailerName: 'The Nest (Grand Design 2930RL)', verdict: 'pass' },
  { id: 'h3', date: 'May 2, 2026', truckName: 'Big Blue (Ford F-350)', trailerName: 'The Nest (Grand Design 2930RL)', verdict: 'pass' },
];

export const initialWizard: WizardState = {
  step: 0,
  subStep: 'upload',
  rigChoice: 'r1',
  truck: { manufacturer: 'Ford', gvwr_lb: 14000, front_gawr_lb: 6000, rear_gawr_lb: 9500 },
  trailer: { manufacturer: 'Grand Design', gvwr_lb: 12500, gawr_per_axle_lb: 6000, uvw_lb: 9800 },
  scale: {
    steer_axle_lb: 5620,
    drive_axle_lb: 9040,
    trailer_axle_lb: 11380,
    gross_weight_lb: 26040,
    location_name: 'Loves Travel Stop #432',
    date: '08/10/2026',
  },
};

export type FieldType = 'text' | 'number';

export interface FieldDef {
  name: string;
  label: string;
  type: FieldType;
}

export interface ModuleDef {
  key: 'truck' | 'trailer' | 'scale';
  title: string;
  instructions: string;
  slotPlaceholder: string;
  continueLabel: string;
  fields: FieldDef[];
}

export const MODULES: Record<1 | 2 | 3, ModuleDef> = {
  1: {
    key: 'truck',
    title: 'Truck Compliance Label',
    instructions: "Photograph the Safety Compliance Certification label on your tow vehicle's door jamb.",
    slotPlaceholder: 'Drop a photo of the truck tag',
    continueLabel: 'Next: Trailer Tag',
    fields: [
      { name: 'manufacturer', label: 'Manufacturer', type: 'text' },
      { name: 'gvwr_lb', label: 'GVWR (lb)', type: 'number' },
      { name: 'front_gawr_lb', label: 'Front GAWR (lb)', type: 'number' },
      { name: 'rear_gawr_lb', label: 'Rear GAWR (lb)', type: 'number' },
    ],
  },
  2: {
    key: 'trailer',
    title: 'Trailer Compliance Label',
    instructions: 'Photograph the Safety Compliance Certification label on your trailer.',
    slotPlaceholder: 'Drop a photo of the trailer tag',
    continueLabel: 'Next: Scale Ticket',
    fields: [
      { name: 'manufacturer', label: 'Manufacturer', type: 'text' },
      { name: 'gvwr_lb', label: 'GVWR (lb)', type: 'number' },
      { name: 'gawr_per_axle_lb', label: 'GAWR per axle (lb)', type: 'number' },
      { name: 'uvw_lb', label: 'Unloaded Weight / UVW (lb)', type: 'number' },
    ],
  },
  3: {
    key: 'scale',
    title: 'CAT Scale Ticket',
    instructions: 'Photograph your CAT Scale weigh ticket, showing steer, drive, and trailer axle weights.',
    slotPlaceholder: 'Drop a photo of the scale ticket',
    continueLabel: 'See My Results',
    fields: [
      { name: 'location_name', label: 'Scale Location', type: 'text' },
      { name: 'steer_axle_lb', label: 'Steer Axle (lb)', type: 'number' },
      { name: 'drive_axle_lb', label: 'Drive Axle (lb)', type: 'number' },
      { name: 'trailer_axle_lb', label: 'Trailer Axle(s) (lb)', type: 'number' },
      { name: 'gross_weight_lb', label: 'Gross Weight (lb)', type: 'number' },
    ],
  },
};
