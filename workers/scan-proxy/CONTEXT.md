# Scan Proxy

The Cloudflare Worker that gates paid Claude-vision scans behind a purchase, and performs the scan on the client's behalf so the Anthropic API key never ships in the app.

## Language

**Scan**:
One request to extract fields from a photographed document (Truck Tag, Trailer Tag, or Scale Ticket — see Core's `CONTEXT.md`) via Claude vision, gated by Scan Credit.

**Scan Credit**:
The unit of paid usage, implemented as a RevenueCat "virtual currency" (currency code `SCAN`). A user's Scan Credit balance is spent before a Scan runs and refunded if the Scan fails to deliver a result.

**Spend / Refund**:
The two credit-balance operations Scan Proxy performs against RevenueCat directly (server-side, not through the client SDK's own purchase flow): Spend happens before the costly Claude call; Refund happens only if extraction then fails, so a user is never billed for a Scan that didn't deliver.

**Idempotency Key**:
A client-supplied id, stable across retries of the same logical Scan attempt, that makes Spend/Refund safe to retry without double-charging or double-refunding after a lost or timed-out response.

**Entitlement** (reserved term — narrower uses should say "Scan Credit balance," not "entitlement"):
The unresolved, cross-platform question of which system is the **source of truth** for a user's paid status (RevenueCat alone, RevenueCat-for-Android-with-Stripe-reconciled-for-Web, or one unified system) — not yet decided, tracked in `NEXT_STEPS.md` item #20. Don't use "entitlement" for the per-request "does this user have enough Scan Credit balance" check performed inside `runScan` — that's a Spend, and a `422`/`insufficient_credits` response from it is a balance check, not an entitlement decision in this larger sense.
