// The one structured log line per scan (#183), checked at the request handler:
// worker.fetch runs the real wiring with fetch faked for RevenueCat, Anthropic
// and Supabase's JWKS endpoint, and the console is captured. Every request
// below carries a token, an image and fake secrets, so the same runs also show
// that none of them reach the log.
import "./requireInstall.ts";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test, { beforeEach, type TestContext } from "node:test";
import { jwksUrl } from "./accountTokenContract.ts";
import { generateTestKeyPair, jwksFor, signToken, TEST_SUPABASE_URL } from "./accountTokenFixtures.ts";
import { clearJwksCache } from "./auth.ts";
import worker from "./index.ts";
import { logScanResponse } from "./scanLog.ts";
import type { Env } from "./types.ts";

const ANTHROPIC_KEY = "sk-ant-FAKE-anthropic-key-4f9c";
const REVENUECAT_KEY = "sk_FAKE_revenuecat_key_7b21";
const ACCOUNT_ID = "acct-5d1f0c8e-3a77";
const EMAIL = "tester.fake@example.com";
const IMAGE = "SU1BR0VfQllURVNfRkFLRV9QSE9UTw==";

const env: Env = {
  ANTHROPIC_API_KEY: ANTHROPIC_KEY,
  REVENUECAT_SECRET_KEY: REVENUECAT_KEY,
  REVENUECAT_PROJECT_ID: "proj",
  REVENUECAT_CURRENCY_CODE: "SCAN",
  SUPABASE_URL: TEST_SUPABASE_URL,
};

const signingKey = await generateTestKeyPair();
// A real Supabase token also carries the account's email.
const token = await signToken(ACCOUNT_ID, { key: signingKey, claims: { email: EMAIL } });

beforeEach(() => clearJwksCache());

const toolUse = {
  id: "msg_test",
  type: "message",
  role: "assistant",
  model: "claude-sonnet-5",
  content: [{ type: "tool_use", id: "toolu_1", name: "record_truck_tag", input: { manufacturer: "Ford" } }],
  stop_reason: "tool_use",
  stop_sequence: null,
  usage: { input_tokens: 1, output_tokens: 1 },
};
const unreadable = { ...toolUse, content: [{ type: "text", text: "I can't read this label." }], stop_reason: "end_turn" };

// RevenueCat's error bodies can echo the customer.
const echoesCustomer = { message: `no balance for customer ${ACCOUNT_ID} <${EMAIL}>` };

interface Scenario {
  name: string;
  outcome: string;
  docType: string | null;
  refunded: boolean;
  // The scan request; "no-auth" sends no Authorization header.
  body?: unknown;
  authorization?: string | null;
  jwks?: "ok" | "down";
  // RevenueCat answers, in call order: the spend, then the refund.
  revenuecat?: Array<{ status: number; body?: unknown } | "throw">;
  anthropic?: unknown;
  // Makes the handler throw before it can answer.
  breakIdempotencyKey?: boolean;
}

const validBody = { doc_type: "truck_tag", image_base64: IMAGE, media_type: "image/jpeg", client_request_id: "req-1" };

