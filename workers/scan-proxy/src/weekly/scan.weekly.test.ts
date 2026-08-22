// Weekly tier — real, bounded network calls against the actual deployed
// Worker and RevenueCat, using dedicated disposable test customers (never
// smoke-test-user, which stays reserved for manual Android field testing).
// Deliberately kept out of `src/*.test.ts`'s glob (used by `npm test`/
// `npm run test:sanity`) by living in this subdirectory — run explicitly
// via `npm run test:weekly`, not on every commit.
import assert from "node:assert/strict";
import test from "node:test";

const SCAN_ENDPOINT = "https://rigcheck-scan-proxy.wanderingtrailswaggingtails.workers.dev/v1/scan";

// weekly-test-user-no-credits: created 2026-08-21 specifically for this
// case, deliberately left at its default zero SCAN balance (no dashboard
// grant needed - RevenueCat.entitlement_check has nothing to do with this
// path either; see NEXT_STEPS.md for why an entitlement-based test
// customer wouldn't exercise any real logic as of this writing). A tiny
// placeholder image is enough - spendCredit fails and the request short-
// circuits before Claude is ever called, so this costs nothing per run.
test("a customer with no SCAN credits gets 402 insufficient_credits, never reaches Claude", async () => {
  const response = await fetch(SCAN_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      app_user_id: "weekly-test-user-no-credits",
      doc_type: "truck_tag",
      image_base64: "aGVsbG8=",
      media_type: "image/jpeg",
    }),
  });

  assert.equal(response.status, 402);
  const body = await response.json();
  assert.deepEqual(body, {
    ok: false,
    code: "insufficient_credits",
    message: "Not enough scan credits.",
  });
});
