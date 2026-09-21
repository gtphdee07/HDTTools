# Screen-level UI re-skin: match RigCheck's design canvases (Refresh screens only)

## Context

Item #21 (2026-09-21) ported the "Wandering Trails Wagging Tails" color/font
tokens into both codebases at the shared-component level (`tokens.css`,
Android's `Color.kt`/`Theme.kt`/`Type.kt`), but explicitly left "matching
each screen's layout to the fuller visual treatment shown in the Artifact
canvases" undone. `DESIGN_BRIEF.md` tags 7 Web + 7 Android screens as
"🔄 Refresh" (existing, working screens needing only a visual update, no
new backend). This work was picked specifically because it's independent
of the still-pending entitlement/scan-gating axis decision (item #20) —
these are today's free, no-account flow.

I pulled and read all 14 real mockup artboards from the two published
design canvases (`RigCheck Web` — `https://claude.ai/artifact/XAShfYmhqyvjyJKQmjPcyQ`,
`RigCheck Android` — `https://claude.ai/artifact/Upyv1fvNLmuAM5JxdCX8Bt`) and
compared each against its current implementation. Finding: the "Refresh"
label undersells the gap unevenly.

- **Android's gap is small.** `BreakdownRow.kt` already renders exactly the
  icon+label+percentage+progress-bar+expandable-note pattern the Results
  mockup shows. `ScanOrManualChooser` already matches the Chooser mockup's
  two-card pattern (scan vs. manual, per DESIGN_BRIEF). Mainly needs a
  layout/spacing/step-indicator pass, not new components.
- **Web's gap is real.** No `Footer` component exists anywhere in
  `web/src/` today. `Header.tsx` uses plain text nav buttons where every
  mockup shows pill-shaped nav. `Dashboard.tsx` is missing entire sections
  the mockup has (hero with headline/CTA/3-step graphic, per-axle
  progress-bar cards for recent checks, a 4-up rig grid, an "Upgrade"
  teaser banner). `History.tsx` is a flat list where the mockup shows
  filter pills + a table layout. `StepPills.tsx` is flat pills where the
  mockup shows numbered circles connected by lines. `ResultsStep.tsx` is
  the closest Web screen to its mockup already (it already has per-axle
  progress bars via `item.pct`/`item.barColor`).

## Goal

Bring all 14 "Refresh" screens to visual/structural parity with their
mockups (same sections, same content arrangement, same component
treatments) using the already-ported color/type tokens — presentation
layer only, no data flow, API, or business logic changes, and nothing
touching the Evolve (Paywall, credit chip) or New (accounts) screens.

## Scope boundary (explicit exclusions)

- No Paywall / credit-balance-chip changes (Evolve — needs account-aware
  backend, tied to item #20).
- No Sign Up / Log In / Forgot / Account screens (New — same reason).
- The mockups' header nav shows a scan-credit chip and an Account link on
  every screen. Since neither accounts nor credits exist in the deployed
  Web app yet, these are **omitted** from the rebuilt Header for now, not
  stubbed — adding a fake/dead affordance would be worse than leaving the
  space for later. Revisit when item #20 ships.
- The mockups' "Upgrade to Claude scanning" banners (Dashboard, Results)
  **are** included, but as static/inert sections — matching copy and
  layout, button disabled or pointing nowhere real — since Paywall itself
  doesn't exist yet. Wire to the real Paywall when item #20 ships.

## Execution order

**Android first** (steps 1-5 of the Android section below), since its
existing components (`BreakdownRow`, `ScanOrManualChooser`) already closely
match the mockups — smaller, faster wins that confirm the re-skin approach
before tackling Web's bigger lift. **Web** (steps 1-10 of the Web section)
follows, shared chrome (Footer/Header/StepPills) before the individual
screens that depend on it.

## Steps

### Android — layout/spacing pass (components already close, do this first)

1. **`RigPickerScreen.kt`**: radio-card rig list + nickname input +
   sticky bottom Continue button, matching `Main.dc.html` (Android).
2. **`ChooserScreen.kt`**: add the 3-segment step-progress bar (Step X
   of 3), confirm the scan-vs-manual two-card layout matches
   `Android-2-Chooser.dc.html` (likely close already per
   `ScanOrManualChooser`).
3. **`TruckTagEntryScreen.kt` / `TrailerTagEntryScreen.kt` /
   `ScaleTicketEntryScreen.kt`**: same step-progress-bar treatment,
   confirm field-list spacing/low-confidence-warning styling matches
   `Android-3/4/5-*.dc.html`, sticky bottom Confirm button.
4. **`DisclaimerScreen.kt`**: centered icon + headline + body + checkbox
   treatment, matching `Android-6-Disclaimer.dc.html`.
5. **`ResultsScreen.kt`**: header row (rig name/date + verdict badge),
   confirm `BreakdownRow` usage/spacing matches
   `Android-7-Results.dc.html`, sticky bottom "Start another check".

### Web — shared chrome and components first (used by every screen)

1. **New `web/src/components/Footer.tsx`**: brand wordmark, nav links
   (Dashboard/History), disclaimer line, copyright — matches every
   mockup's footer exactly (same content/order on all 7). Wire into
   `App.tsx` once, below the routed screen content.
2. **Rework `web/src/components/Header.tsx`**: pill-shaped nav items
   (active = filled pill) replacing today's plain text buttons, matching
   the mockup's header treatment. Keep existing props/behavior
   (`onGoHome`/`onGoHistory`/`onStartWizard`); this is a visual-only
   change to the same component.
3. **Upgrade `web/src/components/StepPills.tsx`**: numbered-circle +
   connector-line treatment (mockup shows 5 steps — Rig/Truck
   tag/Trailer tag/Scale ticket/Results — vs. today's 4 which start at
   "Truck Tag"). Add the missing "Rig" step to match `Wizard-1-Rig`'s
   presence in the mockup flow. Check `RigStep.tsx`/`App.tsx` for how the
   step number is currently threaded through before changing the shape.
4. **`web/src/screens/Dashboard.tsx`**: add hero section (headline/
   subhead/CTA button + 3-step icon graphic, static content — no new
   data), convert the Recent Checks list to full cards with per-axle
   progress bars (reuse the exact bar pattern already in
   `wizard/ResultsStep.tsx`'s `item.pct`/`item.barColor` rendering — pull
   into a small shared row component if reused 2+ places), rework the rig
   grid to the mockup's 4-up layout with colored dot + "Start check" link
   + dashed "new rig" tile (reuses existing `RecentRig` data, no new
   props needed). Add a static "Upgrade" teaser banner section (no real
   Paywall link target yet — link to nothing or disable, per the scope
   boundary above).
5. **`web/src/screens/History.tsx`**: add filter-pill row (All rigs /
   per-rig / Within limits / Over limit — client-side filter over
   existing `history` prop, no new data needed) and convert the list to
   the mockup's table-style grid (Date/Rig/Truck+Trailer/Verdict/View
   columns).
6. **`web/src/wizard/RigStep.tsx`**: radio-card list of existing rigs +
   "start new rig" nickname input, matching `Wizard-1-Rig.dc.html` —
   check current implementation first; likely needs restyling more than
   restructuring since the underlying pick/create-rig logic already
   exists.
7. **`web/src/wizard/UploadStep.tsx`**: dashed drop-zone with icon +
   "what we read" info sidebar card + "I don't have this image" skip
   link, matching `Wizard-2-Upload.dc.html`.
8. **`web/src/wizard/ProcessingStep.tsx`**: circular spinner + 3-item
   checklist (Photo received / Reading the label / Checking the numbers),
   matching `Wizard-3-Processing.dc.html`.
9. **`web/src/wizard/ReviewStep.tsx`**: split photo-preview/form layout,
   inline low-confidence-field warning treatment (border+note, mirrors
   what `ReviewStep.tsx` likely already flags via existing confidence
   data — restyle, not new logic), matching `Wizard-4-Review.dc.html`.
10. **`web/src/wizard/ResultsStep.tsx`**: smallest change of the 7 — add
    the split-layout static "Scan again with Claude" teaser card
    (no real link target, same scope boundary as step 4's Upgrade
    banner) and confirm the disclaimer banner matches
    `Wizard-5-Results.dc.html`'s styling. Breakdown cards already match.

### Wrap-up

11. Re-run the accessibility check from item #21 (no white text landing on
    orange/teal) on every newly added element — the on-orange/on-teal
    tokens already exist, just need applying to new markup.
12. Update `NEXT_STEPS.md` item #21 (or add a follow-up item) recording
    this as done, since #21 explicitly flagged this as outstanding.

## Definition of Done

- All 14 screens match their mockup's layout/section structure using
  already-ported tokens (not necessarily pixel-perfect, but same
  sections in the same arrangement).
- Zero changes to data flow, API calls, props contracts, or business
  logic — verified by diffing each changed file's non-JSX/non-Composable
  logic.
- `npm run build` (web) and `./gradlew.bat compileDebugKotlin` (Android)
  both pass clean.
- Existing test suites pass; any test asserting on now-changed DOM
  structure/Compose tree gets updated (not deleted) to match.
- `NEXT_STEPS.md` reflects completion.

## Verification

- After each Android screen (1-5): build and run on the existing AVD,
  visual compare against its `.dc.html` mockup.
- After the Web shared-chrome steps (1-3 of the Web section): run
  `npm run dev`, visually compare Header/Footer/StepPills against the
  mockups on at least one screen.
- After each remaining Web screen (4-10 of the Web section): visual
  compare against its `.dc.html` mockup in the browser.
- Full `npm test` (web) and Android test suite run once at the end.
- Final side-by-side pass: every one of the 14 screens open next to its
  mockup.
