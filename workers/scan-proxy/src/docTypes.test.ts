import assert from "node:assert/strict";
import test from "node:test";
import { DOC_TYPE_CONFIG } from "./docTypes.ts";

test("every doc type has a complete config", () => {
  for (const [docType, config] of Object.entries(DOC_TYPE_CONFIG)) {
    assert.ok(config.systemPrompt.length > 0, `${docType} missing systemPrompt`);
    assert.ok(config.toolName.length > 0, `${docType} missing toolName`);
    assert.ok(config.toolDescription.length > 0, `${docType} missing toolDescription`);
    assert.equal((config.schema as { type: string }).type, "object");
  }
});

// A required[]/properties mismatch is exactly the kind of copy-paste bug
// that creeps in when porting near-identical schemas across doc types (this
// one was ported by hand from the Python readers) — and it's the kind of
// thing that only fails loudly once it hits the real Claude API.
function assertRequiredMatchesProperties(schema: unknown, path: string): void {
  if (
    schema !== null &&
    typeof schema === "object" &&
    "type" in schema &&
    (schema as { type: unknown }).type === "object" &&
    "properties" in schema
  ) {
    const { properties, required } = schema as {
      properties: Record<string, unknown>;
      required?: string[];
    };
    const propertyKeys = Object.keys(properties).sort();
    const requiredKeys = [...(required ?? [])].sort();
    assert.deepEqual(requiredKeys, propertyKeys, `${path}: required[] doesn't match properties`);

    for (const [key, value] of Object.entries(properties)) {
      assertRequiredMatchesProperties(value, `${path}.${key}`);
    }
  }
}

test("every schema's required list matches its properties, including nested tire schemas", () => {
  for (const [docType, config] of Object.entries(DOC_TYPE_CONFIG)) {
    assertRequiredMatchesProperties(config.schema, docType);
  }
});
