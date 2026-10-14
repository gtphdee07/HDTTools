# Web

The React + Vite + TS frontend: the paid-product-in-progress surface that wraps Core's OCR/breakdown math in a guided, multi-step flow. Hosted as a static site on Cloudflare Pages (push-to-deploy).

## Language

**Rig**:
A user-named, reusable pairing of a Truck Tag and Trailer Tag (a `RecentRig`: nickname + truck + trailer + last-used timestamp), saved so a returning user can start a new check without re-entering or re-scanning both tags. Not a Core concept — Core's `compute_breakdown` takes bare truck/trailer/scale data with no notion of a saved, named pairing. This is the product's central noun (the app is "RigCheck"); Android maintains its own equivalent concept independently — see `android/CONTEXT.md` once written.
_Avoid_: vehicle combination, setup.

**Garage**:
The collection of a user's saved Rigs (not a single Rig). Capped per account — a count, not unbounded storage — with the cap itself a pricing-tier detail, not a Garage-concept detail. Account-synced per ADR-0005, superseding the device-local-only scoping in ADR-0004: for a signed-in user the Garage lives in Supabase (`garage_rigs`; the cap is enforced by the database function `add_rig`, currently 5 on the Free plan), identical on every device; a signed-out visitor keeps a browser-local Garage (`recentRigs.ts`), which is not carried into the account on its own: it is hidden while signed in and comes back on sign-out. On the first sign-in to an account on a browser that holds such Rigs, the app offers to import them (`garageImport.ts`). Accepting adds them through the same capped, idempotent add path as any save, one idempotency key per Rig that is kept across a retry of an interrupted import; a Rig the account already holds under that nickname is left as it is, and Rigs the cap leaves out are named to the user. Declining, or finishing, ends the offer for that account on this browser; the browser's own Rigs are never changed either way. One Rig per nickname, in the browser list and the account alike: nicknames are compared ignoring case and surrounding spaces ("Truck A" and " truck a " are the same Rig; `nickname.ts` is the one rule, matching the account's `lower(btrim(nickname))` index), saving under a matching nickname refreshes that Rig instead of adding one, and a nickname is stored and shown trimmed. A full Garage refuses a new Rig with a message; it never silently drops the oldest. The way out of a full Garage is deleting a Rig: the user picks the bin on a Rig in the Rig list, confirms, and the slot is free at once (a failed delete says so and keeps the Rig); a signed-out visitor's browser-local Garage has no delete control.
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

**Scan**:
Defined in `workers/scan-proxy/CONTEXT.md` (the Scan Proxy Worker is the shared "scan service": it spends one **Scan Credit** before reading and refunds it if nothing is read). On Web, a Scan reads a photographed Truck Tag, Trailer Tag or Scale Ticket, including the tow-vehicle-only ticket on the Truck review step. Who may scan: a signed-in **Pro** user with at least one Scan Credit. Anyone else is shown the one thing in their way instead of "Extract Data": sign in (signed out), upgrade to Pro (a Free user, since scans are not sold without Pro), or buy a **Scan pack** (a Pro user with none left); each leads to the Account screen and back to the same check. Typing the numbers in is always open. The Web app sends the account token and a `client_request_id`; charging, refunding and deduplication are the service's. The id stays the same across retries of a photo whose answer never arrived (so a retry is charged once) and is new once the service has answered. A photo the service cannot take (a format it does not read, or over about 3.5 MB) is converted or shrunk in the browser when possible, else refused before anything is sent.
_Avoid_: OCR, extract (the button says "Extract Data" for history's sake; the product noun is **Scan**), "scan credits" in lower case.

**Disclaimer**:
A session-scoped acknowledgment gate shown before results, independently implemented per platform with its own wording — see `android/CONTEXT.md` for the fuller definition and `CONTEXT-MAP.md`'s Relationships.
