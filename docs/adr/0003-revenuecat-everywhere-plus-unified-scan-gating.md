# Entitlement source-of-truth is RevenueCat everywhere; scan-gating unifies into one shared Worker

Decided 2026-09-23 (wayfinder ticket [#6](https://github.com/gtphdee07/HDTTools/issues/6), part of map [#3](https://github.com/gtphdee07/HDTTools/issues/3)). RevenueCat is the single source of truth for a user's paid status (Scan Credit balance) on **both** Android and Web — Web adopts RevenueCat's own Web Billing SDK instead of integrating Stripe directly, running on RevenueCat's own managed billing engine (Stripe under the hood, RevenueCat-operated). `workers/scan-proxy` (or a generalized successor) becomes the single scan-gating implementation for both platforms, since it only ever needs to check one balance source now — no platform-aware branching on which vendor funded a credit.

This reverses the original research doc's (`ClaudePlans/2026-09-21-entitlement-and-scan-gating-unification-impacts.md`) leaning recommendation of 1B (RevenueCat primary, Stripe reconciled in for Web). Two things changed the calculus: research ([#4](https://github.com/gtphdee07/HDTTools/issues/4)) found RevenueCat's Web Billing has no real product-maturity blocker and that its default engine already runs on Stripe's payment rails underneath, narrowing the "newer, less-proven" risk to RevenueCat's own SDK/dashboard layer rather than payment processing itself; and a hands-on prototype ([#5](https://github.com/gtphdee07/HDTTools/issues/5)) confirmed a real sandboxed checkout (Modal placement) renders correctly, cancels cleanly, and doesn't orphan on repeat purchase. Against that, 1B's reconciliation engineering (idempotency, retries, sync monitoring) is a real, avoidable cost — and this app's already-decided educational-tier, high-downtime-tolerance framing (map #3's Notes) discounts 1A's remaining con (single-vendor entitlement dependency) more than it discounts 1B's guaranteed cost.

## Considered options

- **1B** (RevenueCat primary + Stripe reconciled for Web): rejected — the reconciliation cost 1A avoids entirely.
- **1C** (one owned entitlements database, both platforms as thin payment rails): rejected for now, not permanently — biggest lift of the three, plus a real repositioning of Android's already-live, already-working billing code (RevenueCat demoted from entitlement answer to purchase verifier). Remains the better long-term architecture if there's ever appetite for that lift.
- **2A** (Web builds its own separate scan-gating endpoint): rejected — would duplicate the security-sensitive check-credit/call-Claude/deduct logic in a second codebase, and Android's already-audited `scan-proxy` experience wouldn't transfer.
- **Stripe Billing engine** (bring-your-own Stripe account under RevenueCat's abstraction): rejected for now — no benefit over RevenueCat's managed engine at this app's current volume; switching later is a config-level engine swap, not a re-architecture.

## Consequences

- Web gains a new billing module (TypeScript analog of Android's `RevenueCatManager.kt`) driving RevenueCat's Web SDK directly; no backend billing endpoint needed for purchase state, only for scan-gating.
- `scan-proxy`'s Web impact is simpler than originally modeled: it gains a new caller, not new branching logic, since both platforms now check the identical RevenueCat Virtual Currency (`SCAN`) balance.
- No owned `entitlements`/`credit_balances` table exists anywhere — this narrows the scope of the still-open auth/DB provider ticket ([#7](https://github.com/gtphdee07/HDTTools/issues/7)) to users/sessions/auth-identity only.
- Checkout UI placement (Modal, not Inline) was decided separately on [#5](https://github.com/gtphdee07/HDTTools/issues/5) and isn't restated here.