const scenarios: Scenario[] = [
  { name: "a delivered scan", outcome: "delivered", docType: "truck_tag", refunded: false, anthropic: toolUse },
  {
    name: "no credits left",
    outcome: "insufficient_credits",
    docType: "truck_tag",
    refunded: false,
    revenuecat: [{ status: 422, body: echoesCustomer }],
  },
  {
    name: "RevenueCat answers with an error",
    outcome: "billing_error",
    docType: "truck_tag",
    refunded: false,
    revenuecat: [{ status: 500, body: echoesCustomer }],
  },
  {
    name: "RevenueCat cannot be reached",
    outcome: "billing_error",
    docType: "truck_tag",
    refunded: false,
    revenuecat: ["throw"],
  },
  {
    name: "a failed extraction whose credit is refunded",
    outcome: "extraction_failed",
    docType: "truck_tag",
    refunded: true,
    anthropic: unreadable,
  },
  {
    name: "a failed extraction whose refund fails too",
    outcome: "extraction_failed_no_refund",
    docType: "truck_tag",
    refunded: false,
    anthropic: unreadable,
    revenuecat: [{ status: 200 }, { status: 500, body: echoesCustomer }],
  },
  {
    name: "no Authorization header",
    outcome: "unauthorized",
    docType: null,
    refunded: false,
    authorization: null,
  },
  {
    name: "Supabase's keys cannot be loaded",
    outcome: "auth_unavailable",
    docType: null,
    refunded: false,
    jwks: "down",
  },
  { name: "a body that is not JSON", outcome: "bad_request", docType: null, refunded: false, body: "{not json" },
  {
    name: "an unknown document type",
    outcome: "bad_request",
    docType: null,
    refunded: false,
    body: { ...validBody, doc_type: "receipt" },
  },
  {
    name: "a handler that throws",
    outcome: "internal_error",
    docType: null,
    refunded: false,
    breakIdempotencyKey: true,
  },
];

interface Run {
  response: Response | undefined;
  // Everything the Worker wrote to the console, one entry per call.
  logged: string[];
}

async function run(t: TestContext, scenario: Scenario): Promise<Run> {
  const logged: string[] = [];
  for (const level of ["log", "error", "warn", "info", "debug"] as const) {
    t.mock.method(console, level, (...args: unknown[]) => {
      logged.push(args.map((arg) => (typeof arg === "string" ? arg : JSON.stringify(arg) ?? String(arg))).join(" "));
    });
  }

  let revenuecatCalls = 0;
  t.mock.method(globalThis, "fetch", async (url: string | URL) => {
    const urlStr = String(url);
    if (urlStr === jwksUrl(TEST_SUPABASE_URL)) {
      if (scenario.jwks === "down") return new Response("down", { status: 500 });
      return Response.json(jwksFor(signingKey));
    }
    if (urlStr.includes("revenuecat.com")) {
      const answer = scenario.revenuecat?.[revenuecatCalls++] ?? { status: 200, body: { items: [{ balance: 4 }] } };
      // A network error's message names the URL, which holds the account id.
      if (answer === "throw") throw new TypeError(`fetch failed: ${urlStr}`);
      return Response.json(answer.body ?? {}, { status: answer.status });
    }
    if (urlStr.includes("anthropic.com")) return Response.json(scenario.anthropic ?? toolUse);
    throw new Error(`Unexpected fetch to ${urlStr}`);
  });
  if (scenario.breakIdempotencyKey) {
    t.mock.method(crypto.subtle, "digest", async () => {
      throw new Error(`digest failed for ${ACCOUNT_ID}`);
    });
  }

  const body = scenario.body ?? validBody;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (scenario.authorization !== null) headers.Authorization = scenario.authorization ?? `Bearer ${token}`;
  const request = new Request("https://example.com/v1/scan", {
    method: "POST",
    headers,
    body: typeof body === "string" ? body : JSON.stringify(body),
  });

  try {
    return { response: await worker.fetch(request, env), logged };
  } catch {
    return { response: undefined, logged };
  }
}

function scanLines(logged: string[]): Array<Record<string, unknown>> {
  const lines: Array<Record<string, unknown>> = [];
  for (const entry of logged) {
    try {
      const parsed = JSON.parse(entry) as Record<string, unknown>;
      if (parsed.event === "scan") lines.push(parsed);
    } catch {
      // Not a structured line.
    }
  }
  return lines;
}

