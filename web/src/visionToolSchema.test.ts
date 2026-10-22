import { describe, expect, it } from 'vitest';
import SCHEMAS from '../../test-vectors/vision_tool_schemas.json';
import { MODULES } from './mockData';

// The review step pre-fills each field of MODULES by name from the Worker's `fields` object, and the Worker's
// fields are the properties of the Claude vision tool it forces. A MODULES name that is not a property of that
// tool (a typo, or a rename on one side only) is never pre-filled, and the Scan notice would report it as "not
// read" on every scan. test-vectors/vision_tool_schemas.json is the shared copy of those tool schemas that the
// Worker and the Python readers are each pinned to; this checks Web's side of it. The Streamlit (#140) and
// Android (#149) slices of the same check read the same file.
//
// The fields marked `optional: true` in mockData.ts (standalone_weight_lb, gcwr_lb, axle_count) are manual-only:
// no Scan is expected to fill them, so they are not in the tool schema. They are excluded by that flag, and the
// test below pins that exactly those three are the ones excluded, so a new optional field cannot slip out of
// the check unnoticed.

const DOC_TYPE_FOR_MODULE = { truck: 'truck_tag', trailer: 'trailer_tag', scale: 'scale_ticket' } as const;

const MANUAL_ONLY = ['standalone_weight_lb', 'gcwr_lb', 'axle_count'];

const ALL_MODULES = Object.values(MODULES);

describe('Review-form field names against the shared Claude-vision tool schema', () => {
  it.each(ALL_MODULES.map((module) => [module.key, module] as const))(
    '%s: every field that is not optional is a property of the tool',
    (key, module) => {
      const properties = new Set(SCHEMAS.doc_types[DOC_TYPE_FOR_MODULE[key]].properties);
      const missing = module.fields.filter((field) => !field.optional && !properties.has(field.name)).map((f) => f.name);
      expect(missing, `MODULES ${key} names the Claude tool does not return`).toEqual([]);
    },
  );

  it('the optional fields are exactly the manual-only ones', () => {
    const optional = ALL_MODULES.flatMap((module) => module.fields.filter((f) => f.optional).map((f) => f.name));
    expect(optional.sort()).toEqual([...MANUAL_ONLY].sort());
  });
});
