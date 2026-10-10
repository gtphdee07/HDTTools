import { describe, expect, it, vi } from 'vitest';
import { createRevenueCatBillingClient, readBillingConfig } from './revenueCatBilling';
import type { BillingConfig, RevenueCatModule } from './revenueCatBilling';

// The production BillingClient against a fake of the RevenueCat SDK: this is
// where the SDK's own shapes (offerings, entitlements, virtual currencies,
// cancel errors) are translated into the app's narrow billing contract.

class FakePurchasesError extends Error {
  errorCode: number;
  constructor(errorCode: number, message = 'sdk error') {
    super(message);
    this.errorCode = errorCode;
  }
}
const USER_CANCELLED = 1;

const CONFIG: BillingConfig = {
  apiKey: 'rcb_test',
  offeringId: 'web',
  proEntitlementId: 'pro',
  proPackageId: null,
};

function makeFakeSdk(overrides: { entitlements?: Record<string, unknown>; balance?: number } = {}) {
  const lifetime = {
    identifier: '$rc_lifetime',
    webBillingProduct: { title: 'RigCheck Pro', currentPrice: { formattedPrice: '$9.99' } },
  };
  const packPackage = {
    identifier: 'scan_pack',
    webBillingProduct: { title: 'Scan pack', currentPrice: { formattedPrice: '$2.99' } },
  };
  const androidOnly = { identifier: 'android_only', webBillingProduct: null };
  const offering = { identifier: 'web', lifetime, availablePackages: [androidOnly, packPackage, lifetime] };

  const purchases = {
    getOfferings: vi.fn(
      async (): Promise<{ all: Record<string, typeof offering>; current: null }> => ({ all: { web: offering }, current: null }),
    ),
    getCustomerInfo: vi.fn(async () => ({ entitlements: { active: overrides.entitlements ?? {} } })),
    getVirtualCurrencies: vi.fn(
      async (): Promise<{ all: Record<string, { balance: number }> }> => ({
        all: { SCAN: { balance: overrides.balance ?? 0 } },
      }),
    ),
    invalidateVirtualCurrenciesCache: vi.fn(),
    purchase: vi.fn(async () => ({ operationSessionId: 'op-1' })),
    changeUser: vi.fn(async () => ({})),
  };
  const configure = vi.fn(() => purchases);
  const sdk = {
    Purchases: { configure },
    PurchasesError: FakePurchasesError,
    ErrorCode: { UserCancelledError: USER_CANCELLED },
  } as unknown as RevenueCatModule;
  return { sdk, purchases, configure, lifetime };
}

const clientFor = (fake: ReturnType<typeof makeFakeSdk>, config: BillingConfig = CONFIG) =>
  createRevenueCatBillingClient(config, async () => fake.sdk);

