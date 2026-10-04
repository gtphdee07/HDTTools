# Test audit: Web (`web/`)

Audited 2026-10-04 against `docs/test-audit/rules.md`. Measured facts come from runs on this date (Vitest 4.1.11, Node 24.19.0, Windows); judgement is labelled as such. Nothing live was run: `npm run test:external` and `scripts/external_freshness.py` (which queries the npm registry) were not executed.

## 1. Summary

- Worst gap: the Web External suite covers one surface (`supabase-auth`); the Pages site, the Worker scan call, Web Billing and the Supabase Garage/History tables are untested, and not even listed as `planned` in `scripts/external_manifest/surfaces/` (only `supabase-auth.json` and `revenuecat-rest.json` exist).
- ADR-0008's Web gate (rule 5) does not exist yet: there is no pre-push hook (`.git/hooks` has only `*.sample`, `core.hooksPath` is unset); ticket #43 owns it.
- Offline suite is healthy: 16 files, 107 tests, all pass in about 7 s; statements 91.74 %, branches 87.21 %, functions 88.65 %, lines 95.13 %. Weakest: `History.tsx` 61.5 % statements (filters untested), `auth.tsx` 83 %, `App.tsx` 87.8 %, `UploadStep.tsx` 87.5 %.
- All 14 golden-vector cases run on the TypeScript port with nothing skipped, but the runner only checks rows named in the fixture, not the verdict headline/subline, row notes or badge labels.
- `web/TESTING.md` is stale (says 71 tests, describes `createBreakdown` tests in `api.test.ts` that moved to `breakdown.test.ts`, calls `api.ts` the breakdown client, and has no entry for `breakdown.test.ts`, `App.auth.test.tsx` or `src/external/*`).

## 2. Inventory

All counts from `npm test` (16 files, 107 tests) and the files under `web/src`. Category numbers are those of the root `TESTING.md`. Judgement on categorisation is mine; `web/TESTING.md` does not classify the newer files.

| Cat | Files | Tests | Notes |
|---|---|---|---|
| 1 Function | `src/breakdown.test.ts` (golden vectors 14 + `createBreakdown` 4 = 18), `src/api.test.ts` (4), `src/recentRigs.test.ts`, `src/external/config.test.ts` (3), `src/App.smoke.test.tsx` (harness check) | | `breakdown.ts` is a pure module, so this file is also its Module test (cat 3). |
| 2 Interaction | `src/App.interaction.test.tsx` (5), `src/App.auth.test.tsx` (8) | 13 | Real rendered UI via user-event; `./api` mocked in the first, a fake `AuthClient` in the second. |
| 3 Module | `wizard/UploadStep`, `ReviewStep`, `ResultsStep`, `RigStep`, `components/DisclaimerModal`, `screens/Dashboard`, `screens/History` tests | | Fake props, no App. |
| 4 Inter-module / cross-platform | `src/apiShape.test.ts` (2, key list vs `breakdown_response_shape_contract.json`), the golden-vector block and the pin-percent case in `breakdown.test.ts` (fixtures `breakdown_cases.json`, `pin_weight_pct_contract.json`), `src/external/externalGuards.test.ts` (static guards) | | See section 6 about `apiShape.test.ts`. |
| 5 External | `src/external/supabaseAuth.external.test.ts` (7 tests, tag `[supabase-auth]`) | 7 | Not run here. |

Per-file test counts were not individually measured beyond the totals above; the counts in the table come from reading `it(` calls.

How each group is run (all from `web/`):

