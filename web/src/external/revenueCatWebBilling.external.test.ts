import { beforeAll, describe, expect, it } from 'vitest';
import { createClient } from '@supabase/supabase-js';
import { ErrorCode, ProductType, Purchases, PurchasesError } from '@revenuecat/purchases-js';
import { createRevenueCatBillingClient, readBillingConfig } from '../revenueCatBilling';
import type { BillingConfig } from '../revenueCatBilling';
import { REQUIRED, REVENUECAT, readConfig } from './config';

// External suite (ADR-0008): real calls to RevenueCat Web Billing through the real
// @revenuecat/purchases-js SDK, run only via `npm run test:external`. The
// "[revenuecat-web-billing]" name tag is what the wrapper filters on.
// Reads only, and never buys anything: a sandbox purchase stays the human checklist in #11. The one side
// effect is that RevenueCat creates a customer for NO_PURCHASES_USER the first time it sees it.
// The test account is the Supabase one from scripts/wizard_web_external_test_user.sh: its
// Supabase user id is the RevenueCat app user id, exactly as the site identifies a customer.

// The virtual currency revenueCatBilling.ts reads the scan balance from.
const SCAN_CURRENCY = 'SCAN';
const HAS_DIGIT = /\d/;

// A well-formed key the server has never issued (the SDK rejects a malformed one locally).
const WRONG_KEY = 'rcb_external_suite_wrong_key';
// An app user id that never buys anything. RevenueCat creates a customer on first sight, so a
// fixed id keeps that to one customer instead of one per run.
const NO_PURCHASES_USER = 'external-suite-no-purchases';

describe('[revenuecat-web-billing] RevenueCat Web Billing live contract', () => {
  let billing: BillingConfig;
  let testAccountId: string;

  // The SDK keeps one global instance; configuring again closes the previous one, so every test
  // configures its own and nothing depends on test order.
  const sdkFor = (appUserId: string, apiKey = billing.apiKey) => Purchases.configure({ apiKey, appUserId });

  beforeAll(async () => {
    const env = import.meta.env as Record<string, string | undefined>;
    const cfg = readConfig(env, [...REQUIRED, ...REVENUECAT]);
    // built exactly as the site builds it, so the entitlement id and package overrides are the site's
    billing = readBillingConfig(env)!;

    const supabase = createClient(cfg.VITE_SUPABASE_URL, cfg.VITE_SUPABASE_PUBLISHABLE_KEY, {
      auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
    });
    const { data, error } = await supabase.auth.signInWithPassword({
      email: cfg.WEB_EXTERNAL_TEST_EMAIL,
      password: cfg.WEB_EXTERNAL_TEST_PASSWORD,
    });
    if (error || !data.user) throw new Error('External test account could not sign in');
    testAccountId = data.user.id;
  });

  it('accepts the Web public API key and answers with the configured offering', async () => {
    const offerings = await sdkFor(testAccountId).getOfferings();

    expect(Object.keys(offerings.all).length).toBeGreaterThan(0);
    expect(offerings.all[billing.offeringId], `offering "${billing.offeringId}" must exist in the RevenueCat project`).toBeDefined();
    expect(offerings.all[billing.offeringId].identifier).toBe(billing.offeringId);
  });

  it('offers a lifetime package backed by a Web Billing product with a formatted price', async () => {
    const offering = (await sdkFor(testAccountId).getOfferings()).all[billing.offeringId];
    expect(offering).toBeDefined();

    // getProOffer reads offering.lifetime.webBillingProduct.currentPrice.formattedPrice
    const lifetime = offering.lifetime;
    expect(lifetime, 'the offering needs a lifetime package for Pro').not.toBeNull();
    const product = lifetime!.webBillingProduct;
    expect(product, 'the lifetime package must be backed by a Web Billing product').toBeTruthy();
    expect(product!.productType).toBe(ProductType.NonConsumable);
    expect(typeof product!.currentPrice.formattedPrice).toBe('string');
    expect(product!.currentPrice.formattedPrice).toMatch(HAS_DIGIT);

    // getScanPacks walks availablePackages and reads each package's identifier and product
    expect(Array.isArray(offering.availablePackages)).toBe(true);
    for (const pkg of offering.availablePackages) {
      expect(typeof pkg.identifier).toBe('string');
      if (pkg.webBillingProduct) {
        expect(typeof pkg.webBillingProduct.title).toBe('string');
        expect(Object.values(ProductType)).toContain(pkg.webBillingProduct.productType);
        expect(typeof pkg.webBillingProduct.currentPrice.formattedPrice).toBe('string');
      }
    }
  });

  it('returns customer info with an entitlements map and a SCAN balance for the test account', async () => {
    const sdk = sdkFor(testAccountId);
    const [customerInfo, currencies] = await Promise.all([sdk.getCustomerInfo(), sdk.getVirtualCurrencies()]);

    // getStatus reads customerInfo.entitlements.active[proEntitlementId] and currencies.all.SCAN.balance
    expect(typeof customerInfo.entitlements.active).toBe('object');
    expect(customerInfo.entitlements.active).not.toBeNull();
    const scan = currencies.all[SCAN_CURRENCY];
    expect(scan, `the "${SCAN_CURRENCY}" virtual currency must exist in the RevenueCat project`).toBeDefined();
    expect(Number.isInteger(scan.balance)).toBe(true);
    expect(scan.balance).toBeGreaterThanOrEqual(0);
  });

  it('rejects a key the server does not know with the invalid-credentials error', async () => {
    const error = await sdkFor(testAccountId, WRONG_KEY)
      .getOfferings()
      .then(
        () => null,
        (e: unknown) => e,
      );

    expect(error).toBeInstanceOf(PurchasesError);
    expect((error as PurchasesError).errorCode).toBe(ErrorCode.InvalidCredentialsError);
  });

  it('treats an app user with no purchases as a free customer with no scans, not an error', async () => {
    const sdk = sdkFor(NO_PURCHASES_USER);
    const [customerInfo, currencies] = await Promise.all([sdk.getCustomerInfo(), sdk.getVirtualCurrencies()]);

    expect(Object.keys(customerInfo.entitlements.active)).not.toContain(billing.proEntitlementId);
    expect(currencies.all[SCAN_CURRENCY]?.balance ?? 0).toBe(0);
  });

  it('journey: identifies the test account, fetches offerings, reads entitlement and balance, then switches user', async () => {
    const client = createRevenueCatBillingClient(billing);

    await client.identify(testAccountId);
    const offer = await client.getProOffer();
    expect(offer, 'Pro must be on sale on the web: the lifetime package needs a Web Billing product').not.toBeNull();
    expect(offer!.price).toMatch(HAS_DIGIT);

    const status = await client.getStatus();
    expect(typeof status.isPro).toBe('boolean');
    expect(Number.isInteger(status.scanBalance)).toBe(true);
    expect(status.scanBalance).toBeGreaterThanOrEqual(0);

    // the client and the raw SDK agree about the same customer
    const customerInfo = await Purchases.getSharedInstance().getCustomerInfo();
    expect(status.isPro).toBe(billing.proEntitlementId in customerInfo.entitlements.active);

    const packs = await client.getScanPacks();
    for (const pack of packs) {
      expect(typeof pack.id).toBe('string');
      expect(typeof pack.title).toBe('string');
      expect(pack.price).toMatch(HAS_DIGIT);
    }

    // signing out and in as someone else switches the customer on the same instance
    await client.identify(NO_PURCHASES_USER);
    expect(await client.getStatus()).toEqual({ isPro: false, scanBalance: 0 });
  });
});
