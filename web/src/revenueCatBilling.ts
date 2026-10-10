import type { BillingClient, BillingStatus, ProOffer, PurchaseOutcome } from './billing';

// RevenueCat's SDK is large, so it is loaded only when an account is first
// identified - the free, account-less calculator never downloads it.
type SdkModule = typeof import('@revenuecat/purchases-js');
export type RevenueCatModule = Pick<SdkModule, 'Purchases' | 'PurchasesError' | 'ErrorCode'>;
type Sdk = ReturnType<SdkModule['Purchases']['configure']>;
type SdkPackage = Awaited<ReturnType<Sdk['getOfferings']>>['all'][string]['availablePackages'][number];

// The "SCAN" virtual currency code, matching Android and the scan-proxy Worker.
const SCAN_CURRENCY_CODE = 'SCAN';
const DEFAULT_PRO_ENTITLEMENT_ID = 'pro';

export interface BillingConfig {
  apiKey: string;
  offeringId: string;
  proEntitlementId: string;
  // null means "the offering's lifetime package"
  proPackageId: string | null;
}

// Null when the public API key or offering id is missing: the site then runs
// without purchases, like a build without Supabase runs without accounts.
export function readBillingConfig(env: Record<string, string | undefined>): BillingConfig | null {
  const apiKey = env.VITE_REVENUECAT_WEB_PUBLIC_API_KEY;
  const offeringId = env.VITE_REVENUECAT_WEB_OFFERING_ID;
  if (!apiKey || !offeringId) return null;
  return {
    apiKey,
    offeringId,
    proEntitlementId: env.VITE_REVENUECAT_PRO_ENTITLEMENT_ID || DEFAULT_PRO_ENTITLEMENT_ID,
    proPackageId: env.VITE_REVENUECAT_PRO_PACKAGE_ID || null,
  };
}

export function createRevenueCatBillingClient(
  config: BillingConfig,
  loadSdk: () => Promise<RevenueCatModule> = () => import('@revenuecat/purchases-js'),
): BillingClient {
  let module: RevenueCatModule | null = null;
  let sdk: Sdk | null = null;
  let currentUserId: string | null = null;
  let proPackage: SdkPackage | null = null;

  const requireSdk = (): Sdk => {
    if (!sdk) throw new Error('Purchases are not available until an account is signed in.');
    return sdk;
  };

  return {
    async identify(accountId) {
      if (accountId === currentUserId) return;
      if (!sdk) {
        module = await loadSdk();
        // Configuring more than one Purchases instance is unsupported, so this
        // happens once; later accounts switch the existing instance's user.
        sdk = module.Purchases.configure({ apiKey: config.apiKey, appUserId: accountId });
      } else {
        await sdk.changeUser(accountId);
      }
      currentUserId = accountId;
      proPackage = null;
    },

    async getProOffer(): Promise<ProOffer | null> {
      const offerings = await requireSdk().getOfferings();
      const offering = offerings.all[config.offeringId] ?? offerings.current;
      const pkg = config.proPackageId
        ? offering?.availablePackages.find((p) => p.identifier === config.proPackageId)
        : offering?.lifetime;
      // Packages not backed by Web Billing (for example Android's) cannot be bought here.
      if (!pkg?.webBillingProduct) {
        proPackage = null;
        return null;
      }
      proPackage = pkg;
      return { price: pkg.webBillingProduct.currentPrice.formattedPrice };
    },

    async getStatus(): Promise<BillingStatus> {
      const purchases = requireSdk();
      // Scans are charged by the Worker through RevenueCat's REST API, which the
      // SDK's cache never hears about, so always fetch a fresh balance.
      purchases.invalidateVirtualCurrenciesCache();
      const [customerInfo, currencies] = await Promise.all([purchases.getCustomerInfo(), purchases.getVirtualCurrencies()]);
      return {
        isPro: config.proEntitlementId in customerInfo.entitlements.active,
        scanBalance: currencies.all[SCAN_CURRENCY_CODE]?.balance ?? 0,
      };
    },

    async purchasePro(): Promise<PurchaseOutcome> {
      const purchases = requireSdk();
      if (!proPackage || !module) throw new Error('Pro is not available to buy right now.');
      try {
        // Modal placement: no htmlTarget. The inline placement does not render
        // and cannot be cancelled (purchases-js #1095).
        await purchases.purchase({ rcPackage: proPackage });
        return 'purchased';
      } catch (err) {
        if (err instanceof module.PurchasesError && err.errorCode === module.ErrorCode.UserCancelledError) return 'cancelled';
        throw err;
      }
    },
  };
}
