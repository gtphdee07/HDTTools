# Web

The React + Vite + TS frontend: the paid-product-in-progress surface that wraps Core's OCR/breakdown math in a guided, multi-step flow. Hosted as a static site on Cloudflare Pages (push-to-deploy).

## Language

**Rig**:
A user-named, reusable pairing of a Truck Tag and Trailer Tag (a `RecentRig`: nickname + truck + trailer + last-used timestamp), saved so a returning user can start a new check without re-entering or re-scanning both tags. Not a Core concept — Core's `compute_breakdown` takes bare truck/trailer/scale data with no notion of a saved, named pairing. This is the product's central noun (the app is "RigCheck"); Android maintains its own equivalent concept independently — see `android/CONTEXT.md` once written.
_Avoid_: vehicle combination, setup.

**Garage**:
The collection of a user's saved Rigs (not a single Rig). Capped per account — a count, not unbounded storage — with the cap itself a pricing-tier detail, not a Garage-concept detail. Account-synced per ADR-0005, superseding the device-local-only scoping in ADR-0004: for a signed-in user the Garage lives in Supabase (`garage_rigs`; the cap is enforced by the database function `add_rig`, currently 5 on the Free plan), identical on every device; a signed-out visitor keeps a browser-local Garage (`recentRigs.ts`), which is not carried into the account on sign-in. A full Garage refuses a new Rig with a message; it never silently drops the oldest.
_Avoid_: using "Garage" and "Rig" interchangeably — Garage is the set, Rig is one member of it.

**Wizard**:
The guided, five-step flow that produces one Breakdown: select a Rig (step 0), enter/scan the Truck Tag (1), Trailer Tag (2), Scale Ticket (3), then view Results (4). Each step has its own sub-state (`upload` / `processing` / `review` / `error` / `finalizing`) tracking where the user is within that step's own data-entry flow.

**History**:
The list of a user's **past, completed** checks (`HistoryEntry`: id, date, rig nickname, Verdict) — a record of *results*, not to be confused with a Rig, which is a *reusable input* (a saved truck+trailer pairing) rather than a past outcome.

**Dashboard**:
The app's home screen, showing recent activity and entry points into the Wizard and History.

**Pro**:
The one-time, lifetime paid plan, as opposed to Free. It is shared across platforms through the account (ADR-0003/0006) and is backed by the `pro` entitlement *object* in RevenueCat; that is RevenueCat's own record, not the reserved glossary term **Entitlement** (the question of which system is the source of truth for paid status — see `workers/scan-proxy/CONTEXT.md`). A signed-in Free user buys it from the paywall on the Account screen, in RevenueCat's modal checkout; the Web app only reads the Pro status and the **Scan Credit** balance (the `SCAN` virtual currency) back from RevenueCat, it never grants either. RevenueCat grants the starter scan bundle server-side, so after a purchase the Account screen rechecks the balance over a short, bounded window ("Updating your scans...") and, if it never changes, says scans may take a minute; the user stays on Pro throughout. The paywall states that results are not certified DOT weights; that is separate from the **Disclaimer** gate.
_Avoid_: Entitlement, Premium, subscription (it is a one-time purchase), "Scan credits" in lower case (the term is **Scan Credit**; the Account screen says "Scan Credit balance").

**Scan pack**:
A consumable top-up of the **Scan Credit** balance (ADR-0006), bought from the "Buy more scans" card on the Account screen by a **Pro** user (a Free user is offered Pro, not packs, so scans are not sold without Pro), in the same RevenueCat modal checkout as Pro. A pack adds scans only: it never changes the plan, so the Garage and History caps are untouched. Which packs are on sale, their titles and prices, and how many scans each grants are RevenueCat's configuration; the Web app lists the offering's web-purchasable consumable packages other than Pro (or just those named in `VITE_REVENUECAT_SCAN_PACK_PACKAGE_IDS`) and only ever reads the new balance back, using the same bounded "Updating your scans..." recheck as the Pro starter bundle. No packs configured means no card.
_Avoid_: credit pack, top-up, bundle (the **Pro** "starter bundle" is a different thing, granted with Pro).

**Disclaimer**:
A session-scoped acknowledgment gate shown before results, independently implemented per platform with its own wording — see `android/CONTEXT.md` for the fuller definition and `CONTEXT-MAP.md`'s Relationships.
