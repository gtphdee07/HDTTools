# Web (React) testing

Classifies `web/`'s test suite against the four categories defined in the
root `TESTING.md`. Written 2026-08-21, the same day the harness itself
(Vitest + React Testing Library) was installed — this is the first test
suite this package has ever had. See `NEXT_STEPS.md` for the narrative
history.

`npm test` (`vitest run`) — currently 25 tests, all passing.
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
| `src/App.interaction.test.tsx` | **Interaction** | `App.tsx` has no exported handlers — its ~10 handlers (`startNewRig`, `selectExistingRig`, `onFileSelected`, `extractCurrent`, `skipCurrent`, `scanStandaloneTicket`, `updatePinWeightPct`, `continueReview`, `updateField`, `acknowledgeDisclaimer`) all read/write one shared `wizard` state object via closures, the same shared-mutable-state shape `test_streamlit_app.py` covers on the Python side via `st.session_state`. Driven through the real rendered UI with `@testing-library/user-event`, not by calling handlers directly (they aren't reachable that way). Five cases: (1) a full happy path — start a new rig, skip all three image steps, reach Results, and confirm both `recentRigs` (localStorage) and `history` (in-memory) updated from the same `continueReview` call; (2) selecting an existing rig jumps straight to the scale step, skipping truck/trailer entirely — the same "skipped a step it shouldn't have" bug shape Android's `RigCheckNavHostTest` caught on 2026-08-18, here as a regression-shaped test written ahead of any bug, not after one; (3) an extraction error clears once the user skips instead of retrying, not left dangling on `wizard.uploadError`; (4) scanning a tow-vehicle-only ticket fills the stand-alone-weight field and hides the now-unnecessary pin-weight slider; (5) the pin-weight slider's value *leaves App.tsx* as the raw 15–25 whole number, unconverted — `./api` is mocked here, so this only proves App passes the number through, not that `api.ts` itself converts it (that's `src/api.test.ts`, below). |
| `src/api.test.ts` | Function + **Cross-platform interface** | Only `fetch` is mocked, so `api.ts` itself runs for real. `createBreakdown`: request shape (truck/trailer/scale pass through unchanged), success resolves with the parsed body, failure rejects with the server's `detail` message or a generic `Request failed (status)` fallback when the body has no `detail` (or isn't JSON) — plus the **cross-platform interface** case, `pin_weight_pct: pinWeightPct / 100`, paired with `tests/test_api.py`'s `test_breakdown_endpoint_pin_weight_pct_is_a_fraction_not_the_ui_percentage` via the shared `test-vectors/pin_weight_pct_contract.json` fixture (a Python-side and TypeScript-side test both derive their expected numbers from the one file, not two independently hardcoded ones). `extractTruckTag` gets the same success/error coverage (posts `FormData` with the file, to `/api/extract/truck-tag`); `extractTrailerTag`/`extractScaleTicket` only confirm they hit their own distinct endpoint, since they're thin wrappers over the same shared `postFile` helper `extractTruckTag` already exercises fully — a copy-paste bug pointing two of them at the same path is the one thing that actually varies between them. |
| `src/recentRigs.test.ts` | Function | `loadRecentRigs`: empty array when nothing stored, the stored array when valid, empty array (not a throw) on corrupt JSON or a parsed-but-non-array value. `saveRecentRig`: prepends and persists a new rig; replaces (not duplicates) a same-nickname rig case-insensitively, moving it to the front; caps the list at 5, dropping the oldest; still returns the computed list even if `localStorage.setItem` throws (e.g. quota exceeded) — the in-memory return value staying usable even when persistence silently fails is deliberate behavior worth locking down, not an oversight. |

## Known gaps (identified 2026-08-21, not yet closed)

- ✅ **Closed 2026-08-21**: function tests for `recentRigs.ts` and
  `api.ts` in isolation — see `src/recentRigs.test.ts` and
  `src/api.test.ts` above.
- ✅ **Closed 2026-08-21**: the `pin_weight_pct` inter-module interface
  fixture (`test-vectors/pin_weight_pct_contract.json`, `src/api.test.ts`,
  `tests/test_api.py`'s matching case) — see the root `TESTING.md`'s
  cross-platform section.
- **`ReviewStep`/`UploadStep`/`ResultsStep` have no dedicated
  component-level tests** of their own yet - only indirect coverage via
  `App.interaction.test.tsx` driving them through `App`. Lower priority
  than the interaction suite per the retrofit's stated order (App's
  shared-state handlers first), but each has enough own logic (e.g.
  `ReviewStep`'s `standaloneWeightKnown` conditional, `UploadStep`'s
  scale-specific extra skip button) to eventually warrant its own Module-
  category tests.
