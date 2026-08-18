# RigCheck Android — Design Brief

Handoff doc originally written 2026-08-14, before any Android design
work happened. Updated 2026-08-15 to reconcile with reality: Claude
Design has since produced full mockups (in a local, gitignored
`android/design/` — see "Current status" at the bottom) and the Android
business model was decided in the meantime. This version brings the
brief back in sync with `NEXT_STEPS.md`, which is the source of truth
for the business/backend reasoning — this doc doesn't re-derive it, just
stays consistent with it.

**Updated again 2026-08-17** — real mockups exist now (the earlier
version above was written before any Design work had actually happened).
This pass reconciles a handful of deliberate deviations Design flagged in
its own handoff — see "Current status" for exactly what changed and why.

## What RigCheck is

An experimental RV/trailer tow-weight safety checker: get the numbers
off a truck's compliance label, a trailer's compliance label, and a CAT
Scale weigh ticket — by photo (web, Streamlit, and Android's optional
paid scan feature) or by typing them in directly (Android's free
default) — and it computes an axle-by-axle pass/fail breakdown against
each axle's rated limit. It's explicitly an experimental learning
project, not a certified safety tool — every version shows a blocking
"not for safety decisions" disclaimer before results (see below).

**Live reference — the actual running app**: https://hdttools-ynfeq8py78ghmeyulo2grr.streamlit.app
(Streamlit version; same core flow and field set. It doesn't have
Android's scan/manual choice or purchase flow, but is still the fastest
way to see the real content, copy tone, and results screen.)

The web app (React, not currently hosted) followed the same flow and was
itself built from a prior pixel-perfect design handoff — precedent for
doing the same here.

## How Android differs: manual entry by default, optional paid scan

**Manual entry is the free, fully offline default** — no OCR, no
network, no account needed. This was the original Phase C decision and
it still holds for the default path.

**On top of that, there's now an optional paid "scan" feature**: instead
of typing values in, the user can photograph the label/ticket and have
Claude vision extract the fields (same idea as the web/Streamlit OCR
step, just cloud-vision instead of on-device Tesseract). This is gated
by credits — see `NEXT_STEPS.md`'s "Android monetization" section for
the full reasoning (lifetime purchase + consumable credit packs;
subscription was considered and explicitly rejected). Backend:
`workers/scan-proxy/` (Cloudflare Worker, already in this repo, not yet
deployed) exposes `POST /v1/scan` — charges one RevenueCat credit,
calls Claude vision, refunds the credit if extraction fails. See
`workers/scan-proxy/README.md` for the exact request/response contract.

Two things worth knowing about the scan path specifically:
- **A successful scan still lands on the same editable review form**
  manual entry uses — mirrors the web/Streamlit "extract, then let the
  user fix mistakes" pattern. Scanning isn't a shortcut past review.
- **`standalone_weight_lb` (truck) and `axle_count` (trailer) are always
  manual**, scan or no scan — neither value appears on a label/ticket,
  so there's nothing for Claude vision to extract. The Worker's field
  schema (`docTypes.ts`) doesn't include them at all, by design.
- **Credit balance and purchases go through the RevenueCat SDK directly
  on-device**, not through the Worker — the Worker only handles the
  scan-and-charge call itself, there's no balance-check endpoint to poll.

## Brand / design tokens (from the existing web app)

Source of truth: `web/src/design-system/tokens.css`. Native Android has
its own conventions (Material, system fonts, density units) so treat
these as the palette/type pairing to adapt, not literal CSS to port.

**Colors**
| Token | Hex | Use |
|---|---|---|
| Sunset orange | `#f0942f` | Primary accent / CTA |
| Trail green | `#4d7a3a` | Secondary accent, "success" / pass |
| Dusk mauve | `#8d7fa0` | Tertiary accent |
| Sunset rose | `#c17f8f` | Quaternary accent |
| Charcoal | `#2a2a28` | Primary text |
| Charcoal soft | `#4a4844` | Secondary text |
| Cream | `#f6efe4` | Page background |
| White | `#ffffff` | Card/surface background |
| Danger red | `#b5473a` | "Over limit" / fail state |

**Type**: "Quicksand" (headings/display, weight 600–700), "Karla" (body
text), "Alex Brush" (script — used sparingly/decoratively, e.g. a
wordmark, not body content).

**Spacing scale**: 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64px (small to large).
**Corner radius**: 8px (small controls), 14px (cards), 22px (large
panels), pill/999px (buttons, badges).

