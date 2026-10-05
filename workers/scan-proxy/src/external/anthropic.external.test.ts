// External suite (ADR-0008): real calls to the live Anthropic API via
// extractFields (this Worker's own boundary, ../claude.ts), called
// directly - never through the deployed Worker or RevenueCat (that's the
// Release/Weekly tiers' job; scan.release.test.ts and scan.weekly.test.ts
// keep their own separate suites and budgets, per issue #37's scope note -
// this file is the "anthropic" surface's own suite, additive to them).
// Run only via test-external.ps1 / `npm run test:external`. The
// "[anthropic]" name tag is what the wrapper filters on.
//
// Needs ANTHROPIC_API_KEY in the environment - a missing key fails the run
// outright, never a silent skip (the wrapper's -Skip switch already covers
// that via its own `skipped` recording).
//
// Real cost: exactly one real, billed Claude call per doc type (3 total,
// matching scripts/external_manifest/surfaces/anthropic.json's
// max_paid_calls, enforced by scripts/external_wrapper.py's paid-call
// budget gate). The reachable/authenticated and malformed-image cases
// below are free - same reasoning as scan.weekly.test.ts's corrupted-image
// case: Anthropic rejects an undecodable image at the request layer
// before any model call happens.
import assert from "node:assert/strict";
import { Buffer } from "node:buffer";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { extractFields } from "../claude.ts";
import { DOC_TYPE_CONFIG } from "../docTypes.ts";
import type { DocType } from "../docTypes.ts";
import type { MediaType } from "../types.ts";

const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
if (!ANTHROPIC_API_KEY) {
  throw new Error(
    "External test credentials missing: ANTHROPIC_API_KEY is not set in the environment.",
  );
}

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../..");

// One real fixture per doc type (same files tests/test_claude_vision_external.py's
// pass-pool journey uses on the Python side), with the field names each
// platform's parser actually reads from the forced tool_use output.
const FIXTURES: Record<DocType, { file: string; mediaType: MediaType; expectFields: string[] }> = {
  truck_tag: {
    file: "AddieTag.jpg",
    mediaType: "image/jpeg",
    expectFields: ["manufacturer", "gvwr_lb", "front_gawr_lb", "rear_gawr_lb"],
  },
  trailer_tag: {
    file: "GooseTag.jpg",
    mediaType: "image/jpeg",
    expectFields: ["manufacturer", "gvwr_lb", "gawr_per_axle_lb", "uvw_lb"],
  },
  scale_ticket: {
    file: "CatScale-Ticket.jpg",
    mediaType: "image/jpeg",
    expectFields: ["location_name", "scale_number", "steer_axle_lb", "gross_weight_lb"],
  },
};

test("[anthropic] reachable and authenticated: a bad key is rejected with a real auth error", async () => {
  await assert.rejects(
    extractFields("sk-ant-api03-invalid-external-test-key", "aGVsbG8=", "image/jpeg", DOC_TYPE_CONFIG.truck_tag),
    (err: unknown) => {
      const status = (err as { status?: unknown }).status;
      const message = err instanceof Error ? err.message : String(err);
      return status === 401 || /401|authentication/i.test(message);
    },
  );
});

test("[anthropic] error contract: a corrupted/undecodable image is rejected before any model call", async () => {
  const fullImage = readFileSync(path.join(REPO_ROOT, "streamlit_app", "assets", "wtwt_logo.png"));
  const truncated = Buffer.from(fullImage.subarray(0, 200)).toString("base64");

  await assert.rejects(extractFields(ANTHROPIC_API_KEY, truncated, "image/png", DOC_TYPE_CONFIG.truck_tag), (err: unknown) => {
    const status = (err as { status?: unknown }).status;
    return status === 400 || status === 422;
  });
});

for (const [docType, fixture] of Object.entries(FIXTURES) as [DocType, (typeof FIXTURES)[DocType]][]) {
  test(`[anthropic] response shape and journey: a real ${docType} scan returns the fields its parser reads`, async () => {
    const imagePath = path.join(REPO_ROOT, "ExampleDocs", fixture.file);
    const imageBase64 = readFileSync(imagePath, "base64");

    const fields = await extractFields(ANTHROPIC_API_KEY, imageBase64, fixture.mediaType, DOC_TYPE_CONFIG[docType]);

    assert.equal(typeof fields, "object");
    for (const field of fixture.expectFields) {
      assert.ok(field in fields, `expected "${field}" in ${JSON.stringify(fields)}`);
    }
  });
}
