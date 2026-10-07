// Offline tests for the live suites' credential and sign-in helper. Sign-in is
// exercised against a mocked fetch, with credentials supplied through
// process.env (which wins over web/.env.local), so nothing touches Supabase.
import assert from "node:assert/strict";
import test, { type TestContext } from "node:test";
import { generateTestKeyPair, signToken } from "./accountTokenFixtures.ts";
import {
  liveCredentialsMissing,
  liveSupabaseUrl,
  missingVars,
  parseEnvText,
  readEnvFile,
  requireVars,
  signInTestAccount,
  subjectOf,
} from "./liveToken.ts";

const FAKE_ENV = {
  VITE_SUPABASE_URL: "https://fake-project.supabase.co",
  VITE_SUPABASE_PUBLISHABLE_KEY: "sb_publishable_fake",
  WEB_EXTERNAL_TEST_EMAIL: "funded@example.com",
  WEB_EXTERNAL_TEST_PASSWORD: "funded-secret-pw",
  WEB_EXTERNAL_TEST_NOCREDITS_EMAIL: "empty@example.com",
  WEB_EXTERNAL_TEST_NOCREDITS_PASSWORD: "empty-secret-pw",
};

function withFakeEnv(t: TestContext) {
  const saved = Object.fromEntries(Object.keys(FAKE_ENV).map((name) => [name, process.env[name]]));
  Object.assign(process.env, FAKE_ENV);
  t.after(() => {
    for (const [name, value] of Object.entries(saved)) {
      if (value === undefined) delete process.env[name];
      else process.env[name] = value;
    }
  });
}

test("parseEnvText reads KEY=value lines, skipping comments and blanks, stripping matching quotes, keeping '=' in values", () => {
  const parsed = parseEnvText('# comment\r\nA=1\r\n\r\nB="two words"\nC=\'x\'\nD=a=b=c\n  E = spaced \nlower=ignored\n');
  assert.deepEqual(parsed, { A: "1", B: "two words", C: "x", D: "a=b=c", E: "spaced" });
});

test("missingVars reports names only: the environment wins, the file is the fallback, empty values count as missing", () => {
  const missing = missingVars(["A", "B", "C", "D"], { A: "from-env", C: "" }, { B: "from-file", C: "", D: "" });
  assert.deepEqual(missing, ["C", "D"]);
});

test("requireVars returns env values first, then file values, and throws naming (not showing) what's missing", () => {
  assert.deepEqual(requireVars(["A", "B"], { A: "env-a" }, { A: "file-a", B: "file-b" }), { A: "env-a", B: "file-b" });
  assert.throws(
    () => requireVars(["A", "SECRET_NAME"], { A: "1" }, {}),
    (err: Error) => /SECRET_NAME/.test(err.message) && !/\b1\b/.test(err.message.split(":").pop() ?? ""),
  );
});

test("readEnvFile returns no values for a file that doesn't exist, instead of throwing", () => {
  assert.deepEqual(readEnvFile("G:/does/not/exist/.env.local"), {});
});

test("liveSupabaseUrl returns the Supabase project URL", (t) => {
  withFakeEnv(t);
  assert.equal(liveSupabaseUrl(), "https://fake-project.supabase.co");
});

test("liveCredentialsMissing is empty when everything is in the environment, and names only what an account needs", (t) => {
  withFakeEnv(t);
  assert.deepEqual(liveCredentialsMissing(["funded", "noCredits"]), []);
  delete process.env.WEB_EXTERNAL_TEST_NOCREDITS_PASSWORD;
  const missing = liveCredentialsMissing(["funded"]);
  assert.ok(!missing.includes("WEB_EXTERNAL_TEST_NOCREDITS_PASSWORD"), "the no-credits account isn't needed here");
});

test("subjectOf returns the token's sub, and throws without one", async () => {
  const key = await generateTestKeyPair();
  assert.equal(subjectOf(await signToken("user-uuid-1", { key })), "user-uuid-1");
  const withoutSub = await signToken("user-uuid-1", { key, omitClaims: ["sub"] });
  assert.throws(() => subjectOf(withoutSub), /no sub claim/);
  assert.throws(() => subjectOf("garbage"), /no sub claim/);
});

test("signInTestAccount posts the account's credentials to Supabase's password grant and returns the access token", async (t) => {
  withFakeEnv(t);
  const calls: Array<{ url: string; init: RequestInit }> = [];
  t.mock.method(globalThis, "fetch", async (url: string | URL, init: RequestInit) => {
    calls.push({ url: String(url), init });
    return new Response(JSON.stringify({ access_token: "the.access.token" }), { status: 200 });
  });

  assert.equal(await signInTestAccount("noCredits"), "the.access.token");

  assert.equal(calls.length, 1);
  assert.equal(calls[0]!.url, "https://fake-project.supabase.co/auth/v1/token?grant_type=password");
  assert.equal((calls[0]!.init.headers as Record<string, string>).apikey, "sb_publishable_fake");
  assert.deepEqual(JSON.parse(String(calls[0]!.init.body)), {
    email: "empty@example.com",
    password: "empty-secret-pw",
  });
});

test("a failed sign-in throws naming the account and HTTP status, never the credentials", async (t) => {
  withFakeEnv(t);
  t.mock.method(globalThis, "fetch", async () => new Response("{}", { status: 400 }));
  await assert.rejects(signInTestAccount("funded"), (err: Error) => {
    assert.match(err.message, /funded.*HTTP 400/);
    assert.doesNotMatch(err.message, /funded-secret-pw|funded@example\.com/);
    return true;
  });
});

test("a sign-in response without an access_token throws", async (t) => {
  withFakeEnv(t);
  t.mock.method(globalThis, "fetch", async () => new Response("{}", { status: 200 }));
  await assert.rejects(signInTestAccount("funded"), /no access_token/);
});
