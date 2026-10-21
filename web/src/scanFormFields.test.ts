import { describe, expect, it } from 'vitest';
import FORM_FIELDS from '../../test-vectors/scan_form_fields.json';
import { MODULES } from './mockData';

// The review form's fields are MODULES[n].fields in mockData.ts. test-vectors/scan_form_fields.json is the shared
// list of what each surface's review form shows per doc type (`scanned` fields a Scan can fill, `manual_only`
// fields it never returns), with each field's type. Streamlit and Android check their own forms against the same
// file, so a field added, renamed or retyped on one surface only fails there. visionToolSchema.test.ts checks the
// narrower question of which names the Claude tool returns; this one checks the form as a whole, types included.

const DOC_TYPE_FOR_MODULE = { truck: 'truck_tag', trailer: 'trailer_tag', scale: 'scale_ticket' } as const;

const ALL_MODULES = Object.values(MODULES);

const asPairs = (fields: { name: string; type: string }[]) => fields.map((f) => `${f.name}:${f.type}`).sort();

describe('Review-form fields against the shared scan form fields', () => {
  it.each(ALL_MODULES.map((module) => [module.key, module] as const))(
    '%s: the (name, type) pairs are exactly the fixture\'s scanned plus manual_only',
    (key, module) => {
      const doc = FORM_FIELDS[DOC_TYPE_FOR_MODULE[key]];
      expect(asPairs(module.fields)).toEqual(asPairs([...doc.scanned, ...doc.manual_only]));
    },
  );

  it.each(ALL_MODULES.map((module) => [module.key, module] as const))(
    '%s: the optional fields are exactly the fixture\'s manual_only names',
    (key, module) => {
      const doc = FORM_FIELDS[DOC_TYPE_FOR_MODULE[key]];
      const optional = module.fields.filter((f) => f.optional).map((f) => f.name);
      expect(optional.sort()).toEqual(doc.manual_only.map((f) => f.name).sort());
    },
  );
});
