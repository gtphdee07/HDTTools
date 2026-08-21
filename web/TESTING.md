# Web (React) testing

Classifies `web/`'s test suite against the four categories defined in the
root `TESTING.md`. Written 2026-08-21, the same day the harness itself
(Vitest + React Testing Library) was installed — this is the first test
suite this package has ever had. See `NEXT_STEPS.md` for the narrative
history.

`npm test` (`vitest run`) — currently 6 tests, all passing.
`npm run build` (`tsc -b && vite build`) typechecks `src/**`, test files
included, since `tsconfig.app.json`'s `include` is just `["src"]`.

## Harness

- `vite.config.ts`'s `test` block (`environment: 'jsdom'`, one
  `setupFiles` entry) — no separate `vitest.config.ts`, kept in the same
  file as the dev/build config via the `/// <reference types="vitest/config" />`
  triple-slash pattern.
- `src/setupTests.ts` — imports `@testing-library/jest-dom/vitest` for
  matchers like `toBeInTheDocument()`/`toHaveValue()`.
- Network calls (`./api`'s `extractTruckTag`/`extractTrailerTag`/
  `extractScaleTicket`/`createBreakdown`) are mocked with `vi.mock('./api')`
  in every test that needs them — nothing here ever hits a real backend.
  `localStorage`/`sessionStorage` are the real jsdom implementations, not
  mocked, since `recentRigs.ts` and the disclaimer-acknowledged flag's
  actual persistence behavior is exactly what's worth exercising for real.

## By file

| File | Category | Covers |
|---|---|---|
| `src/App.smoke.test.tsx` | Function | Proves the harness itself works (jsdom environment, jest-dom matchers, `App`'s `localStorage`/`sessionStorage` reads on mount) before anything real was written against it. Not meant to catch regressions in `App` itself. |
| `src/App.interaction.test.tsx` | **Interaction** | `App.tsx` has no exported handlers — its ~10 handlers (`startNewRig`, `selectExistingRig`, `onFileSelected`, `extractCurrent`, `skipCurrent`, `scanStandaloneTicket`, `updatePinWeightPct`, `continueReview`, `updateField`, `acknowledgeDisclaimer`) all read/write one shared `wizard` state object via closures, the same shared-mutable-state shape `test_streamlit_app.py` covers on the Python side via `st.session_state`. Driven through the real rendered UI with `@testing-library/user-event`, not by calling handlers directly (they aren't reachable that way). Five cases: (1) a full happy path — start a new rig, skip all three image steps, reach Results, and confirm both `recentRigs` (localStorage) and `history` (in-memory) updated from the same `continueReview` call; (2) selecting an existing rig jumps straight to the scale step, skipping truck/trailer entirely — the same "skipped a step it shouldn't have" bug shape Android's `RigCheckNavHostTest` caught on 2026-08-18, here as a regression-shaped test written ahead of any bug, not after one; (3) an extraction error clears once the user skips instead of retrying, not left dangling on `wizard.uploadError`; (4) scanning a tow-vehicle-only ticket fills the stand-alone-weight field and hides the now-unnecessary pin-weight slider; (5) the pin-weight slider's value reaches `createBreakdown` as the raw 15–25 whole number, not divided by 100 — the exact units-convention risk (whole number in the UI vs. a `0.15`–`0.25` fraction in `compute_breakdown`) flagged when this retrofit was planned. |

## Known gaps (identified 2026-08-21, not yet closed)

- **No function tests yet** for `recentRigs.ts` (`loadRecentRigs`/
  `saveRecentRig`'s own logic — nickname de-dup, the 5-rig cap, corrupt-
  JSON fallback) or `api.ts` (request shape, error-body parsing) in
  isolation. Currently covered only indirectly, through the interaction
  suite's happy path.
- **No inter-module interface fixture** yet between `test_api.py` and a
  Web-side test for the `/api/breakdown` request/response contract - the
  `pin_weight_pct` units convention above is now locked down from the Web
  side (whole number in, sent as `pin_weight_pct / 100` by `api.ts`), but
  nothing on the Python side asserts the matching expectation from
  `test_api.py`'s end, the way `test_breakdown_golden_vectors.py` does for
  `compute_breakdown` itself.
- **`ReviewStep`/`UploadStep`/`ResultsStep` have no dedicated
  component-level tests** of their own yet - only indirect coverage via
  `App.interaction.test.tsx` driving them through `App`. Lower priority
  than the interaction suite per the retrofit's stated order (App's
  shared-state handlers first), but each has enough own logic (e.g.
  `ReviewStep`'s `standaloneWeightKnown` conditional, `UploadStep`'s
  scale-specific extra skip button) to eventually warrant its own Module-
  category tests.
