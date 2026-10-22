// Pro and the Scan Credit balance carry across Android and Web (#27) only while three
// surfaces name the same things in RevenueCat: the Worker spends the `SCAN` currency,
// and each client reads that currency and the `pro` entitlement. A rename on one side
// does not fail anywhere else - the other clients just show Free or a zero balance for
// an account that has both - so this reads the other surfaces' own source and fails
// where the drift starts. It also pins that no client writes a price into its screens:
// both show the string RevenueCat gives them, which is what keeps one price on every
// platform (ADR-0006). That the two RevenueCat products carry the same price is a
// dashboard fact no offline test can see.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../../..");
const WRANGLER = path.join(ROOT, "workers/scan-proxy/wrangler.toml");
const ANDROID_BILLING = path.join(ROOT, "android/app/src/main/java/com/rigcheck/app/data/RevenueCatManager.kt");
const ANDROID_PAYWALL = path.join(ROOT, "android/app/src/main/java/com/rigcheck/app/ui/screens/PaywallScreen.kt");
const WEB_BILLING = path.join(ROOT, "web/src/revenueCatBilling.ts");
const WEB_SCREENS = ["web/src/components/ProPaywall.tsx", "web/src/components/ScanPacks.tsx", "web/src/screens/Account.tsx"].map(
  (file) => path.join(ROOT, file),
);

// The one quoted value assigned by the pattern in a file; a failed match names the file, so a
// renamed constant or a moved file is a loud failure, not a silent pass.
function valueIn(file: string, pattern: RegExp, what: string): string {
  const match = pattern.exec(readFileSync(file, "utf8"));
  assert.ok(match, `${path.relative(ROOT, file)} no longer defines ${what} in the form this test reads; update this test with it`);
  return match[1];
}

test("[sanity] the Worker, Android and Web all use the same Scan Credit currency code", () => {
  const worker = valueIn(WRANGLER, /^REVENUECAT_CURRENCY_CODE\s*=\s*"([^"]+)"/m, "REVENUECAT_CURRENCY_CODE");
  const android = valueIn(ANDROID_BILLING, /private const val SCAN_CURRENCY_CODE = "([^"]+)"/, "SCAN_CURRENCY_CODE");
  const web = valueIn(WEB_BILLING, /const SCAN_CURRENCY_CODE = '([^']+)'/, "SCAN_CURRENCY_CODE");
  assert.deepEqual({ android, web }, { android: worker, web: worker });
});

test("[sanity] Android and Web read Pro from the same entitlement", () => {
  const android = valueIn(ANDROID_BILLING, /private const val PRO_ENTITLEMENT_ID = "([^"]+)"/, "PRO_ENTITLEMENT_ID");
  const web = valueIn(WEB_BILLING, /const DEFAULT_PRO_ENTITLEMENT_ID = '([^']+)'/, "DEFAULT_PRO_ENTITLEMENT_ID");
  assert.equal(android, web);
});

test("[sanity] neither client writes a dollar amount into its screens and each shows RevenueCat's formatted price", () => {
  const screens = [ANDROID_PAYWALL, ...WEB_SCREENS];
  for (const file of screens) {
    const text = readFileSync(file, "utf8");
    assert.doesNotMatch(text, /\$\s?\d/, `${path.relative(ROOT, file)} contains a dollar amount; prices come from RevenueCat only`);
  }
  assert.match(readFileSync(ANDROID_PAYWALL, "utf8"), /pkg\.product\.price\.formatted/);
  assert.match(readFileSync(WEB_BILLING, "utf8"), /currentPrice\.formattedPrice/);
});
