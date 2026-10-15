// The Scan service's time limits have to agree across three surfaces (#112): a
// client that gives up before the Worker can finish abandons a Scan the
// Worker then completes and charges for, and the user never sees the result.
// This reads the other two surfaces' own source for their limits (the way
// docTypes.test.ts reads ScanFieldMapping.kt), so a change on any side that
// breaks the agreement fails here instead of drifting unnoticed. The
// arithmetic and the reasoning are written down in CONTEXT.md "Time limits".
import "./requireInstall.ts";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { JWKS_TIMEOUT_MS } from "./auth.ts";
import { REVENUECAT_TIMEOUT_MS } from "./revenuecat.ts";
// Dynamic for claude.ts, which imports the SDK (see requireInstall.ts).
const { ANTHROPIC_MAX_RETRIES, ANTHROPIC_TIMEOUT_MS } = await import("./claude.ts");

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ANDROID_CLIENT = path.resolve(HERE, "../../../android/app/src/main/java/com/rigcheck/app/data/ScanApiClient.kt");
const WEB_API = path.resolve(HERE, "../../../web/src/api.ts");

function androidReadTimeoutMs(): number {
  const match = /\.readTimeout\(\s*(\d+)\s*,\s*TimeUnit\.SECONDS\s*\)/.exec(readFileSync(ANDROID_CLIENT, "utf8"));
  assert.ok(match, "ScanApiClient.kt no longer sets .readTimeout(<n>, TimeUnit.SECONDS); update this test with it");
  return Number(match[1]) * 1000;
}

function webScanTimeoutMs(): number {
  const match = /export const SCAN_TIMEOUT_MS = ([\d_]+);/.exec(readFileSync(WEB_API, "utf8"));
  assert.ok(match, "web/src/api.ts no longer exports SCAN_TIMEOUT_MS as a number literal; update this test with it");
  return Number(match[1].replaceAll("_", ""));
}

// The longest a single Scan request can keep the Worker busy: verify the
// sign-in key (one fetch), spend the credit, make the one Claude attempt, and
// refund when it fails. Each step is individually time-limited. With no
// retries there is no back-off or Retry-After wait to add.
function workerWorstCaseMs(): number {
  assert.equal(
    ANTHROPIC_MAX_RETRIES,
    0,
    "with retries the worst case also holds back-off and Retry-After waits (up to 60 s each), which this sum does not count",
  );
  return JWKS_TIMEOUT_MS + REVENUECAT_TIMEOUT_MS + ANTHROPIC_TIMEOUT_MS * (1 + ANTHROPIC_MAX_RETRIES) + REVENUECAT_TIMEOUT_MS;
}

test("[sanity] the Worker's worst case is 5 + 10 + 20 + 10 = 45 s", () => {
  assert.equal(workerWorstCaseMs(), 45_000);
});

test("[sanity] Android's read timeout is longer than the Worker's worst case", () => {
  assert.ok(
    workerWorstCaseMs() < androidReadTimeoutMs(),
    `the Worker can take ${workerWorstCaseMs()} ms but Android gives up after ${androidReadTimeoutMs()} ms`,
  );
});

test("[sanity] Web's Scan time limit is longer than the Worker's worst case", () => {
  assert.ok(
    workerWorstCaseMs() < webScanTimeoutMs(),
    `the Worker can take ${workerWorstCaseMs()} ms but Web gives up after ${webScanTimeoutMs()} ms`,
  );
});
