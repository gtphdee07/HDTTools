// Creates the RevenueCat customer "external-suite-pro" (ticket #105) so the owner can grant it
// the `pro` entitlement in the dashboard. The dashboard has no "new customer" button: RevenueCat
// creates a customer the first time an SDK identifies an app user id.
//
// Run from web/: npm run fixture:revenuecat-pro-user
// Uses only the public Web Billing key from .env.local (no secret key, no purchase). Safe to re-run.

import { Purchases } from '@revenuecat/purchases-js';

const APP_USER_ID = 'external-suite-pro';
const apiKey = process.env.VITE_REVENUECAT_WEB_PUBLIC_API_KEY;

if (!apiKey) {
  console.error('VITE_REVENUECAT_WEB_PUBLIC_API_KEY is not set: run this through `npm run fixture:revenuecat-pro-user` from web/.');
  process.exit(1);
}
// The Pro fixture belongs in the sandbox project; never create a customer with a live key.
if (!apiKey.startsWith('rcb_sb_')) {
  console.error('The Web public key is not a sandbox key (rcb_sb_...): refusing to create the fixture customer.');
  process.exit(1);
}

const sdk = Purchases.configure({ apiKey, appUserId: APP_USER_ID });
const info = await sdk.getCustomerInfo();
const active = Object.keys(info.entitlements.active);

console.log(`Customer "${info.originalAppUserId}" exists in RevenueCat.`);
console.log(active.length > 0 ? `Active entitlements: ${active.join(', ')}` : 'No active entitlements yet: grant `pro` in the dashboard (Customers > external-suite-pro > Entitlements > Grant).');
sdk.close();
