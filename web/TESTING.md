# Web (React) testing

Classifies `web/`'s test suite against the categories defined in the
root `TESTING.md`. Written 2026-08-21, the same day the harness itself
(Vitest + React Testing Library) was installed — this is the first test
suite this package has ever had. See `ARCHIVE_TESTING.md` and
`ARCHIVE_WEB_STREAMLIT.md` (repo root) for the narrative history.

`npm test` (`vitest run`) — currently 71 tests, all passing.
`npm run build` (`tsc -b && vite build`) typechecks `src/**`, test files
included, since `tsconfig.app.json`'s `include` is just `["src"]`.

## Event-based tiers

Per the root `TESTING.md`'s Minor/Major/External model (retired
2026-08-24, roadmap item #9): this suite has never tagged a fast subset,
so today a full `npm test` run covers both **Minor** and **Major**
undifferentiated — documented honestly here rather than inventing a
split that doesn't exist. Scoping which specific test files a given
change actually calls for (Minor vs. Major, per the root file's
regression-scoping rules) is still a per-session judgment call against
the real diff, same as any other platform. **No External suite exists
here today** — every network call (`./api`'s `extractTruckTag`/etc.) is
mocked in this suite; nothing here calls a real 3rd-party boundary
directly, so that category is N/A for this platform, not a gap.

## Coverage

Real coverage, wired up 2026-08-24 (roadmap item #9) via
`@vitest/coverage-v8`:

```bash
npm run test:coverage
```

(`vitest run --coverage`, configured in `vite.config.ts`'s `test.coverage`
block — `provider: 'v8'`, `reporter: ['text', 'json-summary']`, so the
machine-readable total lands at `coverage/coverage-summary.json`.) Real
numbers as of 2026-08-24: 91.41% statements overall (181/198); weakest
files `UploadStep.tsx` (85.71%) and `App.tsx` (86.95%). **No release
event exists for Web yet** (see `NEXT_STEPS.md`'s "Deliberately not on
this list" — local dev only), so `scripts/coverage_gate.py` reports this
number **report-only**, not enforced — see the root `TESTING.md`'s
"Coverage gate" section.

**Structured pass-rate reporting for the README dashboard** (roadmap
item #7, new 2026-08-24): `npm run test:report` runs the same suite as
`npm test` with Vitest's built-in `junit` reporter, writing to
`test-results/junit.xml` (gitignored) — see the root `TESTING.md`'s
"Dashboard" section.

## Dead code

`knip` is a dev dependency (roadmap item #10, added 2026-08-24):

```bash
npm run check:dead-code
```

Real run, 2026-08-24: found 4 exported types/interfaces (`FieldType`/
`FieldDef` in `mockData.ts`, `TireSpec`/`WizardSubStep` in `types.ts`)
that were genuinely used, just unnecessarily `export`ed — nothing outside
their own file ever imported them by name (their consuming types,
`ModuleDef`/`WizardState`, *are* imported elsewhere, and TypeScript's
structural typing means a consumer never needs the inner type imported
by name too). Fixed by removing the unneeded `export` keyword, not by
deleting anything — confirmed via `git grep` for each name before
touching it, and via a clean `npm run build` + `npm test` afterward. No
genuine dead code found. Command exits clean (0 findings) as of this
writing.

## Harness

- `vite.config.ts`'s `test` block (`environment: 'jsdom'`, one
  `setupFiles` entry) — no separate `vitest.config.ts`, kept in the same
  file as the dev/build config via the `/// <reference types="vitest/config" />`
  triple-slash pattern.
- `src/setupTests.ts` — imports `@testing-library/jest-dom/vitest` for
  matchers like `toBeInTheDocument()`/`toHaveValue()`, and centralizes
  `afterEach(cleanup)` (React Testing Library's automatic cleanup only
  self-wires when it finds a global `afterEach`, which isn't the case
  here since `globals: true` isn't set — found the hard way when
  `UploadStep.test.tsx` initially left every test's render mounted,
  causing later tests' `getByText`/`getByRole` queries to match multiple
  stale elements from earlier tests in the same file).
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
| `src/wizard/UploadStep.test.tsx` | Module | Fake props, no `App`/network involved. Title/instructions render; Extract Data is disabled with no file, enabled with one, and the drop zone's placeholder swaps to the filename; selecting a file calls `onFileSelected`; Extract Data calls `onExtract`; the error message renders when given; the scale module's two extra pieces (the "No CAT scale ticket?" hint and the second "Build Estimated Model" skip button, both wired to `onSkip`, plus the first skip button's label swapping to "No Image / Enter Weight Manually") are present only for the scale module, absent for every other one. |
| `src/wizard/ReviewStep.test.tsx` | Module | Fake props. Each field renders from `data` (blank when missing); typing calls `onFieldChange(name, isNumber, value)`; the continue button (labelled `module.continueLabel`) calls `onContinue`; the error prop renders. The stand-alone-weight scan section: absent for non-truck modules and absent for the truck module when `onScanStandaloneTicket` isn't passed; its pin-weight slider shows only while `standalone_weight_lb` is unknown, hides once it's set (via `rerender`, not a fresh mount, to prove it's the same data change driving both states); the slider's `onChange` reports the numeric value. Scanning a ticket: shows "Reading…" and disables the button while the promise it's given is pending, re-enables once resolved; a rejection surfaces the scan's own local error text, distinct from the `error` prop — complements `App.interaction.test.tsx`'s standalone-scan case, which only exercises the resolved path. |
| `src/wizard/ResultsStep.test.tsx` | Module | Fake props. Verdict headline/subline render; each breakdown item's label, badge, actual/rated weight, and note (present vs. `null`, via `rerender`) render correctly; the estimated-figures notice shows when any item is `estimated`, hidden when none are — the one thing `App.interaction.test.tsx` never exercises, since its `RESULT` fixture is always non-estimated; "Run Another Check"/"Back to Dashboard" call `onRestart`/`onGoHome`. |
| `src/wizard/RigStep.test.tsx` | Module | Fake props. No rig cards when `recentRigs` is empty; each recent rig's nickname and a manufacturer subtitle render when at least one of truck/trailer has one, the subtitle line omitted entirely when neither does; clicking a card calls `onSelectExisting` with that rig; Start New Rig stays disabled for an empty or whitespace-only nickname, enables once typed, and calls `onStartNew` with the **trimmed** nickname — the interface contract a caller (`App.tsx`'s `startNewRig`) relies on to not receive stray whitespace. |
| `src/apiShape.test.ts` | **Cross-platform interface** | "Option B" from the API-shape-drift discussion (see `FUTURE_API_SCHEMA_VALIDATION.md` for the fuller schema-export "Option C" this stops short of). Doesn't touch a real response — proves `BreakdownItem`/`VerdictInfo`, as currently declared in `types.ts`, have exactly the keys `test-vectors/breakdown_response_shape_contract.json` declares. Paired with `tests/test_api.py`'s `test_breakdown_response_matches_the_shared_api_contract`, which is the half that actually calls the real endpoint. TypeScript's excess-property checking on this file's object literals does real work here: add a field to `BreakdownItem` without adding it to the literal and the build fails (missing property) before this test even runs; remove one without removing it from the literal and the build fails too (excess property) — either way a human is forced to touch this file, and its own assertion then forces the shared contract (and the paired Python test) to be updated too. |
| `src/components/DisclaimerModal.test.tsx` | Module | Renders the disclaimer heading; clicking "I Understand — Continue" calls `onAcknowledge`. Deliberately small — this component has exactly one behavior. |
| `src/screens/History.test.tsx`, `src/screens/Dashboard.test.tsx` | Module | Both cover `verdictBadge.ts`'s `VERDICT_BADGE` map (`pass`→"Safe to Tow"/success, `fail`→"Over Limit"/warning, `partial`→"Partially Checked"/insufficient, `insufficient`→"Not Enough Info"/insufficient), which each file's verdict badge now reads from. **Regression tests for a real bug found 2026-08-21** auditing this suite's coverage: both files previously rendered *any* non-`'pass'` verdict as "Over Limit" with a warning badge — a partial or insufficient check (missing data, not an actual over-limit reading) got the same alarming label as a genuine failure. `History.test.tsx` also covers the title and per-entry nickname/date rendering; `Dashboard.test.tsx` is scoped narrowly to the verdict-labeling fix (the rest of `Dashboard.tsx` — the recent-rigs grid, its manufacturer-subtitle join, "+ Add a new rig" — remains covered only indirectly via `App.interaction.test.tsx`, a known gap below, not a full Module suite). |

## Known gaps (identified 2026-08-21, not yet closed)

- ✅ **Closed 2026-08-21**: function tests for `recentRigs.ts` and
  `api.ts` in isolation — see `src/recentRigs.test.ts` and
  `src/api.test.ts` above.
- ✅ **Closed 2026-08-21**: the `pin_weight_pct` inter-module interface
  fixture (`test-vectors/pin_weight_pct_contract.json`, `src/api.test.ts`,
  `tests/test_api.py`'s matching case) — see the root `TESTING.md`'s
  cross-platform section.
- ✅ **Closed 2026-08-21**: `ReviewStep`/`UploadStep`/`ResultsStep`
  component-level tests — see the three entries above.
- ✅ **Closed 2026-08-21**: `RigStep`/`DisclaimerModal`/`History`
  component-level tests, plus the `Dashboard`/`History` verdict-badge bug
  found in the process — see the entries above.
- ✅ **Partially closed 2026-08-21** ("Option B"): `BreakdownItemOut`/
  `VerdictOut` — the two highest-traffic response shapes — now have a
  real cross-platform interface test pair, `src/apiShape.test.ts` and
  `tests/test_api.py`'s `test_breakdown_response_matches_the_shared_api_contract`,
  via `test-vectors/breakdown_response_shape_contract.json`.
- **Still not closed**: `TruckTagOut`/`TrailerTagOut`/`ScaleTicketOut`
  (the three `/api/extract/*` response shapes, plus their nested
  `TireSpecOut`) have no equivalent contract yet — extending Option B to
  them would mean three more hand-maintained fixture files, which is
  exactly the scaling problem that motivated writing up "Option C" (a
  Pydantic JSON-Schema export, so nothing needs hand-syncing at all) in
  `FUTURE_API_SCHEMA_VALIDATION.md` rather than starting it now.
- **Not fully closed, scoped down deliberately**: `Dashboard.tsx`'s own
  logic beyond the verdict badge (the recent-rigs grid, its
  manufacturer-subtitle join, the "+ Add a new rig"/"Run Check" click
  targets) has no dedicated Module test, only indirect coverage via
  `App.interaction.test.tsx`'s happy path. Lower priority — nothing found
  auditing it suggested a real bug the way the verdict badge did.
- **Deliberately not tested**: `wizard/ProcessingStep.tsx`,
  `components/StepPills.tsx`, `components/PredictiveEstimateNotice.tsx`,
  and the `design-system/` primitives (`Badge`/`Button`/`Card`) — purely
  presentational, no branching that affects correctness, the same
  judgment call already made not to write a dedicated test for Android's
  parallel `EstimatedFiguresNotice.kt`.
