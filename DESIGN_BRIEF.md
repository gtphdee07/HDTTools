# RigCheck Design Brief — screens for the visual refresh + new accounts/paywall work

**For: graphics designer.** This document lists every screen in RigCheck
today, plus every new screen needed for upcoming account/paywall features,
so visual design work can start without reading any code. It does not
prescribe colors, layout, or visual style — that's the design work itself.
It only defines: what each screen is for, what has to be on it, where it
sits in the flow, and whether it's an existing screen getting a refresh or
a brand-new one being designed from scratch.

**Companion Artifact** (visual flow diagram + this same content in a
shareable page): see the link at the bottom of this document once published.

## How to read this

Each screen is tagged:
- 🔄 **Refresh** — screen already exists and works; only needs the new
  colors/visual language applied, not a new layout.
- 🆕 **New** — doesn't exist yet; needs full visual design from scratch.
- 🔧 **Evolve** — exists today but its purpose is changing (e.g. gaining an
  account concept it doesn't have now), so it needs more than a re-skin but
  isn't starting from a blank page either.

## Design foundation (context for the refresh)

Both platforms already pull their colors from one shared source, kept in
sync by convention: Android's `Color.kt` (Kotlin) mirrors Web's
`tokens.css`. The current palette is the "Wandering Trails, Wagging Tails"
theme (sunset orange, trail green, dusk mauve, sunset rose, charcoal/cream
neutrals). The refresh should replace this one shared palette definition,
not be designed twice — whatever new colors are chosen apply identically to
both platforms.

Both platforms also already have a small reusable component library rather
than one-off styling per screen:
- **Web** (`design-system/`): Button, Card, Badge — each screen composes
  from these three plus shared page components (Header, StepPills,
  DisclaimerModal, PredictiveEstimateNotice).
- **Android** (`ui/components/`): a handful of shared composables
  (BreakdownRow, CreditBalanceChip, ReferenceImageCard, LabeledFields,
  ScanOrManualChooser, EstimatedFiguresNotice) reused across screens.

Redesigning these shared building blocks once, rather than each screen
individually, covers most of the visual surface on both platforms.

---

## Android screens

Entry point: **Rig Picker**. Full flow: Rig Picker → Chooser (per module) →
manual entry or photo scan → cycles Truck → Trailer → Scale → Disclaimer
(first time only) → Results. Paywall is reached only from Chooser, either
by tapping "Scan Photo" with zero credits, or by tapping the credit-balance
indicator.

### Core flow — 🔄 Refresh

| Screen | Purpose | Reached from → leads to |
|---|---|---|
| Rig Picker | Home/start screen — pick a previously-used truck+trailer combo, or start a new one by nickname | App launch → Chooser |
| Chooser | Per-document-type screen: "scan a photo" (camera or gallery) vs. "enter manually," for whichever of Truck/Trailer/Scale is next | Rig Picker, or the previous entry screen's "Continue" → an entry screen, or Paywall |
| Truck Tag Entry | Reviewed/editable form for the truck's compliance-label fields (manufacturer + 3 weight figures) | Chooser (Truck) → Chooser (Trailer) |
| Trailer Tag Entry | Same, for the trailer's compliance label | Chooser (Trailer) → Chooser (Scale) |
| Scale Ticket Entry | Same, for the CAT Scale weigh ticket | Chooser (Scale) → Disclaimer or Results |
| Disclaimer | One-time (first check only) "experimental tool, not a certified safety decision" acknowledgment | Scale Ticket Entry (first time only) → Results |
| Results | The computed axle-by-axle pass/fail verdict | Disclaimer or Scale Ticket Entry (repeat checks) |

### Paywall / credits — 🔧 Evolve

| Screen | Today | What's changing |
|---|---|---|
| Paywall | Shows current credit balance, lists purchasable credit packages with live store pricing, Buy/Restore-purchase buttons. No account or login concept at all. | Needs to become account-aware — it will sit behind login once accounts exist, and may need to show *which account* is buying credits. Purchase-list/buy/restore mechanics stay the same shape. |
| Credit balance indicator | A small pill (camera icon + "N scans") shown on the Chooser screen; tapping it opens Paywall. | Likely stays the same shape and placement; may need a subtle treatment change once it's tied to a real account rather than an anonymous store identity. |

### New account screens — 🆕 New

| Screen | Purpose | Notes for design |
|---|---|---|
| Sign Up | Create an account: email + password, plus "Continue with Google" and "Continue with Apple" | Only needs to appear when the user first tries to reach Paywall without an account — the free manual-entry flow above stays fully ungated |
| Log In | Same fields/buttons as Sign Up, returning-user framing | Reached the same way as Sign Up, or from Account/Profile's "log out" |
| Forgot / Reset Password | Standard "enter your email, get a reset link" flow | Reached from Log In |
| Account / Profile | Shows the logged-in email, a log-out action | Reached from a new entry point (likely near the credit-balance indicator, or a small profile icon) — exact placement is a design decision |

---

## Web screens

Entry point: **Dashboard**. Top-level screens are `Dashboard`, `History`,
and `Wizard` (a 5-step flow). No account/settings screen exists at all
today.

### Core flow — 🔄 Refresh

| Screen | Purpose | Reached from → leads to |
|---|---|---|
| Dashboard | Home screen — "Start New Check" button, your recent rigs, your 2 most recent check results | App load → Wizard, or History |
| History | Full list of past checks and their verdicts | Header nav → (back to Dashboard) |
| Rig Step (wizard step 1) | Pick an existing rig or start a new one by nickname | Dashboard ("Start New Check") → Upload |
| Upload Step (per doc type, steps 2-4) | Upload a photo, or "I don't have this image" to skip to manual entry | Rig Step → Processing (or straight to Review if skipped) |
| Processing Step | Loading state while OCR runs | Upload → Review |
| Review Step | Editable, reviewed field values for that document | Processing → next document type, or Results if this was the last one |
| Results Step | The computed verdict, plus a one-time disclaimer modal shown first the very first time | Review (Scale Ticket) → Dashboard, or restart |

### New account screens — 🆕 New

| Screen | Purpose | Notes for design |
|---|---|---|
| Sign Up | Create an account: email + password, plus "Continue with Google" and "Continue with Apple" | Only appears when the user tries to reach the Claude-vision paid tier — the free Tesseract wizard flow above stays fully ungated |
| Log In | Same as Android's | Same trigger points as Sign Up |
| Forgot / Reset Password | Same as Android's | Reached from Log In |
| Account / Profile | Logged-in email, log-out action | New entry point in the Header, alongside "Dashboard"/"History" |
| Paywall / Upgrade | Shows current credit balance, lists purchasable packages, buy button (billed via Stripe, not an app-store purchase) | Same conceptual shape as Android's Paywall — balance, options, purchase action — but the payment mechanism underneath is different |
| Credit balance indicator | Small persistent indicator of remaining credits | Placed in the Header, same idea as Android's chip |

---

## Cross-platform notes

- **The free tier stays fully ungated on both platforms.** Login only gets
  triggered when a user tries to reach the paid Claude-vision tier — not at
  app launch, not on the manual-entry/Tesseract path. Keep this framing in
  mind when placing the new Sign Up/Log In entry points: they're a
  "gate before checkout," not a front door.
- **One account works on both platforms.** A user's login, credit balance,
  and purchase history are the same whether they're on the Android app or
  the web app — design the Account/Profile screen with that framing (no
  need for a "which platform am I on" distinction in the UI itself).
- **Account linking/migration is explicitly out of scope for this pass** —
  if a returning user has an existing Android-only purchase history from
  before accounts existed, reconciling that is a separate, later effort.
- Not in scope for this brief: anything about *how* payment/auth is wired
  up technically (Stripe vs. RevenueCat, token formats, etc.) — that's
  engineering work happening in parallel and doesn't change what's on
  these screens.

---

*Companion Artifact (same content, with visual flow diagrams, designer-shareable): https://claude.ai/artifact/TgHcNTKWDkrLs52skQkqGW — this file is the canonical, versioned source; update it first if anything here changes, then republish the Artifact.*