- Whole offline suite (Minor and Major are not separated, as `web/TESTING.md` admits): `npm test` (`vitest run`). Measured 6.75 s Vitest duration, 8 s wall. Needs no network, no secrets, no device.
- One file: `npx vitest run src/wizard/RigStep.test.tsx` (standard Vitest; not documented in `web/TESTING.md`).
- Coverage: `npm run test:coverage`, 7.3 s Vitest duration, 9 s wall. Writes gitignored `web/coverage/` (the only artefact this audit created, outside the report).
- JUnit report: `npm run test:report` (not run here).
- Typecheck including tests: `npm run build` (not run here, it writes `dist/`).
- Lint and dead code: `npm run lint` (oxlint), `npm run check:dead-code` (knip); not run.
- External: `npm run test:external` or `web/test-external.ps1` (needs network, `web/.env.local` with four variables, a pre-made Supabase test user; free, `max_paid_calls: 0`). Not run.

## 3. Code coverage

Measured by `npm run test:coverage` (v8 provider, text and json-summary reporters), 2026-10-04:

| Metric | Value |
|---|---|
| Statements | 91.74 % (400/436) |
| Branches | 87.21 % (307/352) |
| Functions | 88.65 % (125/141) |
| Lines | 95.13 % (352/370) |

The text table hides fully covered files; `web/coverage/coverage-summary.json` lists them. Files below 100 % statements:

| File | Stmts | Branch | Funcs | Lines | Uncovered lines |
|---|---|---|---|---|---|
| `src/screens/History.tsx` | 61.53 | 63.15 | 58.33 | 68.42 | 24-26, 52, 60-63 |
| `src/auth.tsx` | 83.01 | 64.28 | 87.5 | 90.47 | 78-81 |
| `src/wizard/UploadStep.tsx` | 87.5 | 92.85 | 75 | 85.71 | 76 |
| `src/App.tsx` | 87.75 | 79.51 | 82.35 | 91.89 | several, incl. 168-169, 227 |
| `src/api.ts` | 91.66 | 100 | 80 | 100 | none (one function) |
| `src/wizard/ReviewStep.tsx` | 91.66 | 86.36 | 85.71 | 95.45 | 101 |
| `src/screens/Account.tsx` | 98.27 | 95 | 100 | 100 | 66, 91 |
| `src/screens/Dashboard.tsx` | 100 | 91.66 | 100 | 100 | branch at 162 |
| `src/components/Header.tsx`, `design-system/Button.tsx` | 100 | 85.7 / 80 | 100 | 100 | branches only |

All other files, including `breakdown.ts`, `recentRigs.ts`, `verdictBadge.ts`, `ResultsStep.tsx`, `RigStep.tsx`, `ProcessingStep.tsx` and `StepPills.tsx`, are at 100 % statements.

Gaps of consequence:

