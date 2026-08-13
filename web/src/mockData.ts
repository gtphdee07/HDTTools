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
      { name: 'standalone_weight_lb', label: 'Stand-alone Weight (lb, optional)', type: 'number' },
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
      { name: 'axle_count', label: 'Axle Count (optional, defaults to 2)', type: 'number' },
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
