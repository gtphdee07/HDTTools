// Free checks that the Worker and the Python vision client (src/hdttools/, surface
// anthropic-python) cannot quietly drift apart (#143). Both Claude vision External tests read
// test-vectors/vision_external_cases.json and the golden values in ExampleDocs/golden_fields.json;
// both sides send the tool in test-vectors/vision_tool_schemas.json. The Python side runs the same
// checks in tests/test_vision_shared_fixtures.py. No Claude call is made here.
import "./requireInstall.ts";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { DOC_TYPE_CONFIG } from "./docTypes.ts";
import { REPO_ROOT, loadVisionCases, newMismatches } from "./external/visionCases.ts";

const EXTERNAL_DIR = path.join(import.meta.dirname, "external");

interface SchemaNode {
  properties?: Record<string, unknown>;
  required?: string[];
}

interface ToolSchemas {
  tire: { properties: string[]; required: string[] };
  doc_types: Record<string, { tool_name: string; properties: string[]; required: string[]; nested: string[] }>;
}

const TOOL_SCHEMAS = JSON.parse(
  readFileSync(path.join(REPO_ROOT, "test-vectors", "vision_tool_schemas.json"), "utf8"),
) as ToolSchemas;

test("[sanity] every shared vision case points at an image that exists and a golden entry that exists", () => {
  const cases = loadVisionCases(); // throws, naming the case, when the golden entry is missing
  assert.ok(cases.length > 0);
  for (const visionCase of cases) {
    assert.ok(existsSync(visionCase.imagePath), `${visionCase.docType}: ${visionCase.image} is not in ExampleDocs/`);
    assert.ok(Object.keys(visionCase.fields).length > 0, `${visionCase.docType}: golden entry has no fields`);
  }
});

test("[sanity] the shared vision cases cover every doc type exactly once", () => {
  const caseTypes = loadVisionCases().map((visionCase) => visionCase.docType);
  assert.deepEqual([...caseTypes].sort(), Object.keys(DOC_TYPE_CONFIG).sort());
});

test("[sanity] a shared vision case's golden entry is for the same doc type as the case", () => {
  const goldenFile = JSON.parse(readFileSync(path.join(REPO_ROOT, "ExampleDocs", "golden_fields.json"), "utf8")) as {
    photos: Record<string, { doc_type: string }>;
  };
  for (const visionCase of loadVisionCases()) {
    assert.equal(goldenFile.photos[visionCase.golden]?.doc_type, visionCase.docType, visionCase.golden);
  }
});

test("[sanity] the Worker's External test takes its cases from the shared file and keeps no list of its own", () => {
  const source = readFileSync(path.join(EXTERNAL_DIR, "anthropic.external.test.ts"), "utf8");
  assert.match(source, /import\s*\{[^}]*\bloadVisionCases\b[^}]*\}\s*from\s*"\.\/visionCases\.ts"/);
  assert.match(source, /=\s*loadVisionCases\(\)/);
  assert.doesNotMatch(source, /\.jpe?g"/, "the External test names a photo of its own");
  assert.doesNotMatch(source, /"ExampleDocs"/, "the External test reads ExampleDocs itself");
  assert.doesNotMatch(source, /expectFields/, "the External test keeps its own list of fields");

  const loader = readFileSync(path.join(EXTERNAL_DIR, "visionCases.ts"), "utf8");
  assert.ok(loader.includes("vision_external_cases.json"));
  assert.ok(loader.includes("golden_fields.json"));
});

const KNOWN = { fields: { a: 1, b: "x", c: 5 }, knownOcrLimitations: { c: "reads 50" } };

test("[sanity] a value that differs from the golden value is a mismatch, not only a missing field name", () => {
  assert.deepEqual(newMismatches(KNOWN, { a: 1, b: "y", c: 5 }), { b: { got: "y", expected: "x" } });
  assert.deepEqual(newMismatches(KNOWN, { a: 2, b: "x", c: 5 }), { a: { got: 2, expected: 1 } });
});

test("[sanity] a field the golden entry does not return at all is a mismatch", () => {
  assert.deepEqual(newMismatches(KNOWN, { b: "x", c: 5 }), { a: { got: undefined, expected: 1 } });
});

test("[sanity] only a field named in known_ocr_limitations is tolerated", () => {
  assert.deepEqual(newMismatches(KNOWN, { a: 1, b: "x", c: 50 }), {});
  assert.deepEqual(newMismatches(KNOWN, { a: 1, b: "x" }), {});
  assert.deepEqual(newMismatches(KNOWN, { a: 1, b: "x", c: 50, zzz: 9 }), {});
});

function propertyNames(schema: unknown): string[] {
  return Object.keys((schema as SchemaNode).properties ?? {});
}

function requiredNames(schema: unknown): string[] {
  return (schema as SchemaNode).required ?? [];
}

test("[sanity] every doc type sends the tool name, property names and required names the Python readers send", () => {
  assert.deepEqual(Object.keys(DOC_TYPE_CONFIG).sort(), Object.keys(TOOL_SCHEMAS.doc_types).sort());
  for (const [docType, config] of Object.entries(DOC_TYPE_CONFIG)) {
    const shared = TOOL_SCHEMAS.doc_types[docType];
    assert.equal(config.toolName, shared.tool_name, `${docType} tool name`);
    assert.deepEqual(propertyNames(config.schema), shared.properties, `${docType} properties`);
    assert.deepEqual([...requiredNames(config.schema)].sort(), [...shared.required].sort(), `${docType} required`);

    const nestedObjects = propertyNames(config.schema).filter(
      (name) => (config.schema.properties as Record<string, { type?: unknown }>)[name].type === "object",
    );
    assert.deepEqual(nestedObjects, shared.nested, `${docType} nested objects`);
    for (const name of shared.nested) {
      const tire = (config.schema.properties as Record<string, unknown>)[name];
      assert.deepEqual(propertyNames(tire), TOOL_SCHEMAS.tire.properties, `${docType}.${name} properties`);
      assert.deepEqual([...requiredNames(tire)].sort(), [...TOOL_SCHEMAS.tire.required].sort(), `${docType}.${name} required`);
    }
  }
});