- `History.tsx` lines 24-26 and 60-63: the filter pills (All rigs, per-rig, Within limits, Over limit) and the empty state are never exercised. The filter logic maps `pass` to "Within limits" and only `fail` to "Over limit", so partial and insufficient verdicts appear under neither filter; no test states whether that is intended.
- `auth.tsx` lines 78-81: `createSupabaseAuthClient` (the env-var read and `createClient` call that wires production). Only the injected fake client is tested, so a missing or misnamed `VITE_SUPABASE_*` variable is invisible offline; this is what ticket #42's baked-in-env check is for.
- Coverage counts only files that are imported by a test. Vitest's default `coverage.include` is not set, so a file no test imports (for example `main.tsx`) would not appear at all; `main.tsx` (15 lines) is absent from the summary. Setting `coverage.include: ['src/**']` would reveal such files.
- Coverage is report-only for Web in `scripts/coverage_gate.py` (`get_web_result`), consistent with rule 9.

## 4. Feature coverage

Features are taken from `web/CONTEXT.md`, issue #15 (stories 1, 2, 3, 6, 7, 8, 40-45) and the Web tickets. "Open" tickets are features not built yet.

| Feature | Test that verifies it | Judgement |
|---|---|---|
| Wizard flow: pick or create Rig, steps 1-3, Results | `App.interaction.test.tsx` (full happy path, existing-rig jump to step 3, error-then-skip, standalone scan, pin slider); step components by `UploadStep/ReviewStep/RigStep/ResultsStep.test.tsx` | Good. No test for going Back mid-wizard, or for `finalizing` failing (the `catch` in `continueReview`, `App.tsx` ~line 127, is part of the uncovered App branches). |
| Rig / Garage (save, recall, 5-rig cap, same-nickname replace) | `recentRigs.test.ts`; `RigStep.test.tsx`; saved-rig assertion in `App.interaction.test.tsx` | Device-local only. Synced Garage (#28) not built. |
| History | `History.test.tsx` (labels, rendering); recorded in `App.interaction.test.tsx` | In-memory only (`useState` in `App.tsx`), not persisted at all; filters untested. Synced History (#29) not built. |
| Dashboard | `Dashboard.test.tsx` (verdict labels only) plus indirect coverage | Rig grid, subtitle join, "Add a new rig" and Run Check targets lack a dedicated test (acknowledged in `web/TESTING.md`); statement coverage is 100 %, so they are exercised indirectly. |
| Sign-in, sign-up, sign-out, password reset, recovery link, unconfigured state, free flow without account (story 1, 3, 7, 8) | `App.auth.test.tsx` (8 tests) | Good at the fake-client level; live contract in the External suite. Google/Apple (#20) not built. |
| Disclaimer gate (story 41) | `DisclaimerModal.test.tsx` (renders, acknowledge); gate behaviour in `App.interaction.test.tsx` happy path | Whether Results is withheld until acknowledgement, and that it persists for the session (`sessionStorage`), is only touched indirectly; I did not find an assertion that Results is hidden before acknowledging. |
| Scan flow (upload, processing, review, error, standalone-weight scan) | `UploadStep`, `ReviewStep` tests; `api.test.ts`; `App.interaction.test.tsx` | `api.ts` posts to same-origin `/api/extract/*` with no auth token and the Worker has no matching route, so the real scan path to the shared Worker does not exist yet (#26, #21). Tests pin the current paths, so they will need to change with #26. |
| Breakdown math in TypeScript (stories 42-45) | `breakdown.test.ts`: 14/14 golden cases, including rounding edges `rounding_half_way_values_round_up` and `rounding_half_way_predictive_truck_estimate`, all run with none skipped | Good. Web has its own tests for: local compute with no fetch, date stamp format, pin percent conversion, NaN treated as missing. Not covered by Web-specific tests: the verdict headline and subline wording, `note` text, `badgeLabel`, `barColor`, and the combinatorial sweep Python has (`tests/test_breakdown_combinatorial_sweep.py`). |
| Free offline calculator (story 2) | `breakdown.test.ts` asserts no `fetch` call | No service-worker or offline test; the claim "works offline" rests on there being no network call. |
| Buy Pro / packs, balance, Web Billing checkout, cancel and reopen (#24, #25, #11) | none | Not built. |
| Pro and Scan Credit balance across platforms (#27), Pro caps (#30) | none | Not built. |
| GCWR field and Combined Rig Weight change (#46) | none | Not built; its acceptance needs the fixture and Web interaction tests. |

## 5. Interface coverage

### Our interfaces

| Interface | Test | Notes |
|---|---|---|
| `breakdown.ts` public surface (`computeBreakdown`, `verdictFor`, `createBreakdown`) | `breakdown.test.ts` | `createBreakdown` is called from `App.tsx` with the UI whole-number percent. |
| `test-vectors/breakdown_cases.json` (shared golden vectors) | `breakdown.test.ts` golden block | All 14 cases run. The runner only iterates the fixture's expected items; extra rows the port produced would pass, and `verdict_status` is the only verdict field compared. |
| `test-vectors/pin_weight_pct_contract.json` | `breakdown.test.ts` "converts the UI whole-number pin weight..." | Moved here from `api.test.ts` when the API call was removed; `web/TESTING.md` still says `api.test.ts`. |
| `test-vectors/breakdown_response_shape_contract.json` | `apiShape.test.ts` | See section 6. |
| `api.ts` extract endpoints (our Worker or old backend) | `api.test.ts` | Mocks `fetch`; asserts three paths and the error message contract. `TruckTagOut`, `TrailerTagOut`, `ScaleTicketOut` shapes have no contract test (acknowledged in `web/TESTING.md`). |
| `AuthClient` slice of Supabase (`auth.tsx`) | `App.auth.test.tsx` fake, `supabaseAuth.external.test.ts` real | The slice is deliberately narrow so the fake is faithful to what is called. |
| `recentRigs.ts` (localStorage schema `RecentRig`) | `recentRigs.test.ts` | No test for loading a stored Rig from an older shape; #46 will need one. |
| Component props (`UploadStep`, `ReviewStep`, `ResultsStep`, `RigStep`, `DisclaimerModal`, `History`, `Dashboard`) | their module tests | `Account`, `Header`, `Footer` have no dedicated module test (covered via `App.auth.test.tsx` and indirectly). |

### Their interfaces

| Third party | Web touches it via | Test | Watched in `scripts/external_manifest/`? |
|---|---|---|---|
| Supabase Auth | `auth.tsx` | `[supabase-auth]` External suite, 7 tests: URL and key accepted, sign-in session shape and JWT, bad password and unknown email errors, sign-in/get-user/sign-out journey, malformed sign-up and reset rejected before any mail. Last recorded pass 2026-10-04T04:32:26Z at commit `2aa05b6`, supabase-js 2.117.2. | Yes: `supabase-auth.json`; boundary `web/src/auth.tsx`; pins `web/package.json`, `web/package-lock.json`; watches npm `@supabase/supabase-js`. |
| Supabase tables (Garage, History) | not built (#28, #29) | none | No manifest entry, not even `planned`. |
| Cloudflare Pages site (deployed) | `web/wrangler.toml`, `web/dist` | none (#42 open) | No manifest entry. |
| Shared scan Worker (deployed) | `api.ts` | none from Web; Worker's own suites cover its side | No manifest entry for the Worker-to-Web path (the `revenuecat-rest` surface lists platforms `scan-proxy`, `android`, not `web`). |
| RevenueCat Web Billing (`@revenuecat/purchases-js`) | not built (#24, #25, #11) | none | No manifest entry. |
| Google, Apple sign-in via Supabase (#20) | not built | none | No entry. |

`web/src/external/` guards that `npm test` enforces (`externalGuards.test.ts`, `config.test.ts`): external files are excluded by the default `vite.config.ts` exclude list; sign-up and reset calls may only use the malformed-address constant; no `signInWithOtp`, `resend`, `admin` or `/auth/v1/(signup|recover|otp|magiclink|invite)` anywhere; no `console.`/`.log(` calls and no password or key on an asserting or erroring line; `readConfig` names missing variables only, never values, and a missing credential throws. These are static text checks, so they are stronger as documentation of intent than as proof (a renamed constant, or a helper that wraps `signUp`, could slip past).

## 6. Spec check

- **ADR-0007 / issue #15 story 44-45 (fixture is the source of truth, rounding cases)**: met. Rounding cases are in the fixture and run on the port. The fixture `_readme` still says "the coming TypeScript port" and describes `predictive_truck_estimate` as unsupported by Kotlin; the text lags behind (documentation, not a test defect).
- **ADR-0007 consequence "`api.ts` loses its `/api/breakdown` call and its hardcoded localhost base URL"**: met. `api.ts` has no breakdown call; the base URL comes from `VITE_API_BASE_URL` and defaults to same-origin. The tests contradict nothing here.
- **`apiShape.test.ts` lags**: it still asserts `types.ts` against `breakdown_response_shape_contract.json`, whose other half is the Python `/api/breakdown` response (`tests/test_api.py`). With the endpoint no longer part of Web's deployment, the contract it guards is between types and a response nobody on Web calls. It still stops `BreakdownItem` and `VerdictInfo` drifting from the shared shape (which Android also mirrors), so keep or retire it deliberately; judgement, not a stated requirement.
- **`web/TESTING.md` lags**: states 71 tests (now 107), names `api.test.ts` as holding `createBreakdown` tests, omits `breakdown.test.ts`, `App.auth.test.tsx`, `externalGuards.test.ts` and `config.test.ts` from its by-file table, quotes 91.41 % coverage (now 91.74 %), and the root `TESTING.md` says Web "has no real External suite", which is no longer true.
- **Root `TESTING.md` "Web ... no release event"**: ADR-0008 and issue #35 define one (a push to `MPSkills` that touches `web/`), but the hook is not installed, so Web remains effectively ungated.
- **Issue #15 story 2 (works offline)**: asserted only by "no `fetch` call"; nothing tests offline behaviour of the built site.
- **Issue #15 story 41 (Disclaimer gate remains)**: covered mostly indirectly (see section 4).
- **Issue #15 stories 15-20 (caps, idempotency, concurrency)** and **#26-#30**: not built, so no tests exist or are expected yet; their acceptance criteria name Web interaction tests as the seam, and the current interaction-test harness (fake `AuthClient`, mocked `./api`) can host them.
- **Issue #46 (GCWR)**: the existing `recentRigs` tests, `ReviewStep` fields and `breakdown.test.ts` will all need extending; `breakdown.ts` already has golden-vector plumbing that will pick up new cases from the fixture automatically.
- **Tests exceeding the spec**: `App.interaction.test.tsx` case 2 (existing rig skips truck/trailer) and the `verdictBadge` regression tests are extra guards not stated in a spec; reasonable.

## 7. Rule fit

1. **Scope ladder (file, context, application).** File level: `npx vitest run <path>` works, and `vitest related <source file>` is available in Vitest but not wired or documented. Context level: `npm test` runs the whole Web context, about 8 s. Application level: no command runs all contexts; `scripts/coverage_gate.py` runs all four platforms' coverage, but is a release-time gate, not a test ladder. The ladder is therefore usable for Web, but only the context step is documented.
2. **Per issue.** A targeted test can be run by file name. Minor versus Major cannot be separated: no tagging exists, so "the module's Minor suite always; Major when the interface changed" collapses to "run `npm test`" (cheap enough that this is acceptable; `web/TESTING.md` says as much). There is no manifest mapping a source file to its test files, so the "inter-module tests for every module that shares a changed interface" step is a human judgement; mapping hints in this report: `types.ts` shared by all, `apiShape.test.ts` and `breakdown.test.ts` for the shared fixtures. The External step works only for `auth.tsx` (via `external_freshness.py`).
3. **Session end.** Running the whole context takes about 8 s with no prerequisites, so it is easy to support. No blockers on Web. (Typecheck via `npm run build` is a separate step; tests are typechecked there, not by `vitest`.)
4. **Release.** The rule says Web, Streamlit and Core have no full-run release. That matches reality: nothing but the Pages push exists.
5. **Web gate.** Not supported today. The freshness script and the per-surface recorder exist (`scripts/external_freshness.py`, `scripts/record_external_result.py`, `scripts/external_wrapper.py`, with tests in `tests/test_external_freshness.py` etc.), and `web/test-external.ps1` runs only stale surfaces. Missing: the pre-push hook (#43), a "web" platform chain that includes surfaces beyond `supabase-auth` (currently `--platform web` yields exactly one surface), and the planned surfaces so that gaps show on the dashboard (#44). The hook would also need to tolerate the one-surface chain until the others exist, per ADR-0008 ("planned never blocks").

## 8. Incremental complexity

Cheapest to most expensive for Web:

| # | Step | Command (from `web/`) | Rough time | Needs |
|---|---|---|---|---|
| 1 | One test file | `npx vitest run <file>` | 1-3 s | nothing |
| 2 | Related tests for a changed source file | `npx vitest related <src file>` (not documented, not tried) | a few s | nothing |
| 3 | Static checks | `npm run lint`; `npm run check:dead-code` | not measured | nothing |
| 4 | Whole offline suite | `npm test` | 7-8 s measured | nothing |
| 5 | Offline suite with coverage | `npm run test:coverage` | 9 s measured | nothing |
| 6 | Typecheck and production build | `npm run build` | not measured | nothing; writes `dist/` |
| 7 | Freshness check | `uv run scripts/external_freshness.py --platform web` | seconds | reaches npm registry; not run here |
| 8 | External, stale surfaces only | `.\test-external.ps1` | tens of seconds (30 s test timeout each) | network, `web/.env.local`, Supabase test user; free; records a result |
| 9 | External, all Web surfaces | `npm run test:external` | as above | same |
| 10 | Cross-platform coverage report | `uv run scripts/coverage_gate.py` | minutes (runs Android JaCoCo) | Android tooling; includes Web as report-only |

Steps beyond these (live Pages, Worker, Web Billing) do not exist yet.

## 9. Gaps and suggested tickets

Suggestions only; no issues were created or edited.

1. **Register the missing Web surfaces as `planned` in the manifest** (`pages-site`, `scan-proxy-worker` Web path, `supabase-tables`, `revenuecat-web-billing`), each with its watched packages; section 5, rule 7 and ADR-0008. Small. Note the dependency chain for `--platform web`.
2. **Watch more packages for the "their side changed" check**; rule 7. Today only `@supabase/supabase-js` is watched. Candidates: `@revenuecat/purchases-js` (when added, #24), `wrangler`/Cloudflare Pages build tooling (the Pages site surface, #42), the Supabase packages beyond `supabase-js` if installed separately, and the Cloudflare platform itself has no npm signal. `react`, `react-dom` and `vite` are build dependencies that change the bundle but not a provider interface, so I would leave them unwatched; `lucide-react` has no remote interface. Small.
3. **Install and verify the pre-push hook for Web** (rule 5, #43). Medium; already ticketed.
4. **Add History filter tests** (Within limits, Over limit, per-rig, empty state) and decide where partial and insufficient verdicts belong under the filters; section 3. Small.
5. **Test `createSupabaseAuthClient` with and without env vars**, or cover it through the Pages-site External test (#42); section 3. Small.
6. **Strengthen the golden-vector runner**: also compare the verdict headline and subline, and fail on rows not in the fixture, if the fixture carries them; section 5. Small to medium (fixture change touches all three platforms).
7. **Add an explicit Disclaimer gate test in `App`** (Results withheld until acknowledged, acknowledgement persists across a restart within the session); section 4. Small.
8. **Add a dedicated Dashboard module test** for rig grid, subtitle join and the entry-point clicks; section 4. Small.
9. **Add a TypeScript sweep test mirroring `test_breakdown_combinatorial_sweep.py`** (never crash, ranges valid) for the port; section 4. Small.
10. **Bring `web/TESTING.md` and root `TESTING.md` up to date** (counts, new files, External suite exists, pin-percent test location, `apiShape` rationale); section 6. Small.
11. **Add `coverage.include: ['src/**']`** so unimported files appear in the coverage report; section 3. Small.
12. **Document the file-level and "related" commands** and a source-to-tests map for rule 1 and 2; section 7. Small.
13. **Decide the fate of `apiShape.test.ts`** now that Web does not call `/api/breakdown`; section 6. Small.
14. **For future feature tickets (#24-#30, #46), write Web interaction tests and External surfaces as part of each ticket's acceptance**, as ADR-0008 says; note #46 needs `recentRigs` backward-compatibility and `ReviewStep` field tests. Per ticket.
15. **Deployed Pages-site External suite and the Worker scan-call suite** (#42 and the Web half of #41), including that the production bundle has the Supabase variables baked in. Medium; already ticketed.
