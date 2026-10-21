// Offline tests for the sign-in helper android/test-weekly.ps1 shells out to (#75). Sign-in runs
// against a mocked fetch with credentials passed in, so nothing touches Supabase or web/.env.local.
import "./requireInstall.ts";
import assert from "node:assert/strict";
import test, { type TestContext } from "node:test";
import { generateTestKeyPair, signToken } from "./accountTokenFixtures.ts";
import { fundedSession, runCli } from "./liveTokenCli.ts";

const FAKE_ENV = {
  VITE_SUPABASE_URL: "https://fake-project.supabase.co",
  VITE_SUPABASE_PUBLISHABLE_KEY: "sb_publishable_fake",
  WEB_EXTERNAL_TEST_EMAIL: "funded@example.com",
  WEB_EXTERNAL_TEST_PASSWORD: "funded-secret-pw",
};

async function mockSignIn(t: TestContext, accountId: string) {
  const token = await signToken(accountId, { key: await generateTestKeyPair() });
  t.mock.method(globalThis, "fetch", async () => new Response(JSON.stringify({ access_token: token }), { status: 200 }));
  return token;
}

function capture() {
  const out: string[] = [];
  const err: string[] = [];
  return { out, err, writeOut: (line: string) => out.push(line), writeErr: (line: string) => err.push(line) };
}

test("fundedSession signs in the funded account and returns its token with the account id the token names", async (t) => {
  const token = await mockSignIn(t, "11111111-2222-3333-4444-555555555555");

  assert.deepEqual(await fundedSession(FAKE_ENV, {}), {
    accessToken: token,
    accountId: "11111111-2222-3333-4444-555555555555",
  });
});

test("runCli prints the session as one JSON line and exits 0", async (t) => {
  const token = await mockSignIn(t, "acct-1");
  const { out, err, writeOut, writeErr } = capture();

  const code = await runCli(writeOut, writeErr, FAKE_ENV, {});

  assert.equal(code, 0);
  assert.deepEqual(err, []);
  assert.equal(out.length, 1);
  assert.deepEqual(JSON.parse(out[0]!), { accessToken: token, accountId: "acct-1" });
});

test("runCli takes a credential from the env file when the environment lacks it", async (t) => {
  await mockSignIn(t, "acct-2");
  const { WEB_EXTERNAL_TEST_PASSWORD, ...envWithoutPassword } = FAKE_ENV;
  const { out, writeOut, writeErr } = capture();

  const code = await runCli(writeOut, writeErr, envWithoutPassword, { WEB_EXTERNAL_TEST_PASSWORD });

  assert.equal(code, 0);
  assert.equal(JSON.parse(out[0]!).accountId, "acct-2");
});

test("runCli with a missing credential exits 1 naming the variable, never printing a value, and never calls Supabase", async (t) => {
  const { WEB_EXTERNAL_TEST_PASSWORD: _omitted, ...envWithoutPassword } = FAKE_ENV;
  const fetchMock = t.mock.method(globalThis, "fetch", async () => new Response("{}", { status: 200 }));
  const { out, err, writeOut, writeErr } = capture();

  const code = await runCli(writeOut, writeErr, envWithoutPassword, {});

  assert.equal(code, 1);
  assert.deepEqual(out, []);
  assert.match(err.join("\n"), /WEB_EXTERNAL_TEST_PASSWORD/);
  assert.doesNotMatch(err.join("\n"), /funded@example\.com|sb_publishable_fake/);
  assert.equal(fetchMock.mock.callCount(), 0);
});

test("runCli with a rejected sign-in exits 1 with the status and none of the credentials", async (t) => {
  t.mock.method(globalThis, "fetch", async () => new Response("{}", { status: 400 }));
  const { out, err, writeOut, writeErr } = capture();

  const code = await runCli(writeOut, writeErr, FAKE_ENV, {});

  assert.equal(code, 1);
  assert.deepEqual(out, []);
  assert.match(err.join("\n"), /HTTP 400/);
  assert.doesNotMatch(err.join("\n"), /funded-secret-pw|funded@example\.com/);
});