test("[sanity] every scan writes exactly one structured line: outcome, document type, duration, refunded", async (t) => {
  for (const scenario of scenarios) {
    await t.test(scenario.name, async (st) => {
      const { logged } = await run(st, scenario);
      const lines = scanLines(logged);
      assert.equal(lines.length, 1, `expected one scan line, got: ${logged.join(" | ")}`);
      const [line] = lines;
      assert.deepEqual(Object.keys(line!).sort(), ["doc_type", "duration_ms", "event", "outcome", "refunded"]);
      assert.equal(line!.outcome, scenario.outcome);
      assert.equal(line!.doc_type, scenario.docType);
      assert.equal(line!.refunded, scenario.refunded);
      assert.ok(Number.isInteger(line!.duration_ms) && (line!.duration_ms as number) >= 0, "duration_ms is whole milliseconds");
    });
  }
});

test("[sanity] no token, image, key, email or account id reaches the log on any path", async (t) => {
  const secrets = { token, image: IMAGE, ANTHROPIC_KEY, REVENUECAT_KEY, EMAIL, ACCOUNT_ID, claims: token.split(".")[1]! };
  for (const scenario of scenarios) {
    await t.test(scenario.name, async (st) => {
      const { logged } = await run(st, scenario);
      assert.ok(logged.length > 0, "the run logged something, so the check below is not vacuous");
      const everything = logged.join("\n");
      for (const [name, secret] of Object.entries(secrets)) {
        assert.ok(!everything.includes(secret), `${name} leaked into the log: ${everything}`);
      }
    });
  }
});

test("duration_ms is the time the request took, in milliseconds", async (t) => {
  // Every read of the clock is one second later than the last.
  let now = Date.now();
  t.mock.method(Date, "now", () => (now += 1000));
  const { logged } = await run(t, scenarios[0]!);
  const duration = scanLines(logged)[0]!.duration_ms as number;
  assert.ok(duration >= 1000 && duration % 1000 === 0, `got ${duration}`);
});

test("a response the log cannot read is logged as unknown, never thrown", async (t) => {
  const logged: string[] = [];
  t.mock.method(console, "error", (...args: unknown[]) => logged.push(args.join(" ")));
  await logScanResponse(new Response("<html>not json</html>", { status: 500 }), "truck_tag", Date.now());
  await logScanResponse(Response.json({ ok: false }, { status: 500 }), null, Date.now());
  assert.deepEqual(
    scanLines(logged).map((line) => line.outcome),
    ["unknown", "unknown"],
  );
});

test("requests that are not scans write no scan line", async (t) => {
  const logged: string[] = [];
  for (const level of ["log", "error", "warn", "info", "debug"] as const) {
    t.mock.method(console, level, (...args: unknown[]) => logged.push(args.join(" ")));
  }
  t.mock.method(globalThis, "fetch", async () => {
    throw new Error("a non-scan request must not call out");
  });

  const preflight = await worker.fetch(
    new Request("https://example.com/v1/scan", {
      method: "OPTIONS",
      headers: { Origin: "https://rigcheck-web.pages.dev", "Access-Control-Request-Method": "POST" },
    }),
    env,
  );
  assert.equal(preflight.status, 204);
  const unknown = await worker.fetch(new Request("https://example.com/health", { method: "GET" }), env);
  assert.equal(unknown.status, 404);
  const wrongMethod = await worker.fetch(new Request("https://example.com/v1/scan", { method: "GET" }), env);
  assert.equal(wrongMethod.status, 404);

  assert.deepEqual(scanLines(logged), []);
  assert.deepEqual(logged, [], "and nothing else is logged for them either");
});

test("wrangler.toml keeps Workers Logs on, with every request kept", () => {
  const toml = readFileSync(join(import.meta.dirname, "..", "wrangler.toml"), "utf8");
  const section = toml.split(/^\[observability\]/m)[1]?.split(/^\[/m)[0];
  assert.ok(section, "wrangler.toml has an [observability] table");
  assert.match(section, /^enabled\s*=\s*true\s*$/m);
  assert.match(section, /^head_sampling_rate\s*=\s*1\s*$/m);
});