The overall feel (from the web app's copy and layout): warm, friendly,
a little playful ("Wandering Trails, Wagging Tails" — this is an RV/dog
household's project) rather than clinical or heavily technical, despite
being a numbers-and-safety tool.

## Screens needed

1. **Rig picker** — pick one of up to 5 recently-used rigs (stored
   on-device only, no server — see "Data & persistence" below), each
   showing a nickname + truck/trailer manufacturer if known; or start a
   new rig by typing a nickname (e.g. "Big Blue").
   - Picking an existing rig should skip straight to the Scale Ticket
     screen (step 3) — truck/trailer specs don't change trip to trip,
     only the scale reading does. This is already how the web/Streamlit
     versions behave.
2. **Truck tag entry** — a choice between **"Scan Photo"** (paid, costs
   one credit, requires camera capture) and **"Enter Manually"** (free),
   both leading to the same reference image (annotated Ford-style
   compliance label) + editable fields:
   - Description (text, e.g. "Ford F-350" — **renamed from
     "Manufacturer" per the 2026-08-17 mockup**, same underlying field,
     broader example content: full make/model, not just the manufacturer
     name)
   - Name (text, e.g. "Addie" — **new field added by the mockup, not in
     the original field list**: a nickname for *this specific vehicle*,
     distinct from the rig-level nickname on screen 1. Display-only, like
     Description — not consumed by the breakdown math)
   - GVWR, lb (number)
   - Front GAWR, lb (number)
   - Rear GAWR, lb (number)
   - Stand-alone weight, lb (number, **optional, always manual even
     after a scan** — used to estimate tongue weight; label should make
     clear it's optional)
3. **Trailer tag entry** — same scan-or-manual choice, reference image
   (annotated Brinkley-RV-style compliance label) + fields:
   - Description (text — same rename as truck tag above)
   - Name (text — same new per-vehicle-nickname field as truck tag above)
   - GVWR, lb (number)
   - GAWR per axle, lb (number)
   - Axle count (number, **optional, always manual even after a scan,
     defaults to 2** — make the default visible/explained, not just an
     empty field)
   - Unloaded weight / UVW, lb (number)
4. **Scale ticket entry** — same scan-or-manual choice, reference image
   (annotated CAT Scale ticket) + fields:
   - Scale location (text)
   - Steer axle, lb (number)
   - Drive axle, lb (number)
   - Trailer axle(s), lb (number)
   - Gross weight, lb (number)
5. **Purchase / paywall** — lifetime unlock (includes a pre-set number
   of scan credits) + consumable credit-pack purchases once those run
   out. The 2026-08-17 mockup is a bespoke, brand-matched layout (not a
   generic paywall) — build this as a custom Compose screen rather than
   RevenueCat's prebuilt Paywall UI, which wouldn't match. Pricing itself
   is deliberately still undecided (see `NEXT_STEPS.md`) — the mockup
   shows "Price TBD" placeholders; don't hard-code dollar amounts
   anywhere they'd be annoying to change later.
6. **Credit balance indicator** — not a dedicated screen; a persistent,
   contextual element near each "Scan Photo" entry point (e.g. "12 scans
   left"), reading from RevenueCat directly. Already covered by the
   existing mockups.
7. **Disclaimer** — blocking, shown once per app session before the
   first results screen. **Wording decided 2026-08-17**: Android uses its
   own text, deliberately *not* identical to web/Streamlit's — the
   original wording's "OCR-read photos" phrasing doesn't fit Android's
   manual-entry-first default (most users never touch a scan). Exact
   required text:

   > **Experimental Tool — Not for Safety Decisions**
   >
   > RigCheck is an experimental project built to learn app development,
   > not a certified or professional weight-safety tool. You type in
   > numbers straight off your own tag and ticket photos, and the math
   > that follows is simplified — any step of that chain can be wrong.
   >
   > Do not use this tool to decide whether your rig is safe to tow.
   > Always verify actual weights and ratings using a certified scale
   > and your vehicle's official documentation, and consult a qualified
   > professional if you're unsure. You use this tool, and any decisions
   > you make based on it, entirely at your own risk and responsibility.
8. **Results** — six axle-by-axle comparisons, each needing: label,
   actual value, rated limit, a pass/fail visual treatment (green/red,
   not just color — we already hit a bug on Streamlit where an
   over-limit item rendered green because the color logic didn't
   actually key off pass/fail, so make the fail state visually
   unambiguous beyond color alone, e.g. an icon), a percent-of-limit
   bar, and an optional explanatory note. Rows:
   - Front Axle (Steer)
   - Rear Axle (Drive)
   - Tow Vehicle Total (GVWR)
   - Trailer Axle(s)
   - Trailer Total (GVWR) — see note below, this row's math has a
     specific default worth getting right
   - Combined Rig Weight

   Plus an overall verdict banner above the breakdown: "Safe to Tow"
   (green) or "Not Safe to Tow" (red), with a one-line explanation.

   **"Trailer Total (GVWR)" default, decided 2026-08-14**: when
   stand-alone weight was left blank, don't just show the trailer axle
   reading unadjusted — that implicitly assumes 0% tongue weight, which
   is wrong in the unsafe direction (can make an overweight trailer look
   compliant). Instead, estimate total trailer weight as
   `trailer_axle_lb / 0.8` (a named constant,
   `DEFAULT_AXLE_TO_TOTAL_RATIO` — pin/tongue weight is commonly ~15–25%
   of trailer weight, so the axle reading alone is assumed to be ~80% of
   the total). Note text should say plainly that this is an estimate,
   e.g. "Estimated total weight — assumes the axle reading is 80% of
   actual trailer weight; enter your truck's stand-alone weight for an
   exact figure." When stand-alone weight *is* provided, the exact
   tongue-weight calculation is used instead (unaffected by this
   default). This is already the assumption baked into the existing
   Android mockups — it's `web`/`streamlit_app`'s implementation
   (`src/hdttools/api/breakdown.py`) that still needs to catch up, per
   `NEXT_STEPS.md`'s current top priority — so build Android against
   this (correct) behavior directly rather than the web app's
   not-yet-fixed one.

## The annotated reference images

For each of the three entry screens (truck tag, trailer tag, scale
ticket), design a reference image: a photo or clean illustration of a
real label/ticket with callouts pointing at exactly the value each input
field is asking for. Goal: someone who has never seen a compliance label
before can look at the reference image, find the same spot on their own
tag, and type the number in confidently. Relevant on the manual-entry
path regardless of whether scanning is available — scanning is
optional/paid, so manual entry needs to stand on its own.

**Two different patterns, per the 2026-08-17 mockup** (not one pattern
for all three, as originally envisioned):
- **Truck tag and trailer tag**: an interactive hover-to-zoom pattern —
  hovering a field smoothly zooms the reference photo into that field's
  exact spot and drops a highlight ring, no static numbered legend.
  **Has no direct mobile equivalent** — the mockup's own README flags
  this and recommends either tap-and-hold, or a persistent lower-third
  crop that updates on focus, to carry the same "confirm you're reading
  the right spot" intent to touch. **Not yet decided which — pick one
  when building screens 2/3.**
- **Scale ticket**: a simpler static pattern — numbered circle badges
  overlaid directly on the ticket photo, matched to a numbered legend row
  above the fields ("1 Scale location · 2 Steer · 3 Drive · 4 Trailer ·
  5 Gross"). Ports directly to Compose (numbered badges positioned over
  an `Image`) — no interaction design needed here.

Starting material — real photos, from the design export
(`android/design/`'s extracted `reference-images/` folder, filenames
already corrected — unlike `ExampleDocs/`'s swapped names, see below):
- `AddieTag-truck.jpg` — truck compliance label (Ford)
- `GooseTag-trailer.jpg` — trailer compliance label (Brinkley RV)
- `CatScale-Ticket.jpg` — CAT Scale weigh ticket

These are re-exported, corrected copies — not the original
`ExampleDocs/AddieTag.jpg` / `ExampleDocs/GooseTag.jpg`, whose filenames
are swapped relative to what they imply (already noted in
`NEXT_STEPS.md`, not fixed there since it wasn't part of that ask). Two
edits were made for this export: the truck tag photo's EXIF orientation
was corrected (it displayed sideways), and both tag photos have their VIN
line and/or barcode redacted with an opaque block, since they're real
customer documents.

## Data & persistence (Android-specific)

- **Manual entry is fully offline** — no server, no account, no network
  call. Matches the "self-contained per platform" decision made for the
  whole portability effort (web app dropped its SQL database for the
  same reason; Streamlit uses a local JSON file).
- **The optional scan path requires network** — a RevenueCat account
  (purchases + credit balance) and a call to `workers/scan-proxy/`'s
  `POST /v1/scan` (which itself calls Claude vision and RevenueCat
  server-side). Android talks to the RevenueCat SDK directly for
  balance/purchases; it only talks to the Worker for the actual scan.
- "Last 5 rigs" should persist on-device only (e.g. Room or DataStore —
  an implementation detail for the build phase, not a design concern,
  but worth knowing the data *is* expected to survive an app restart,
  unlike the web app's session-only check history).

## Current status

**Design: done, mockups confirmed present 2026-08-17.** Claude Design
produced mockups covering the full flow above — rig picker, scan-vs-manual
entry on all three tag/ticket screens, the purchase/paywall flow, the
credit-balance indicator, and results — delivered as a dated export zip
(`RV Towing Safety Calculator-2026-08-17.zip`) into `android/design/`,
which stays gitignored ("local reference only, not version-controlled")
matching the prior session's choice. Extracted contents: a `README.md`
(this reconciliation is based on it), 8 numbered screenshots (2x
resolution, 412×892), the `.dc.html` source file (not standalone —
**the screenshots are the authoritative build reference**, per the
export's own README), and the corrected `reference-images/`. This
document is the portable, synced record of what those mockups cover; the
deviations from the original brief (disclaimer wording, the new
Description/Name fields, the two reference-image interaction patterns,
the bespoke paywall) are now folded in above — if anything here still
doesn't match the actual mockups, the mockups win.

**Build: environment and business logic done, screens not started.**
Android Studio + SDK set up on this Windows machine, project scaffolded
at `android/`, `compute_breakdown`/`verdict_for` ported to Kotlin with
13/13 tests passing, and the emulator fully verified end-to-end
(2026-08-17) — see `NEXT_STEPS.md` for the full account/environment
history. Phase 3 (the actual screens, from the mockups reconciled above)
hasn't started yet.
