# Entitlement + scan-gating unification: impacts and trade-offs

**Status: analysis only — no decision made, no code changed.** This builds
directly on `ClaudePlans/2026-09-21-research-web-hosting-and-entitlement-tradeoffs.md`
and its same-day addendum. Where that document asked "does hosting choice
make the entitlement question easier or harder," this document goes one
level more concrete: for each real option on two separate axes, what
*actually changes in Android's code and Web's code*. It does not resolve
`NEXT_STEPS.md` item #20's central open question — it's built to make that
decision easier to make well, not to make it for you.

**Working assumption, not re-litigated here**: Claude-vision-only OCR
(Tesseract dropped), free tier = manual entry only on both platforms, per
this session's earlier discussion.

## 1. Two separate axes

1. **Entitlement source-of-truth** — when someone asks "what does this
   user currently have," which system answers: RevenueCat, Stripe, or a
   database you own?
2. **Scan-gating backend unification** — once every scan on both platforms
   becomes "check a credit, call Claude, deduct" (the shape
   `workers/scan-proxy` already implements for Android), should Web and
   Android share one backend service for that operation, or keep two?

These are related but genuinely separable: you can share one scanning
service while still asking two different vendors "what does this user
have" underneath it, and you can unify the entitlement data without
touching how each platform calls Claude. Section 3 works through how they
actually interact once both are decided.

---

## 2. Axis 1 — Entitlement source-of-truth

### Option 1A — RevenueCat everywhere

