# Web (React) testing

Classifies `web/`'s test suite against the categories defined in the
root `TESTING.md`. Written 2026-08-21, the same day the harness itself
(Vitest + React Testing Library) was installed — this is the first test
suite this package has ever had. See `ARCHIVE_TESTING.md` and
`ARCHIVE_WEB_STREAMLIT.md` (repo root) for the narrative history.

`npm test` (`vitest run`) — currently 156 tests, all passing (count last
confirmed 2026-10-05; a fuller refresh of this document is #64).
`npm run build` (`tsc -b && vite build`) typechecks `src/**`, test files
included, since `tsconfig.app.json`'s `include` is just `["src"]`.

## Running tests

| Level | Command |
|---|---|
| One file | `npm test -- src/breakdown.test.ts` (run from `web/`) |
| Whole context (offline) | `npm test` |

The one-file command is a Vitest path filter, not an exact match — a less
specific path can select more than one file.

Neither reaches a live provider: `vite.config.ts` excludes
`*.external.test.ts`, which only `npm run test:external` runs. A command
check (`tests/test_context_test_commands.py`, #52) confirms both commands
select the intended files and never an external one.

## Event-based tiers

Per the root `TESTING.md`'s Minor/Major/External model (retired
2026-08-24 — full narrative in `ARCHIVE_TESTING.md`): this suite has never tagged a fast subset,
so today a full `npm test` run covers both **Minor** and **Major**
undifferentiated — documented honestly here rather than inventing a
split that doesn't exist. Scoping which specific test files a given
change actually calls for (Minor vs. Major, per the root file's
regression-scoping rules) is still a per-session judgment call against
the real diff, same as any other platform. `npm test` runs no live
call: every network call (`./api`'s `extractTruckTag`/etc.) is mocked, and
`vite.config.ts` excludes `*.external.test.ts`.

## External suite (ADR-0008)

`npm run test:external` runs `src/external/*.external.test.ts` against the
live providers via `vitest.external.config.ts`. Two surfaces today, each
tagged `[surface]` in its describe title; credentials come from the
gitignored `web/.env.local` and a missing one fails the run, never skips
it. Normally run through `web/test-external.ps1`, which runs only the
surfaces `scripts/external_freshness.py` reports stale and records each
result with `scripts/record_external_result.py` (`-Skip` records
`skipped`, which leaves the surface stale). Add a surface by adding
`scripts/external_manifest/surfaces/<name>.json` and a
`<name>.external.test.ts` whose describe title carries `[<name>]`.

| Surface | Test file | Paid calls |
|---|---|---|
| `supabase-auth` | `supabaseAuth.external.test.ts` | 0 |
| `pages-site` | `pagesSite.external.test.ts` | 0 |

Both are free, so the wrapper runs them without a confirmation prompt.
`externalGuards.test.ts` (in `npm test`) statically guards both files: never
collected by `npm test`, never create a user or send mail, never print a
secret, and the Pages file only issues GETs and never signs in.

### `supabase-auth`

Real calls to the live Supabase project with the test user from
`scripts/wizard_web_external_test_user.sh`. It never creates a user or sends
mail.

### `pages-site` (#42)

Real requests to the deployed Cloudflare Pages site
(`https://rigcheck-web.pages.dev/`). Boundary files are `web/wrangler.toml`,
`web/.env.production`, `web/index.html`, `web/vite.config.ts`,
`web/src/main.tsx` and `web/public/`; pins are `web/wrangler.toml`,
`web/package.json` and `web/package-lock.json`; the watched registry package
is `wrangler` (Pages' deploy tool). Only `VITE_SUPABASE_URL` and
`VITE_SUPABASE_PUBLISHABLE_KEY` are needed (to know what the production
build should have baked in); no test account is used.

Two deliberate trade-offs. The expected host and key come from the
gitignored `web/.env.local`, i.e. the same Supabase project the
`supabase-auth` suite tests, so a deployed build pointing at a different
project fails; the committed `web/.env.production` is a freshness boundary
file, not the test's oracle. And `wrangler` appears in no pin file (it is
not a `web/` dependency), so a wrangler change is detected only through
its registry release date; `web/package.json` and the lockfile are pins
shared with `supabase-auth`, so unrelated dependency churn can also mark
this surface stale.

| ADR-0008 depth | Covered by |
|---|---|
| Reachable and authenticated | The URL returns 200 over HTML with the app shell (`<div id="root">`, the RigCheck title). **Authentication does not apply**: the site is public and read-only, so there is nothing to sign in to. |
| Response shape | The shell names one module script and one stylesheet; the bundle is real JavaScript (not an HTML fallback) of plausible size, the stylesheet is CSS, `/logo.png` is a PNG. The bundle names exactly one Supabase host, equal to the configured project's host (so not `undefined`, a placeholder or a second project), and contains the configured publishable key and no `sb_secret_` key or `service_role` JWT. |
| Error contract | Unknown paths (`/no/such/page`, `/history/deep/link`) return the app shell with 200, identical to `/`, not a Cloudflare error page. |
| Full journey | Loads the shell, runs the live production bundle in jsdom, clicks the header's "Sign in", and sees the email and password fields, with no "Accounts unavailable" card (what a build without the Supabase variables shows). It never submits the form. |

Not covered, by design: a stale page that still points at a deleted hashed
asset (`/assets/nope.js`) gets the shell back with a 200 instead of a 404,
a Pages behaviour a test cannot change (the suite does catch the current
shell's own bundle, stylesheet or logo failing to load, or coming back as
HTML); and real-browser layout or interaction beyond reaching the sign-in
screen.

**Review of existing external tests against the four depths** (read-only,
per the #51 scope note): the only existing Web external file,
`supabaseAuth.external.test.ts`, already covers reachable-and-authenticated
(project URL and key accepted, bad key rejected), response shape (session
with a three-part JWT, user id, confirmed email), error contracts (bad
password, unknown email, malformed sign-up and reset) and a full
sign-in/sign-out journey. No gaps; nothing was changed or retagged. Web has
no older release or weekly External suites.

## Coverage

Real coverage, wired up 2026-08-24 (see `ARCHIVE_TESTING.md`) via
`@vitest/coverage-v8`:

```bash
npm run test:coverage
```

(`vitest run --coverage`, configured in `vite.config.ts`'s `test.coverage`
block — `provider: 'v8'`, `reporter: ['text', 'json-summary']`, so the
machine-readable total lands at `coverage/coverage-summary.json`.) **No
release event exists for Web yet** (see `NEXT_STEPS.md`'s "Deliberately
not on this list" — local dev only), so `scripts/coverage_gate.py`
reports this number **report-only**, not enforced — see the root
`TESTING.md`'s "Coverage gate" section.

`coverage.include: ['src/**']` (added for the #57 test audit) scopes the
report to application code explicitly, rather than to whatever a test
happened to import. Without it, a file no test imports (e.g. `main.tsx`,
the Vite entry point) was silently absent from the report instead of
showing up as an uncovered gap.

**Structured pass-rate reporting for the README dashboard** (roadmap
item #7, new 2026-08-24): `npm run test:report` runs the same suite as
`npm test` with Vitest's built-in `junit` reporter, writing to
`test-results/junit.xml` (gitignored) — see the root `TESTING.md`'s
"Dashboard" section.

## Dead code

`knip` is a dev dependency (added 2026-08-24, see `ARCHIVE_DEAD_CODE.md`):

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
| `src/App.interaction.test.tsx` | **Interaction** | `App.tsx` has no exported handlers — its ~10 handlers (`startNewRig`, `selectExistingRig`, `onFileSelected`, `extractCurrent`, `skipCurrent`, `scanStandaloneTicket`, `updatePinWeightPct`, `continueReview`, `updateField`, `acknowledgeDisclaimer`) all read/write one shared `wizard` state object via closures, the same shared-mutable-state shape `test_streamlit_app.py` covers on the Python side via `st.session_state`. Driven through the real rendered UI with `@testing-library/user-event`, not by calling handlers directly (they aren't reachable that way). Five cases: (1) a full happy path — start a new rig, skip all three image steps, reach Results, and confirm both `recentRigs` (localStorage) and `history` (in-memory) updated from the same `continueReview` call; (2) selecting an existing rig jumps straight to the scale step, skipping truck/trailer entirely — the same "skipped a step it shouldn't have" bug shape Android's `RigCheckNavHostTest` caught on 2026-08-18, here as a regression-shaped test written ahead of any bug, not after one; (3) an extraction error clears once the user skips instead of retrying, not left dangling on `wizard.uploadError`; (4) scanning a tow-vehicle-only ticket fills the stand-alone-weight field and hides the now-unnecessary pin-weight slider; (5) the pin-weight slider's value *leaves App.tsx* as the raw 15–25 whole number, unconverted — `./api` is mocked here, so this only proves App passes the number through, not that `api.ts` itself converts it (that's `src/api.test.ts`, below). A `Disclaimer gate` describe block, added for the #57 test audit, drives the same happy path to Results and asserts the gate directly: `ResultsStep`'s content is absent while the modal is still up and `sessionStorage`'s `rigcheck:disclaimerAcknowledged` key isn't yet `'true'`; acknowledging reveals Results and sets the key; and a second test pre-seeds that key before mounting `App` to confirm the modal does not reappear once it was acknowledged earlier in the session (the real claim behind "persists" — `sessionStorage`, unlike component state, survives a fresh mount). |
| `src/api.test.ts` | Function + **Cross-platform interface** | Only `fetch` is mocked, so `api.ts` itself runs for real. `createBreakdown`: request shape (truck/trailer/scale pass through unchanged), success resolves with the parsed body, failure rejects with the server's `detail` message or a generic `Request failed (status)` fallback when the body has no `detail` (or isn't JSON) — plus the **cross-platform interface** case, `pin_weight_pct: pinWeightPct / 100`, paired with `tests/test_api.py`'s `test_breakdown_endpoint_pin_weight_pct_is_a_fraction_not_the_ui_percentage` via the shared `test-vectors/pin_weight_pct_contract.json` fixture (a Python-side and TypeScript-side test both derive their expected numbers from the one file, not two independently hardcoded ones). `extractTruckTag` gets the same success/error coverage (posts `FormData` with the file, to `/api/extract/truck-tag`); `extractTrailerTag`/`extractScaleTicket` only confirm they hit their own distinct endpoint, since they're thin wrappers over the same shared `postFile` helper `extractTruckTag` already exercises fully — a copy-paste bug pointing two of them at the same path is the one thing that actually varies between them. |
| `src/recentRigs.test.ts` | Function | `loadRecentRigs`: empty array when nothing stored, the stored array when valid, empty array (not a throw) on corrupt JSON or a parsed-but-non-array value. `saveRecentRig`: prepends and persists a new rig; replaces (not duplicates) a same-nickname rig case-insensitively, moving it to the front; caps the list at 5, dropping the oldest; still returns the computed list even if `localStorage.setItem` throws (e.g. quota exceeded) — the in-memory return value staying usable even when persistence silently fails is deliberate behavior worth locking down, not an oversight. |
| `src/wizard/UploadStep.test.tsx` | Module | Fake props, no `App`/network involved. Title/instructions render; Extract Data is disabled with no file, enabled with one, and the drop zone's placeholder swaps to the filename; selecting a file calls `onFileSelected`; Extract Data calls `onExtract`; the error message renders when given; the scale module's two extra pieces (the "No CAT scale ticket?" hint and the second "Build Estimated Model" skip button, both wired to `onSkip`, plus the first skip button's label swapping to "No Image / Enter Weight Manually") are present only for the scale module, absent for every other one. |
| `src/wizard/ReviewStep.test.tsx` | Module | Fake props. Each field renders from `data` (blank when missing); typing calls `onFieldChange(name, isNumber, value)`; the continue button (labelled `module.continueLabel`) calls `onContinue`; the error prop renders. The stand-alone-weight scan section: absent for non-truck modules and absent for the truck module when `onScanStandaloneTicket` isn't passed; its pin-weight slider shows only while `standalone_weight_lb` is unknown, hides once it's set (via `rerender`, not a fresh mount, to prove it's the same data change driving both states); the slider's `onChange` reports the numeric value. Scanning a ticket: shows "Reading…" and disables the button while the promise it's given is pending, re-enables once resolved; a rejection surfaces the scan's own local error text, distinct from the `error` prop — complements `App.interaction.test.tsx`'s standalone-scan case, which only exercises the resolved path. |
| `src/wizard/ResultsStep.test.tsx` | Module | Fake props. Verdict headline/subline render; each breakdown item's label, badge, actual/rated weight, and note (present vs. `null`, via `rerender`) render correctly; the estimated-figures notice shows when any item is `estimated`, hidden when none are — the one thing `App.interaction.test.tsx` never exercises, since its `RESULT` fixture is always non-estimated; "Run Another Check"/"Back to Dashboard" call `onRestart`/`onGoHome`. |
| `src/wizard/RigStep.test.tsx` | Module | Fake props. No rig cards when `recentRigs` is empty; each recent rig's nickname and a manufacturer subtitle render when at least one of truck/trailer has one, the subtitle line omitted entirely when neither does; clicking a card calls `onSelectExisting` with that rig; Start New Rig stays disabled for an empty or whitespace-only nickname, enables once typed, and calls `onStartNew` with the **trimmed** nickname — the interface contract a caller (`App.tsx`'s `startNewRig`) relies on to not receive stray whitespace. |
| `src/apiShape.test.ts` | **Cross-platform interface** | "Option B" from the API-shape-drift discussion (see `FUTURE_API_SCHEMA_VALIDATION.md` for the fuller schema-export "Option C" this stops short of). Doesn't touch a real response — proves `BreakdownItem`/`VerdictInfo`, as currently declared in `types.ts`, have exactly the keys `test-vectors/breakdown_response_shape_contract.json` declares. Paired with `tests/test_api.py`'s `test_breakdown_response_matches_the_shared_api_contract`, which is the half that actually calls the real endpoint. TypeScript's excess-property checking on this file's object literals does real work here: add a field to `BreakdownItem` without adding it to the literal and the build fails (missing property) before this test even runs; remove one without removing it from the literal and the build fails too (excess property) — either way a human is forced to touch this file, and its own assertion then forces the shared contract (and the paired Python test) to be updated too. **Kept deliberately (test audit #57, 2026-10-04)** even though ADR-0007 removed `/api/breakdown` from Web's own deployment: Web no longer calls the endpoint this fixture was named for, but the fixture is still the one place `BreakdownItem`/`VerdictInfo`'s shape is pinned across platforms, so retiring this test would drop the only guard against Web's own types drifting from it. See the in-file comment for the full reasoning. |
| `src/auth.test.ts` | Function | `createSupabaseAuthClient` (the one line `App.auth.test.tsx` never reaches, since that suite injects its own fake client directly): returns `null` without calling the SDK when either `VITE_SUPABASE_URL` or `VITE_SUPABASE_PUBLISHABLE_KEY` is unset, and calls the (mocked) `createClient` with both values when present. `@supabase/supabase-js` is mocked and env vars are stubbed explicitly via `vi.stubEnv`, so this never depends on `web/.env.local`'s actual contents. |
| `src/components/DisclaimerModal.test.tsx` | Module | Renders the disclaimer heading; clicking "I Understand — Continue" calls `onAcknowledge`. Deliberately small — this component has exactly one behavior. |
| `src/screens/History.test.tsx`, `src/screens/Dashboard.test.tsx` | Module | Both cover `verdictBadge.ts`'s `VERDICT_BADGE` map (`pass`→"Safe to Tow"/success, `fail`→"Over Limit"/warning, `partial`→"Partially Checked"/insufficient, `insufficient`→"Not Enough Info"/insufficient), which each file's verdict badge now reads from. **Regression tests for a real bug found 2026-08-21** auditing this suite's coverage: both files previously rendered *any* non-`'pass'` verdict as "Over Limit" with a warning badge — a partial or insufficient check (missing data, not an actual over-limit reading) got the same alarming label as a genuine failure. `History.test.tsx` also covers the title/per-entry rendering and, as of the #57 test audit, every filter pill (`All rigs`, a per-rig pill, `Within limits`, `Over limit`) and the "No checks match this filter." empty state — including that a partial or insufficient entry shows under neither `Within limits` nor `Over limit` (current behavior, asserted as such, not necessarily the last word on where those verdicts "should" sort). `Dashboard.test.tsx` now also covers the recent-rigs grid (card contents, the manufacturer-subtitle join, the truck/trailer line each being omitted when that half of the rig has none), the Recent Checks list (two-item cap, its own subtitle join, the "View history" link appearing only once there is a check), and every click target (`Start New Check`, `View History`, a rig card, "New rig") calling its handler. |

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
- ✅ **Closed 2026-10-04** (test audit #57): `History.tsx`'s filter pills
  and empty state, `Dashboard.tsx`'s rig grid/subtitle join/click
  targets, the Disclaimer gate (`Results` withheld until acknowledged,
  the acknowledgement persisting across a fresh `App` mount), and
  `createSupabaseAuthClient` (with and without the Supabase env vars) —
  see `src/screens/History.test.tsx`, `src/screens/Dashboard.test.tsx`,
  the `Disclaimer gate` block in `src/App.interaction.test.tsx`, and the
  new `src/auth.test.ts` above. `apiShape.test.ts` was reviewed and kept
  deliberately rather than removed; see its entry above.
- **Deliberately not tested**: `wizard/ProcessingStep.tsx`,
  `components/StepPills.tsx`, `components/PredictiveEstimateNotice.tsx`,
  and the `design-system/` primitives (`Badge`/`Button`/`Card`) — purely
  presentational, no branching that affects correctness, the same
  judgment call already made not to write a dedicated test for Android's
  parallel `EstimatedFiguresNotice.kt`.
