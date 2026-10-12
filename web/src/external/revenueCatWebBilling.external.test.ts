import { beforeAll, describe, expect, it } from 'vitest';
import { createClient } from '@supabase/supabase-js';
import { ErrorCode, ProductType, Purchases, PurchasesError } from '@revenuecat/purchases-js';
import { createRevenueCatBillingClient } from '../revenueCatBilling';
import type { BillingConfig } from '../revenueCatBilling';
import { REQUIRED, REVENUECAT, readConfig } from './config';

// External suite (ADR-0008): real calls to RevenueCat Web Billing through the real
// @revenuecat/purchases-js SDK, run only via `npm run test:external`. The
// "[revenuecat-web-billing]" name tag is what the wrapper filters on.
// Reads only. It never buys anything: a sandbox purchase stays the human checklist in #11.
// The test account is the Supabase one from scripts/wizard_web_external_test_user.sh: its
// Supabase user id is the RevenueCat app user id, exactly as the site identifies a customer.

// What revenueCatBilling.ts reads out of RevenueCat's answers.
const PRO_ENTITLEMENT = 'pro';
const SCAN_CURRENCY = 'SCAN';

// A well-formed key the server has never issued (the SDK rejects a malformed one locally).
const WRONG_KEY = 'rcb_external_suite_wrong_key';
// An app user id that never buys anything. RevenueCat creates a customer on first sight, so a
// fixed id keeps that to one customer instead of one per run.
const NO_PURCHASES_USER = 'external-suite-no-purchases';

describe('[revenuecat-web-billing] RevenueCat Web Billing live contract', () => {
  let apiKey: string;
  let offeringId: string;
  let testAccountId: string;

  // The SDK keeps one global instance; configuring again closes the previous one, so every test
  // configures its own and nothing depends on test order.
  const sdkFor = (appUserId: string, key = apiKey) => Purchases.configure({ apiKey: key, appUserId });

  const billingConfig = (): BillingConfig => ({
    apiKey,
    offeringId,
    proEntitlementId: PRO_ENTITLEMENT,
    proPackageId: null,
    scanPackPackageIds: null,
  });

  beforeAll(async () => {
    const cfg = readConfig(import.meta.env as Record<string, string | undefined>, [...REQUIRED, ...REVENUECAT]);
    apiKey = cfg.VITE_REVENUECAT_WEB_PUBLIC_API_KEY;
    offeringId = cfg.VITE_REVENUECAT_WEB_OFFERING_ID;

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
    expect(offerings.all[offeringId], `offering "${offeringId}" must exist in the RevenueCat project`).toBeDefined();
    expect(offerings.all[offeringId].identifier).toBe(offeringId);
  });

  it('offers a lifetime package backed by a Web Billing product with a formatted price', async () => {
    const offering = (await sdkFor(testAccountId).getOfferings()).all[offeringId];

    // getProOffer reads offering.lifetime.webBillingProduct.currentPrice.formattedPrice
    const lifetime = offering.lifetime;
    expect(lifetime, 'the offering needs a lifetime package for Pro').not.toBeNull();
    expect(lifetime!.identifier).toBe('$rc_lifetime');
    const product = lifetime!.webBillingProduct;
    expect(product, 'the lifetime package must be backed by a Web Billing product').toBeTruthy();
    expect(product!.productType).toBe(ProductType.NonConsumable);
    expect(typeof product!.currentPrice.formattedPrice).toBe('string');
    expect(product!.currentPrice.formattedPrice).toMatch(/\d/);

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

    expect(Object.keys(customerInfo.entitlements.active)).not.toContain(PRO_ENTITLEMENT);
    expect(currencies.all[SCAN_CURRENCY]?.balance ?? 0).toBe(0);
  });

  it('journey: identifies the test account, fetches offerings, reads entitlement and balance, then switches user', async () => {
    const client = createRevenueCatBillingClient(billingConfig());

    await client.identify(testAccountId);
    const offer = await client.getProOffer();
    expect(offer, 'Pro must be on sale on the web: the lifetime package needs a Web Billing product').not.toBeNull();
    expect(offer!.price).toMatch(/\d/);

    const status = await client.getStatus();
    expect(typeof status.isPro).toBe('boolean');
    expect(Number.isInteger(status.scanBalance)).toBe(true);
    expect(status.scanBalance).toBeGreaterThanOrEqual(0);

    // the client and the raw SDK agree about the same customer
    const customerInfo = await Purchases.getSharedInstance().getCustomerInfo();
    expect(status.isPro).toBe(PRO_ENTITLEMENT in customerInfo.entitlements.active);

    const packs = await client.getScanPacks();
    for (const pack of packs) {
      expect(typeof pack.id).toBe('string');
      expect(typeof pack.title).toBe('string');
      expect(pack.price).toMatch(/\d/);
    }

    // signing out and in as someone else switches the customer on the same instance
    await client.identify(NO_PURCHASES_USER);
    expect(await client.getStatus()).toEqual({ isPro: false, scanBalance: 0 });
  });
});
