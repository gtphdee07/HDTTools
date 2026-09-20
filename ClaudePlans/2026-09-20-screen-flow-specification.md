# Screen & flow specification for accounts + paywall + UI refresh

## Context

Two things converged in this conversation and both land on the same deliverable:

1. **User feedback requires a color/UI-UX refresh**, starting on Android and
   expected to flow to Web too — the two platforms already share one design-
   token source by convention (`Color.kt`'s own header comment: "Ported from
   web/src/design-system/tokens.css ... keep in sync"), so this should be
   done as one unified design pass, not two separate ones.
2. **Upcoming feature work needs screens that don't exist on either platform
   today**: shared accounts across Android + Web, and a paywall/upgrade flow
   (Web's future Claude-vision tier per `NEXT_STEPS.md` roadmap item #20;
   Android's existing `PaywallScreen` evolving from anonymous-RevenueCat-only
   to account-aware).

Before your graphics designer can start real visual design work, someone
needs to define **what screens are needed and how they connect** — not the
visual design itself, just the structural inventory: each screen's purpose,
where it sits in each platform's navigation flow, what data/state it needs,
and — critically — which screens already exist and just need a re-skin vs.
which are being designed from scratch.

Decisions already locked in earlier this session that shape this spec:
- Android ships first (informal/sideload beta); Web follows later.
- Shared accounts across Web and Android (one login, cross-platform
  entitlement) — not two independent account systems.
- New Sign Up / Log In screens support email+password **and** "Continue with
  Google"/"Continue with Apple" social login.
- **No account-linking/migration screen** in this pass — deferred until
  actually needed, kept out of scope here.
- Deliverable is a **unified brief** (existing screens needing the refresh +
  net-new screens for accounts/paywall together), published as **both** a
  repo doc and a shareable Artifact with a flow diagram.

## Goal

Produce one screen/flow specification — covering both Android and Web, both
existing screens (refresh scope) and net-new screens (accounts/paywall
scope) — detailed enough that a graphics designer can start visual design
work without reading code or needing follow-up engineering questions.

## What already exists (confirmed from source — refresh scope, not redesign-from-scratch)

**Android** (entry point `RigPicker`; full graph confirmed via
`RigCheckNavHost.kt`/`RigCheckRoute.kt`):
`RigPicker` → `Chooser(module)` → manual entry or photo scan for that module
→ cycles Truck → Trailer → Scale → `Disclaimer` (first run only) or straight
to `Results`. `Paywall` is reachable only from `Chooser`, via two triggers:
the 0-credit gate on "Scan Photo," or tapping the `CreditBalanceChip`.
- `RigPickerScreen`, `ChooserScreen` (+ `CreditBalanceChip` contextual
  component), `TruckTagEntryScreen`, `TrailerTagEntryScreen`,
  `ScaleTicketEntryScreen`, `DisclaimerScreen`, `ResultsScreen`
- `PaywallScreen` — today a **pure RevenueCat purchase UI**: shows balance,
  lists packages with live store pricing, buy/restore buttons — no account
  or login concept anywhere in it.

**Web** (`Screen` type is exactly `home | history | wizard`, confirmed via
`App.tsx`/`types.ts` — no settings/account screen exists at all today):
- `Dashboard` (home), `History`
- Wizard sub-flow: `RigStep` → `UploadStep`/`ProcessingStep`/`ReviewStep`
  per doc type (Truck → Trailer → Scale) → `DisclaimerModal` (first time
  only) → `ResultsStep`
- Shared components: `Header`, `DisclaimerModal`, `StepPills`,
  `PredictiveEstimateNotice`
- Design-system: `Button`, `Card`, `Badge`, `tokens.css`

## Net-new screens needed (native UI on each platform)

1. **Sign Up** — email/password + social login buttons
2. **Log In** — same auth methods
3. **Forgot / Reset Password**
4. **Account / Profile** — email, log out
5. **Paywall / Upgrade** — Android: evolve the existing `PaywallScreen` to
   be account-aware; Web: net-new, same conceptual shape (balance, package
   list, buy) via Stripe Checkout instead of RevenueCat
6. **Credit balance indicator** — Android: `CreditBalanceChip` already
   exists, evolve as needed; Web: net-new equivalent, placed in `Header`

## Steps

1. Write one entry per screen (both refresh-scope and net-new, ~17 screens
   total across both platforms) with: purpose, platform, entry/exit points
   in its nav flow, key data/state (loading/empty/error where relevant),
   and an explicit "refresh only" vs. "new design" flag.
2. Write the repo doc: `DESIGN_BRIEF.md` at the repo root, matching the
   existing top-level `*.md` convention (`NEXT_STEPS.md`, `ARCHIVE_*.md`).
3. Build a flow diagram — Android's nav graph and Web's nav graph, existing
   vs. net-new screens visually distinguished — using the
   `artifact-diagramming` approach.
4. Publish a shareable Artifact (via `artifact-design`'s document/brief
   treatment) combining the written brief and the diagram, written for a
   non-technical reader.
5. Cross-link: `DESIGN_BRIEF.md` records the Artifact's URL; the Artifact
   notes the repo doc as the canonical, versioned source for future edits.

## Definition of Done

- `DESIGN_BRIEF.md` exists in the repo root and lists every screen (all ~17)
  with purpose/flow/data/state and its refresh-vs-new flag filled in — no
  placeholders.
- A published Artifact exists with the same content in designer-shareable
  form plus the flow diagram; its URL is recorded in `DESIGN_BRIEF.md`.
- The spec reflects every locked-in decision above (shared accounts, social
  login, no linking screen, Android-first sequencing) without requiring the
  designer to have this conversation's context.

## Verification

- Re-read the finished `DESIGN_BRIEF.md` and Artifact and confirm every
  screen from both lists above is present with all fields filled in.
- Confirm the Artifact opens and its diagram accurately matches the nav
  graphs found during exploration (the `RigPicker`/`Chooser`/`Paywall`
  chain on Android; `home`/`history`/`wizard` on Web).
- Get your sign-off before treating the designer handoff as ready.
