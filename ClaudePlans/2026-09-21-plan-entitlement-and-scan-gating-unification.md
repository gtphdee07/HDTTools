# Entitlement + scan-gating unification: impacts and trade-offs

## Context

Two research documents already exist and both point at the same unresolved
question from different angles:

1. `ClaudePlans/2026-09-21-research-web-hosting-and-entitlement-tradeoffs.md`
   evaluated 5 web-hosting options and, for each, assessed whether it makes
   the entitlement source-of-truth question (RevenueCat-primary vs.
   Stripe-primary vs. one owned system) easier or harder to answer well —
   without resolving it, since hosting choice was found to be largely
   neutral on that question (Options A/B/C) or mildly biasing (D/E).
2. Its same-day addendum worked through what changes if Tesseract is
   dropped and Claude-vision becomes the only OCR backend on both
   platforms (free tier = manual entry only). That discussion surfaced a
   **second, related but separate unification question**: once every scan
   on both platforms becomes "check a credit, call Claude, deduct" (the
   same shape `workers/scan-proxy` already implements for Android), should
   Web and Android share **one scan-gating backend service**, or keep two
   separate implementations?

Both questions are about whether to unify a piece of backend
infrastructure across platforms, and both are still genuinely open —
`NEXT_STEPS.md` item #20 already names the entitlement question as "the
single biggest unresolved risk" without answering it. What's missing is a
document that goes one level more concrete than either prior write-up:
walking through **what actually changes in Android's code and Web's code,
separately**, under each real option for each axis — so the decision can
be made by someone (or some future engineering effort) who hasn't just
been in this conversation.

**Working assumption for this document** (per this session's discussion,
not re-litigated here): Claude-vision-only OCR, Tesseract dropped, free
tier = manual entry only. This is taken as settled context, not one of the
variables being compared.

## Goal

Produce one document, building directly on the two above, that:

1. Treats **entitlement source-of-truth** and **scan-gating backend
   unification** as two distinct axes (per this session's explicit scope
   decision — they're related but separable: you can share one scanning
   service without unifying subscription/entitlement storage, and vice
   versa).
2. For each axis, lays out the real options and, for each option, states
   concretely what changes in **Android's code** and what changes in
   **Web's code** — not just abstract pros/cons, but which files/systems
   on each platform are affected and how.
3. Shows how the two axes interact (does choosing "unify scan-gating"
   make "unify entitlement" easier, harder, or unrelated? — work through
   the real combinations rather than asserting independence).
4. Ends with a specific recommendation on both axes, explicitly framed as
   input to the user's decision, matching the hosting research's style.

## Grounding already in hand (no new research needed — this is synthesis)

This is a synthesis task, not a research task — everything needed was
already gathered this session or in prior sessions:

- `NEXT_STEPS.md` item #20 — full scope of the accounts/paywall work, the
  entitlement question's framing, and the decided facts (shared accounts,
  email+social login, Android-first).
- `DESIGN_BRIEF.md` — which screens on each platform touch
  accounts/paywall (Sign Up/Log In/Account/Paywall on both platforms),
  relevant because entitlement-source-of-truth choice affects what each
  of those screens actually reads from/writes to.
- The hosting research + addendum (above) — the 5 hosting options, the
  entitlement angle already argued per option, and the scan-gating
  unification question raised in the addendum.
- `ARCHIVE_MONETIZATION.md` — real build narrative for how Android's
  existing RevenueCat + `scan-proxy` billing was actually built, useful
  for grounding what "Android's code" concretely means for this analysis.
- Already-confirmed source facts from this session: `workers/scan-proxy`'s
  `request.ts`/`scan.ts`/`revenuecat.ts` shape (charge-before-call,
  RevenueCat Virtual Currency API as the only ledger, unverified
  `app_user_id`); Android's `ScanApiClient.kt`/`RevenueCatManager.kt`
  (no cookie jar, plain `app_user_id` field); Web's `api.ts` (hardcoded
  `localhost:8000`) and `App.tsx` (no account/settings screen today).

## Steps

1. **Axis 1 — Entitlement source-of-truth.** Write up the three concrete
   options (RevenueCat-primary + Stripe reconciled in; Stripe/unified-
   store-primary; one owned system for both) with, for each: what Android
   has to build/change (e.g., does `RevenueCatManager.kt` stay as the only
   client-side billing code, or does it need to also talk to a new shared
   backend?), what Web has to build (its Stripe integration + how it reads
   "what does this user have"), what's genuinely shared vs.
   platform-specific, the real reconciliation/race risk already flagged in
   the hosting research, and a pros/cons table.
2. **Axis 2 — Scan-gating backend unification.** Write up the two concrete
   options (keep separate: Android keeps `scan-proxy`, Web gets its own
   new cost-gating mechanism; unify: one shared scan-gating service both
   platforms call, most concretely a generalized `scan-proxy`) with, for
   each: Android impact (does `scan-proxy` change at all, or does Web just
   start calling the existing one?), Web impact (new client code needed to
   call a Worker instead of its own FastAPI backend for the scan path
   specifically), and a pros/cons table.
3. **Interaction section.** Work through the 4 combinations (unify both /
   unify neither / unify only entitlement / unify only scan-gating) and
   state plainly which combinations are coherent and which create
   awkward seams (e.g., a shared scan-gating service that deducts from an
   entitlement store it doesn't otherwise own).
4. **Recommendation section.** A specific recommended point in this
   2-axis space, with reasoning, explicitly framed as input rather than a
   final decision — matching the hosting research's own recommendation
   style and tone.
5. Save the finished document to
   `ClaudePlans/2026-09-21-entitlement-and-scan-gating-unification-impacts.md`
   and add one cross-link line at the bottom of the existing hosting
   research file pointing to it (mirroring how that file's own addendum
   already forward-references this document).

## Definition of Done

- The document exists at the path above and covers both axes with real,
  named per-platform impacts (not generic "pros/cons" without grounding
  in what actually changes in the code) for every option on both axes.
- The interaction section addresses all 4 combinations, not just the two
  "obvious" ones.
- A clear recommendation is given for both axes together, stated as input
  to the decision, not a directive.
- The hosting research file has a one-line pointer to this new document
  for discoverability.

## Verification

- Re-read the finished document and confirm every option on both axes has
  a concrete Android-side and Web-side impact statement, not just
  abstract trade-off language.
- Confirm the interaction section's 4 combinations are each addressed.
- Confirm the cross-link was added to the hosting research file.
