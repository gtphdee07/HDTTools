// Integration-layer tests for the router/entry point - proves index.ts
// correctly glues parseScanRequest and runScan together, and handles the
// routing/parsing failures neither of those modules is responsible for.
// index.ts always uses runScan's real defaultScanDeps (no injection point
// at this layer), so these tests are also the only place the real
// dependency-injection wiring - defaultScanDeps, the lazy claude.ts import -
// gets exercised at all; every scan.test.ts case uses fake deps instead.
import assert from "node:assert/strict";
import test from "node:test";
import worker from "./index.ts";
import type { Env } from "./types.ts";

const env: Env = {
  ANTHROPIC_API_KEY: "sk-ant-test",
  REVENUECAT_SECRET_KEY: "sk_test",
  REVENUECAT_PROJECT_ID: "proj",
  REVENUECAT_CURRENCY_CODE: "SCAN",
};

const validBody = {
  app_user_id: "user-1",
  doc_type: "truck_tag",
  image_base64: "aGVsbG8=",
  media_type: "image/jpeg",
};

function postScan(body: unknown): Request {
  return new Request("https://example.com/v1/scan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });
}

// Real defaultScanDeps means a single mocked global fetch has to stand in
// for both the RevenueCat and Anthropic APIs at once - route by URL so each
// gets a response shaped like its real API, not one canned response for both.
function mockExternalApis(t: import("node:test").TestContext, anthropicResponse: unknown, anthropicStatus = 200) {
  let revenuecatCalls = 0;
  t.mock.method(globalThis, "fetch", async (url: string | URL) => {
    const urlStr = String(url);
    if (urlStr.includes("revenuecat.com")) {
      revenuecatCalls++;
      return new Response(JSON.stringify({ items: [{ balance: 4 }] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (urlStr.includes("anthropic.com")) {
      // The Anthropic SDK keys its response parsing off Content-Type.
      return new Response(JSON.stringify(anthropicResponse), {
        status: anthropicStatus,
        headers: { "Content-Type": "application/json" },
      });
    }
    throw new Error(`Unexpected fetch to ${urlStr}`);
  });
  return { revenuecatCalls: () => revenuecatCalls };
}

test("[sanity] a valid POST /v1/scan runs the real dependency wiring end-to-end and returns extracted fields", async (t) => {
  mockExternalApis(t, {
    id: "msg_test",
    type: "message",
    role: "assistant",
    model: "claude-sonnet-5",
    content: [{ type: "tool_use", id: "toolu_1", name: "record_truck_tag", input: { manufacturer: "Ford" } }],
    stop_reason: "tool_use",
    stop_sequence: null,
    usage: { input_tokens: 1, output_tokens: 1 },
  });

  const res = await worker.fetch(postScan(validBody), env);
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { ok: true, doc_type: "truck_tag", fields: { manufacturer: "Ford" } });
});

test("extraction failure through the real wiring triggers a real refund and reports extraction_failed", async (t) => {
  const mocks = mockExternalApis(t, {
    id: "msg_test",
    type: "message",
    role: "assistant",
    model: "claude-sonnet-5",
    content: [{ type: "text", text: "I can't read this label." }],
    stop_reason: "end_turn",
    stop_sequence: null,
    usage: { input_tokens: 1, output_tokens: 1 },
  });

  const res = await worker.fetch(postScan(validBody), env);
  assert.equal(res.status, 502);
  assert.equal(((await res.json()) as { code: string }).code, "extraction_failed");
  assert.equal(mocks.revenuecatCalls(), 2, "expected one spend call and one refund call to RevenueCat");
});

test("GET /v1/scan falls through to the generic 404, not a method-specific error", async () => {
  const res = await worker.fetch(new Request("https://example.com/v1/scan", { method: "GET" }), env);
  assert.equal(res.status, 404);
  assert.equal(((await res.json()) as { code: string }).code, "not_found");
});

test("an unknown route returns the same generic 404", async () => {
  const res = await worker.fetch(new Request("https://example.com/health", { method: "GET" }), env);
  assert.equal(res.status, 404);
  assert.equal(((await res.json()) as { code: string }).code, "not_found");
});

test("malformed JSON body returns 400 bad_request, not a 500", async () => {
  const res = await worker.fetch(postScan("{not json"), env);
  assert.equal(res.status, 400);
  const body = (await res.json()) as { code: string; message: string };
  assert.equal(body.code, "bad_request");
  assert.match(body.message, /valid JSON/);
});

test("valid JSON that fails parseScanRequest returns 400 with that specific message, not swallowed", async () => {
  const { app_user_id: _app_user_id, ...rest } = validBody;
  const res = await worker.fetch(postScan(rest), env);
  assert.equal(res.status, 400);
  const body = (await res.json()) as { code: string; message: string };
  assert.equal(body.code, "bad_request");
  assert.match(body.message, /app_user_id/);
});