**What it is.** Don't introduce Stripe at all. RevenueCat now offers a Web
Billing product (already noted as an alternative in `NEXT_STEPS.md` item
#20) — Web adopts RevenueCat's own web SDK/checkout instead of Stripe, so
RevenueCat's entitlement API remains the single, literal source of truth
for both platforms, the same way it already is for Android alone today.

**Android impact.** None. `RevenueCatManager.kt` and the existing
purchase/restore flow are untouched — Android already does exactly this.

**Web impact.** Real, from-scratch work, but simpler than integrating a
second vendor: Web needs a new billing module (structurally analogous to
`RevenueCatManager.kt` but in TypeScript) that initializes RevenueCat's
web SDK, fetches offerings, drives checkout, and reads entitlement status
— replacing what would otherwise have been a Stripe Checkout integration.
`App.tsx` gains its first account/billing-aware state; `api.ts` doesn't
need a new backend billing endpoint at all, since the client talks to
RevenueCat directly for purchase state (only the credit-deduction/scan
gating still needs a backend, see Axis 2).

**What's shared.** Everything — this is the only Option 1 variant where
"what does this user have" is answered by literally the same vendor API
call shape on both platforms. No reconciliation code exists anywhere.

**Risk.** RevenueCat's Web Billing product is newer and less proven than
Stripe for web payments — fewer integrations, thinner documentation,
smaller install base to learn from if something goes wrong. It also
concentrates 100% of both platforms' revenue on one vendor's uptime and
correctness, with no second payment processor as a fallback or comparison
point.

| Pros | Cons |
|---|---|
| Simplest possible design — one vendor, one API shape, zero reconciliation code | Newer product, less battle-tested than Stripe for web payments |
| Fastest to build (no webhook-sync logic to write at all) | No payment-vendor diversification |
| No cross-vendor identity-mapping problem, ever | Doesn't fix `scan-proxy`'s unverified-`app_user_id` gap — that's an Axis 2 problem, independent of which vendor answers the entitlement question |

### Option 1B — RevenueCat stays primary; Stripe collects Web payments, reconciled in

**What it is.** Web integrates Stripe directly (mature, well-documented,
the option `NEXT_STEPS.md` item #20 already leaned toward). A webhook
handler — most naturally living in the future accounts backend — receives
Stripe subscription/payment events and calls RevenueCat's server-side REST
API to mirror that purchase into a RevenueCat customer record keyed to the
same shared-account user ID. RevenueCat stays the one API both platforms'
"what does this user have" checks ultimately ask.

**Android impact.** None. Same as Option 1A — `RevenueCatManager.kt`
unchanged.

**Web impact.** Two new pieces: (1) a standard Stripe Checkout/Billing
integration (client-side redirect + webhook receiver), and (2) a
reconciliation function that translates a Stripe event into a RevenueCat
API call. Web's own "what does this user have" check becomes a
server-to-server call to RevenueCat (there's no RevenueCat *client* SDK
involved on Web in this design, unlike Option 1A) — meaning `api.ts` does
gain a new backend-mediated entitlement-check endpoint.

**What's shared.** The answer to "what does this user have" (RevenueCat),
not the payment-collection mechanism (Stripe for Web, App/Play Store IAP
for Android).

**Risk.** This is where the reconciliation risk both prior documents
already flagged becomes concrete: a delayed or failed Stripe→RevenueCat
sync call means a paying Web user temporarily doesn't show as entitled,
and a duplicate Stripe webhook delivery must not double-grant. This is
real engineering — idempotency keys, retry/backoff, and monitoring for
stuck syncs — not incidental glue code.

| Pros | Cons |
|---|---|
| Keeps Stripe's maturity for Web collections | Real reconciliation code to build and operate correctly (idempotency, retries, monitoring) |
| Still one API answers "what does this user have" everywhere | RevenueCat — an IAP-first product — becomes a hard dependency even for Web users who never touch a mobile store |
| Matches the direction `NEXT_STEPS.md` item #20 already leaned toward | The failure mode (sync lag/failure) directly affects a paying user's access, not just an internal metric |

### Option 1C — One owned system for both

**What it is.** A new database you own becomes the actual source of
truth. RevenueCat (Android) and Stripe (Web) both become thin payment
rails whose webhooks write into one `entitlements`/`credit_balances`
table. Both platforms' clients ask the owned backend "what does this user
have," not RevenueCat's SDK or Stripe's API directly.

**Android impact.** Real and non-trivial — the only option on this axis
that changes Android's code meaningfully. `RevenueCatManager.kt`'s role
narrows to *purchase execution and receipt verification only* (talking to
the App/Play Store and confirming a real purchase happened). Wherever
Android currently asks "how many credits does this user have" (feeding
`CreditBalanceChip` and `PaywallScreen`'s balance display) has to switch
from a RevenueCat SDK call to a call against the new owned backend.
**Purchase restoration gets harder, not easier**: RevenueCat's
`restorePurchases()` today handles Play/App Store receipt verification —
a genuinely hard problem — for free. Under this option, restoring a
purchase still needs RevenueCat (or equivalent store-receipt validation)
for the *verification* step, then a separate write to update the owned
store — RevenueCat isn't removed from the stack, it's demoted from
"entitlement answer" to "purchase verifier," which is a real repositioning
of a component the rest of the Android app is used to trusting fully.

**Web impact.** Simpler than Option 1B's Web side, in one specific way:
Stripe's webhook handler writes directly into the owned database — no
RevenueCat REST call needed at all, one fewer external API in the loop
for Web specifically.

**What's shared.** The data layer itself — one table, one query shape,
both platforms reading the same store regardless of which rail funded the
balance. This is the only option that unifies at the data layer rather
than just at the "which vendor's API do we call" layer, and is the
option that most literally matches `DESIGN_BRIEF.md`'s "one account works
on both platforms" framing.

**Risk.** Same reconciliation risk as Option 1B (two webhook sources,
race/retry/idempotency), *plus* the Android receipt-verification
repositioning above, which is a real architecture change to code that
currently works and is already live with real money flowing through it.

| Pros | Cons |
|---|---|
| Cleanest long-term architecture — one entitlements table, one place to look | Biggest engineering lift of the three options |
| Matches "one account, both platforms" at the data layer, not just the UI | Real Android code change to already-working, already-live billing code |
| No cross-vendor entitlement-API dependency at *query* time (only at *ingestion* time) | Still needs RevenueCat for purchase-receipt verification — doesn't remove it, repositions it, which is easy to underestimate as "simpler" |

---

## 3. Axis 2 — Scan-gating backend unification

### Option 2A — Keep separate

**What it is.** `workers/scan-proxy` stays exactly as it is, serving only
Android. Web gets its own, independently-built cost-gating mechanism.

**Android impact.** None.

**Web impact.** A new endpoint from scratch — most naturally added to the
existing FastAPI backend (or a small new service) — that checks the
user's balance (wherever Axis 1 says that lives), calls Claude vision,
deducts, and returns the result. This duplicates `scan-proxy`'s
charge-before-call discipline in a second codebase and a second language
(Python vs. TypeScript), and its known unverified-identity gap (flagged in
the hosting research, sourced from the local security audit) isn't
automatically inherited — but isn't automatically fixed either; it has to
be independently gotten right in the new code.

| Pros | Cons |
|---|---|
| No shared-infrastructure risk — an outage on one platform never touches the other | Two implementations of the same security-sensitive, real-money-gated logic to build and keep correct |
| Matches how the systems are shaped today — least new coordination | Android's already-audited, already-live `scan-proxy` experience doesn't transfer to Web at all |

### Option 2B — Unify: one shared scan-gating service

**What it is.** `scan-proxy` (or a generalized successor) serves both
platforms. Web's scan-photo flow calls this shared Worker directly instead
of routing through its own backend for that one operation.

**Android impact.** Moderate, not a rewrite: `scan-proxy` needs to stop
assuming RevenueCat is the only possible credit source and gain a
parameterized way to check a balance regardless of which system answers
that question — directly dependent on Axis 1's outcome (see Section 4).

**Web impact.** `web/src/api.ts` gains a second client pointed at the
Worker's own origin (a different host than wherever the rest of the
FastAPI backend lives) specifically for the scan-photo path; the FastAPI
backend loses the Claude-vision-calling responsibility entirely and keeps
only manual-entry + breakdown math — which was always the genuinely
stateless part of the system anyway.

| Pros | Cons |
|---|---|
| One implementation of the hardest, most security-sensitive piece of the system | New cross-platform dependency — a bug/outage in the shared Worker now affects both platforms' paid scanning at once |
| The security-audit-flagged unverified-`app_user_id` gap gets fixed once, for both platforms, instead of needing to be separately remembered on Web | Web's architecture becomes less self-contained — a new origin to manage CORS/monitoring for, on top of whatever hosting choice gets made |
| Android's live operational experience with this exact pattern carries over directly | |

---

## 4. How the two axes interact

Four combinations, worked through concretely rather than assumed
independent:

**(a) Unify neither.** Android keeps RevenueCat + its own `scan-proxy`;
Web builds an independent Stripe integration and an independent
scan-gating endpoint. Fully decoupled — the most total engineering work
(two of nearly everything), but no awkward seams anywhere; each half is
internally coherent on its own.

**(b) Unify scan-gating only (not entitlement).** One shared Worker
handles "check a credit, call Claude, deduct" for both platforms, but
"check a credit" means something different depending on which platform
is calling — a RevenueCat-shaped check for Android-originated requests, a
Stripe/owned-store-shaped check for Web-originated ones. Workable, but the
shared Worker ends up with real branching logic keyed on caller platform,
which is a genuine seam: the "unified" service isn't actually
platform-agnostic, it's platform-*aware*, which caps how much
simplification unifying it actually buys.

**(c) Unify entitlement only (not scan-gating).** One data source (Option
1B or 1C above) answers "what does this user have" for both platforms,
but each platform keeps its own separate mechanism for actually spending
that balance and calling Claude. This is the more natural pairing of the
four: the shared piece is *data* (one balance, one source of truth), while
the *mechanism* that decrements it stays platform-specific — a simpler
contract for two independent services to both honor ("decrement this
shared counter correctly") than combination (b)'s "route to two different
data sources from inside one shared mechanism."

**(d) Unify both.** The cleanest architecture on paper: one owned
entitlements store, one shared scan-gating Worker reading/writing it, both
platforms calling the same service which talks to the same database. No
per-platform branching inside the Worker, one place to fix the identity
gap, one thing to monitor. It's also the largest combined lift of the
four (all of Option 1C's Android re-architecture plus all of Option 2B's
work) — and it makes the two axes' risks additive rather than separable:
a bug in the shared Worker *or* the shared database now affects 100% of
both platforms' revenue-generating traffic at once, where today that
blast radius is split across two independent systems.

**The general pattern**: unifying the *data* (Axis 1) pairs more naturally
with unifying the *mechanism* (Axis 2) than the reverse — (c) is a
cleaner combination than (b) — because a shared store with two independent
access paths is a simpler contract than one shared access path juggling
two different stores.

---

## 5. Recommendation

Framed as input to your decision, not a decision already made.

**Axis 1 — recommend Option 1B** (RevenueCat stays primary, Stripe
collects Web payments and gets reconciled in). This is the pragmatic
middle path: it avoids Option 1A's bet on a newer, less-proven RevenueCat
web product for real revenue, and it avoids Option 1C's Android
re-architecture plus the receipt-verification repositioning risk that's
easy to underestimate. It's also already the direction `NEXT_STEPS.md`
item #20 was leaning before this document existed — this analysis is a
confirmation with the concrete Android/Web impacts spelled out, not a
reversal. Option 1C remains the better long-term architecture if the team
later has appetite for the bigger lift; this is a "not first," not a
permanent no.

**Axis 2 — recommend Option 2B** (unify scan-gating). This is the one
axis where unifying is the *lower*-cost, *higher*-value move: the
security-audit-flagged unverified-identity gap gets fixed once for both
platforms instead of risking it being fixed on Android and forgotten on
Web, and per Section 4, pairing "keep entitlement on RevenueCat (Option
1B)" with "unify scan-gating (Option 2B)" lands on combination **(c)** —
the naturally coherent pairing, not combination (b)'s awkward
platform-branching or (d)'s concentrated blast radius.

**Net recommendation**: combination (c) — unify the data-adjacent
metering/scanning mechanism now (real, contained, immediately fixes a
known security gap), while deferring full entitlement-store unification
(Option 1C) until there's real appetite for re-architecting Android's
already-live billing code. This is meaningfully more unified than doing
nothing, without taking on the biggest lift or the most concentrated risk
available on this board.

---

*See also: `ClaudePlans/2026-09-21-research-web-hosting-and-entitlement-tradeoffs.md`
(hosting options this builds on) and `NEXT_STEPS.md` item #20 (the
roadmap item this feeds).*
