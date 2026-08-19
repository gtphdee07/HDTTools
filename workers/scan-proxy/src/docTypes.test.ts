import assert from "node:assert/strict";
import test from "node:test";
import { DOC_TYPE_CONFIG } from "./docTypes.ts";

test("[sanity] every doc type has a complete config", () => {
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

// The exact field names android/app/.../data/ScanFieldMapping.kt reads out
// of a scan response to merge onto TruckTag/TrailerTag/ScaleTicket. Neither
// test above would catch one of these silently disappearing - "every field
// present is self-consistent" says nothing about whether a specific field
// the client actually depends on is still there. Losing one wouldn't fail
// any build; it would just mean that one form field quietly stops getting
// prefilled by a scan.
const CLIENT_CONSUMED_FIELDS: Record<string, string[]> = {
  truck_tag: ["manufacturer", "gvwr_lb", "front_gawr_lb", "rear_gawr_lb"],
  trailer_tag: ["manufacturer", "gvwr_lb", "gawr_per_axle_lb", "uvw_lb"],
  scale_ticket: ["location_name", "steer_axle_lb", "drive_axle_lb", "trailer_axle_lb", "gross_weight_lb"],
};

test("every doc type's schema still contains the field names the Android client reads", () => {
  for (const [docType, fields] of Object.entries(CLIENT_CONSUMED_FIELDS)) {
    const config = DOC_TYPE_CONFIG[docType as keyof typeof DOC_TYPE_CONFIG];
    const properties = (config.schema as { properties: Record<string, unknown> }).properties;
    for (const field of fields) {
      assert.ok(
        field in properties,
        `${docType} schema is missing "${field}", which ScanFieldMapping.kt on Android reads`,
      );
    }
  }
});

test("toolName values are unique across doc types", () => {
  const names = Object.values(DOC_TYPE_CONFIG).map((config) => config.toolName);
  assert.equal(new Set(names).size, names.length);
});