describe('RevenueCat billing client', () => {
  it('configures the SDK once with the first account, then switches users on later sign-ins', async () => {
    const fake = makeFakeSdk();
    const client = clientFor(fake);
    await client.identify('user-1');
    await client.identify('user-1');
    await client.identify('user-2');
    expect(fake.configure).toHaveBeenCalledTimes(1);
    expect(fake.configure).toHaveBeenCalledWith({ apiKey: 'rcb_test', appUserId: 'user-1' });
    expect(fake.purchases.changeUser).toHaveBeenCalledTimes(1);
    expect(fake.purchases.changeUser).toHaveBeenCalledWith('user-2');
  });

  it('offers the lifetime package of the configured offering as Pro', async () => {
    const client = clientFor(makeFakeSdk());
    await client.identify('user-1');
    expect(await client.getProOffer()).toEqual({ price: '$9.99' });
  });

  it('picks the Pro package by id when one is configured', async () => {
    const client = clientFor(makeFakeSdk(), { ...CONFIG, proPackageId: 'scan_pack' });
    await client.identify('user-1');
    expect(await client.getProOffer()).toEqual({ price: '$2.99' });
  });

  it('offers nothing when the offering has no web-purchasable Pro package', async () => {
    const fake = makeFakeSdk();
    fake.purchases.getOfferings.mockResolvedValue({ all: {}, current: null });
    const client = clientFor(fake);
    await client.identify('user-1');
    expect(await client.getProOffer()).toBeNull();
  });

  it('reports Pro from the active entitlement and the SCAN balance, refetched fresh', async () => {
    const fake = makeFakeSdk({ entitlements: { pro: {} }, balance: 7 });
    const client = clientFor(fake);
    await client.identify('user-1');
    expect(await client.getStatus()).toEqual({ isPro: true, scanBalance: 7 });
    expect(fake.purchases.invalidateVirtualCurrenciesCache).toHaveBeenCalled();
  });

  it('reports Free with zero scans for a customer with no purchases', async () => {
    const fake = makeFakeSdk();
    fake.purchases.getVirtualCurrencies.mockResolvedValue({ all: {} });
    const client = clientFor(fake);
    await client.identify('user-1');
    expect(await client.getStatus()).toEqual({ isPro: false, scanBalance: 0 });
  });

  it('purchases the Pro package in the modal placement (no inline target)', async () => {
    const fake = makeFakeSdk();
    const client = clientFor(fake);
    await client.identify('user-1');
    await client.getProOffer();
    expect(await client.purchasePro()).toBe('purchased');
    expect(fake.purchases.purchase).toHaveBeenCalledWith({ rcPackage: fake.lifetime });
  });

  it('treats the SDK cancel error as a cancelled outcome, not a failure', async () => {
    const fake = makeFakeSdk();
    fake.purchases.purchase.mockRejectedValue(new FakePurchasesError(USER_CANCELLED));
    const client = clientFor(fake);
    await client.identify('user-1');
    await client.getProOffer();
    expect(await client.purchasePro()).toBe('cancelled');
  });

  it('rethrows any other purchase error', async () => {
    const fake = makeFakeSdk();
    fake.purchases.purchase.mockRejectedValue(new FakePurchasesError(99, 'card declined'));
    const client = clientFor(fake);
    await client.identify('user-1');
    await client.getProOffer();
    await expect(client.purchasePro()).rejects.toThrow('card declined');
  });

  it('refuses to purchase before an offer has been loaded', async () => {
    const client = clientFor(makeFakeSdk());
    await client.identify('user-1');
    await expect(client.purchasePro()).rejects.toThrow(/not available/i);
  });
});

describe('readBillingConfig', () => {
  it('needs both the public API key and the offering id', () => {
    expect(readBillingConfig({})).toBeNull();
    expect(readBillingConfig({ VITE_REVENUECAT_WEB_PUBLIC_API_KEY: 'k' })).toBeNull();
    expect(readBillingConfig({ VITE_REVENUECAT_WEB_OFFERING_ID: 'o' })).toBeNull();
  });

  it('defaults the Pro entitlement to "pro" and lets the package id be unset', () => {
    expect(
      readBillingConfig({ VITE_REVENUECAT_WEB_PUBLIC_API_KEY: 'k', VITE_REVENUECAT_WEB_OFFERING_ID: 'o' }),
    ).toEqual({ apiKey: 'k', offeringId: 'o', proEntitlementId: 'pro', proPackageId: null });
  });

  it('reads the optional entitlement and package overrides', () => {
    expect(
      readBillingConfig({
        VITE_REVENUECAT_WEB_PUBLIC_API_KEY: 'k',
        VITE_REVENUECAT_WEB_OFFERING_ID: 'o',
        VITE_REVENUECAT_PRO_ENTITLEMENT_ID: 'rigcheck_pro',
        VITE_REVENUECAT_PRO_PACKAGE_ID: 'lifetime',
      }),
    ).toEqual({ apiKey: 'k', offeringId: 'o', proEntitlementId: 'rigcheck_pro', proPackageId: 'lifetime' });
  });
});
