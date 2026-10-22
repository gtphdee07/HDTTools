# Web (React) testing

Classifies `web/`'s test suite against the categories defined in the
root `TESTING.md`. Written 2026-08-21, the same day the harness itself
(Vitest + React Testing Library) was installed — this is the first test
suite this package has ever had. See `ARCHIVE_TESTING.md` and
`ARCHIVE_WEB_STREAMLIT.md` (repo root) for the narrative history.

`npm test` (`vitest run`) — real run, 2026-10-21 (#64): **34 files, 550 tests: 547
passed, 3 skipped, 0 failed**, in about 23 s (Vitest's own duration; `npm --prefix web test`
from the repo root). The 3 skipped are `src/scanOutcomes.test.ts` declining to check
"Try again" on the 3 rows of the shared `test-vectors/scan_outcomes.json` fixture whose
trigger is a delivered Scan: a notice has no buttons (`App.scanNotice.test.tsx` covers
that screen). No fixture field is pending for Web today, so nothing else is skipped.
`npm run build` (`tsc -b && vite build`) typechecks `src/**`, test files
included, since `tsconfig.app.json`'s `include` is just `["src"]`.

**What to run, and when,** follows the agreed rules in
[`docs/test-audit/rules.md`](../docs/test-audit/rules.md) (scope ladder, per issue,
session end, release); the advisory planner
[`scripts/test_planner.py`](../scripts/test_planner.py) prints the commands for a diff
(`uv run scripts/test_planner.py --level issue|session|release`; it never blocks). The
root [`TESTING.md`](../TESTING.md) has the ladder for all five contexts and the
categories this file's tables use.

## Running tests

| Level | Command |
|---|---|
| One file (per issue, the targeted test first) | `npm test -- src/breakdown.test.ts` (run from `web/`), or `npm --prefix web test -- src/breakdown.test.ts` from the repo root |
| Minor and Major (per issue) | `npm test`: this suite has no Minor subset, so Minor and Major are the same run (see below) |
| Whole context (offline), session end | `npm test` |
| Type check and build | `npm run build` (`tsc -b && vite build`) |
| Coverage | `npm run test:coverage` |
| Dead code | `npm run check:dead-code` |
| Lint | `npm run lint` (oxlint); warnings are judged against an allow-list by the session-end command below |
| Static checks, session end (#150) | `uv run scripts/static_checks.py web` (from the repo root): `tsc -b`, oxlint, knip. Offline, exits 0 only when all three pass |
| Release | none: Web has no full-run release. A push to `MPSkills` that touches `web/` is guarded by the External release gate (`scripts/external_gate.py`, run by `.githooks/pre-push`; `uv run scripts/external_freshness.py --platform web` shows what it would block on) and nothing else |
| External, stale surfaces only (live, free) | `web\test-external.ps1` (see below) |

The one-file command is a Vitest path filter, not an exact match — a less
specific path can select more than one file.

Neither of the first three reaches a live provider: `vite.config.ts` excludes
`*.external.test.ts`, which only `npm run test:external` runs. A command
check (`tests/test_context_test_commands.py`, #52) confirms both commands
select the intended files and never an external one.

## Event-based tiers

Per the root `TESTING.md`'s Minor/Major/External model (retired
2026-08-24 — full narrative in `ARCHIVE_TESTING.md`): this suite has never tagged a fast subset,
so today a full `npm test` run covers both **Minor** and **Major**
undifferentiated — documented honestly here rather than inventing a
split that doesn't exist. The planner agrees: its Web context runs
`npm --prefix web test` for both, narrowed to the one changed file when the diff is
small (`npm --prefix web test -- <file>`). Which test files a given
change calls for (Minor vs. Major, per the root file's
regression-scoping rules) is still a judgment call against
the real diff, same as any other context. `npm test` runs no live
call: every network call is faked (`api.test.ts` fakes `fetch`; the scan tests in `App.scan.test.tsx` use a fake Scan service, and `App.interaction.test.tsx` mocks `./api`), and
`vite.config.ts` excludes `*.external.test.ts`.

## External suite (ADR-0008)

`npm run test:external` runs `src/external/*.external.test.ts` against the
live providers via `vitest.external.config.ts`. Four surfaces today, each
tagged `[surface]` in its describe title; credentials come from the
gitignored `web/.env.local` and a missing one fails the run, never skips
it. Normally run through `web/test-external.ps1`, which runs only the
surfaces `scripts/external_freshness.py` reports stale and records each
result with `scripts/record_external_result.py` (`-Skip` records
`skipped`, which leaves the surface stale). Each surface is recorded from
its own `[surface]` tests, not the run's exit code (#89): the wrapper sets
`EXTERNAL_RESULTS_FILE` and `vitest.external.config.ts` then also writes
JUnit XML there; a surface passes only if none of its tests failed and at
least one passed. Add a surface by adding
`scripts/external_manifest/surfaces/<name>.json` and a
`<name>.external.test.ts` whose describe title carries `[<name>]`.

| Surface | Test file | Paid calls |
|---|---|---|
| `supabase-auth` | `supabaseAuth.external.test.ts` | 0 |
| `pages-site` | `pagesSite.external.test.ts` | 0 |
| `supabase-tables` | `supabaseTables.external.test.ts` | 0 |
| `revenuecat-web-billing` | `revenueCatWebBilling.external.test.ts` | 0 |

All are free, so the wrapper runs them without a confirmation prompt.
`externalGuards.test.ts` (in `npm test`) statically guards every file: never
collected by `npm test`, never create a user or send mail, never start a
purchase, never print a secret, and the Pages file only issues GETs and never
signs in.

**Credential scope (security audit, 2026-10-05).** The Pages journey runs
the live site's JS bundle inside its test worker (the entry script and the chunks it
imports, imported as real ES modules by `bundleLoader.ts`), and
vitest gives a worker the project's `test.env`. So `vitest.external.config.ts`
runs the Pages test as its own `pages-site` project with only the
`VITE_SUPABASE_` variables; every other external test (including any new one)
stays in the default `external` project, which also gets the `WEB_EXTERNAL_`
test-account credentials. The Pages test also scrubs any inherited
`WEB_EXTERNAL_*` variable from its `process.env`, and refuses to fetch a script
that the shell names on another origin. `externalGuards.test.ts` checks the
config split and both safeguards. This is defence in depth, not a sandbox:
`jsdom` and an in-process module import are not a security boundary, so a compromised deployed site
could still run code as the developer; the fix is that the test-account password
is no longer in that process.

### `supabase-auth`

Real calls to the live Supabase project with the test user from
`scripts/wizard_web_external_test_user.sh`. It never creates a user or sends
mail. Since #74 the surface's manifest entry also lists Android's Supabase
pieces (`SupabaseAccountBackend.kt` and the `supabase-kt` pin in
`android/gradle/libs.versions.toml`) and the `android` platform, so a change
there makes it stale and Android's release gate waits on it; only this Web suite
exercises it live.

### `supabase-tables` (#28, #29)

Real calls to the live Supabase project's Garage table (`garage_rigs`) and its
`add_rig` function (#28), and its History table (`history_entries`) and its
`add_history_entry` function (#29), as the two throwaway test accounts
(`WEB_EXTERNAL_TEST_*` and `WEB_EXTERNAL_TEST_NOCREDITS_*`; the second exists to
prove one account cannot reach another's rows). Boundary files are
`web/src/supabaseGarage.ts`, `web/src/supabaseHistory.ts` and the migrations
`supabase/migrations/20261010000000_garage_rigs.sql` and
`supabase/migrations/20261022000000_history_entries.sql`; the watched package is
`@supabase/supabase-js`. **Both migrations must be applied to the project
first** (`docs/BUILD_AND_DEPLOY.md`, Supabase section); until they are, the
matching half of the suite fails at its first call with a message saying so. The
Garage half empties both accounts' Garages before and after every run, so it must
only ever use throwaway accounts. An account cannot delete its own History, so
the History half instead fills an account's History to its cap with its own
checks before each test (which pushes everything older out) and leaves the last 10
checks behind. It never creates a user or sends mail.

| ADR-0008 depth | Covered by |
|---|---|
| Reachable and authenticated | The table and `add_rig` answer a signed-in account and refuse a signed-out caller. |
| Response shape | `add_rig` returns the Rig row (`id`, `nickname`, `truck`, `trailer`, `last_used_at`). |
| Error contract | Over the cap the server answers `garage_full` with the cap in `details`; a direct insert, a change of owner, and another account's update or delete are refused or touch nothing. |
| Full journey | Fills a Garage to the Free cap, is refused the next add, races eight adds from two sessions of one account into the last free slot (exactly one lands), retries an add (one Rig, even once full), updates a Rig in a full Garage, and frees a slot by deleting. |
| History (#29) | `add_history_entry` returns the entry row (`id`, `rig_nickname`, `verdict`, `checked_at`); an account sees only its own checks; a signed-out caller, a direct insert, and any edit or delete (own or another's) are refused; an add past the cap of 10 drops the oldest and the list reads newest first; eight checks arriving at once from two sessions of one account leave exactly 10; a retried add (same key) creates one entry and does not push another out. |

The offline counterparts are `src/garageSchema.test.ts` and
`src/historySchema.test.ts` (in `npm test`): each runs its migration on a real
Postgres (PGlite) as the `authenticated` role and checks row-level security,
grants, the cap and idempotency. They cannot run two transactions at once, which
is why the concurrent-add checks live here.

### `revenuecat-web-billing` (#85)

Real calls to RevenueCat Web Billing through the real `@revenuecat/purchases-js`
SDK, reads only. The one boundary file is `web/src/revenueCatBilling.ts` (the
adapter over the SDK); pins are `web/package.json` and `web/package-lock.json`;
the watched registry package is `@revenuecat/purchases-js`. `web/src/billing.tsx`
(the React provider and the two-line factory that builds the client) is
deliberately not a boundary file: the live test does not exercise it, and
provider edits would otherwise mark the surface stale. Needs `VITE_REVENUECAT_WEB_PUBLIC_API_KEY`
and `VITE_REVENUECAT_WEB_OFFERING_ID` (the same values the site is built with,
public by design) and the `WEB_EXTERNAL_TEST_*` account in `web/.env.local`. The
account's Supabase user id is the RevenueCat app user id, as on the site. **The
RevenueCat dashboard must be configured first** (`scripts/wizard_web_revenuecat_dashboard.sh`):
the offering with a lifetime package backed by a Web Billing product, the `pro`
entitlement, and the `SCAN` virtual currency, plus the Pro fixture customer
`external-suite-pro` holding `pro` (below). A missing piece fails the run with
a message naming it.

No purchase is ever made (0 paid calls; `externalGuards.test.ts` rejects any
`purchase` call in an external file): a sandbox purchase stays the human
checklist in #11. The test account may or may not be Pro, so the tests that use it
check shapes and agreement between the client and the raw SDK, never `isPro`'s
value; `isPro` is asserted only on the two fixture users, `external-suite-pro`
(Pro, below) and `external-suite-no-purchases` (free). Unlike the other suites,
the "unknown user" case is not an error here:
RevenueCat creates a customer on first sight, so an unseen app user id is a free
customer with no scans, and the test uses one fixed id
(`external-suite-no-purchases`) so it creates a single customer, not one per run.

**The Pro fixture (#105).** `external-suite-pro` is a RevenueCat customer that was
granted the `pro` entitlement by hand as a promotional, non-expiring grant, so
the suite can prove that an entitlement named exactly `pro` exists in the project.
The dashboard cannot create a customer, so `npm run fixture:revenuecat-pro-user`
(`web/scripts/createRevenueCatFixtureUser.mjs`, run from `web/`) creates it with
the sandbox public key and then reports its active entitlements; the grant itself
is the dashboard step in `scripts/wizard_web_revenuecat_dashboard.sh`. If the
fixture is missing or the grant lapses, the Pro test fails with a message saying
to grant it, which is a setup fault, not a code bug. What this does not prove: that
the Pro *product* is attached to the entitlement, because a promotional grant
works without it and seeing the attachment needs a purchase or the REST API's
secret key (neither is allowed in this project). The attachment is checked where a
secret already lives, by the Worker's `[revenuecat-rest]` External tests (#146):
they read the project configuration with a read-only key and fail if `pro` is
missing, has no product, or lacks the product this site's paywall sells (see
`workers/scan-proxy/TESTING.md`). A real sandbox purchase stays the human checklist
in #11. `createRevenueCatFixtureUser.mjs` is a setup helper, not
a boundary file: it is not run by the suite, and `web/package.json` (which holds its
npm script) is already a pin of this surface.

| ADR-0008 depth | Covered by |
|---|---|
| Reachable and authenticated | The Web public API key is accepted and `getOfferings` returns the configured offering. |
| Response shape | The offering has a lifetime package backed by a non-consumable Web Billing product with a formatted price; every package has an identifier, and every Web Billing product a title, a known product type and a price. Customer info has an `entitlements.active` map; the `SCAN` virtual currency exists with an integer balance of 0 or more. These are the exact fields `getProOffer`, `getScanPacks` and `getStatus` read. |
| Error contract | A well-formed key the server never issued is rejected with `InvalidCredentialsError`. An app user with no purchases is a free customer with a zero balance, not an error. (A malformed key or user id is rejected by the SDK locally, so it says nothing about the server.) |
| Full journey | Identifies the test account through the real `createRevenueCatBillingClient`, reads the Pro offer, status and scan packs, checks the client agrees with the raw SDK about the `pro` entitlement, then switches the same instance to another user and gets a free customer with no scans. |
| Pro entitlement | The fixture user `external-suite-pro` holds an active `pro` entitlement in the raw SDK, and the real client reads it as `isPro === true`. A missing or misnamed entitlement fails this. |

**Review of existing external tests against the four depths:** none existed for
this surface, so all four were filled.

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
| Full journey | Loads the shell, runs the live production bundle (a code-split build: entry script plus the chunks it imports, as ES modules) in jsdom, clicks the header's "Sign in", and sees the email and password fields, with no "Accounts unavailable" card (what a build without the Supabase variables shows). It never submits the form. |

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

**Supabase dashboard settings the sign-up flow depends on** (not code, so no
test sees them; checked by hand on 2026-10-09, #78): Authentication → URL
Configuration → **Site URL** is `https://rigcheck-web.pages.dev`. The
sign-up confirmation email's link ends there, so a Web or Android sign-up
lands on the live app instead of `http://localhost:3000` (the default, which
shows "refused to connect"). Redirect URLs also allow
`https://rigcheck-web.pages.dev/**` (password-reset emails from Web and
Android redirect to the site root) plus `http://localhost:5173/**` and the
Pages preview hosts. Web signs in with the PKCE flow (#95), so a confirmation or
reset link only signs in the browser that asked for it: opened elsewhere it lands
with `?code=` and the Account screen explains that instead. If a confirmation link ever lands on `localhost` again,
this setting was reset. Google sign-in is enabled under Authentication →
Providers (Android's Google flow, #22); Apple is not, until #77.

## Coverage

Real coverage, wired up 2026-08-24 (see `ARCHIVE_TESTING.md`) via
`@vitest/coverage-v8`:

```bash
npm run test:coverage
```

(`vitest run --coverage`, configured in `vite.config.ts`'s `test.coverage`
block — `provider: 'v8'`, `reporter: ['text', 'json-summary']`, so the
machine-readable total lands at `coverage/coverage-summary.json`.) Real numbers,
2026-10-21 (`uv run scripts/coverage_gate.py --refresh`): **95.95% of statements**
(1,376 of 1,434), 92.96% of branches, 94.08% of functions, 97.69% of lines. The
weakest files: `src/main.tsx` 0% (5 statements; the Vite entry point, deliberately
not imported by any test, and what `coverage.include` below exists to show),
`src/supabaseGarage.ts` 73%, `src/wizard/UploadStep.tsx` 88%, `src/scanImage.ts` 90%,
`src/App.tsx` 92%, `src/garageImport.ts` 94%, `src/billing.tsx` 95%.
`scripts/coverage_gate.py` reports this number **report-only**, not enforced: Web
has a release event now (a push of `MPSkills` that touches `web/` deploys it to
Cloudflare Pages, guarded by the External release gate), but no floor has been set,
and rule 9 of `docs/test-audit/rules.md` leaves the number to the owner. The
script's own "not gated — no release event yet" note is out of date. See the root
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

## Static checks (#150)

Nothing used to run Web's typecheck, lint or dead-code checks except `npm run build`
(which typechecks) before a deploy; they sat green or red unseen. They are now one command,
`uv run scripts/static_checks.py web`, listed by the test planner at session level when a
file under `web/` changes (never for a docs-only change), run and recorded against the tree
by `/ticket-finish`. Steps, in order, every one run even after a failure; exit 0 only when
all pass:

| Step | Command it wraps | Covers | Fails on |
|---|---|---|---|
| typecheck | `tsc -b` | `src/`, `vite.config.ts`, `vitest.external.config.ts` and (since #150, `checkJs`) `scripts/*.mjs` | any error |
| oxlint | `oxlint -f json .` from `web/` | every `.ts`, `.tsx` and `.mjs` file | an error, a warning not in `scripts/static_allowlists/oxlint.json`, or an entry in it that no longer occurs |
| knip | `npm run check:dead-code` | unused files, exports and dependencies | any finding |

There are no coverage floor and no new test here: Web's coverage stays report-only (95.95% of
statements on 2026-10-21), and a floor is #158. The 16 oxlint warnings of 2026-10-21 are all
allow-listed with a reason (16 `only-export-components` and `exhaustive-deps` cases where a hook
or provider shares a file with a component on purpose, or an effect must run once). The
`/// <reference types="vitest/config" />` line in `vite.config.ts` was a real finding and was
removed (the `import` of `vitest/config` already carries the types). What no check covers, and
the ticket for each: [`docs/agents/static-checks.md`](../docs/agents/static-checks.md).

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
- Network calls are faked, never real. Module and interaction tests mock
  `./api`'s `extractTruckTag`/`extractTrailerTag`/`extractScaleTicket` with
  `vi.mock('./api')`; `api.test.ts` fakes only `fetch`, and `App.scan.test.tsx`
  fakes the Scan service itself through `src/scanTestKit.tsx`
  (`makeWorld`/`renderApp`: fake auth, fake billing and a fake Scan service
  that follows the Worker's contract, which `App.interaction.test.tsx` also
  renders through). Nothing here ever hits a real backend.
  `localStorage`/`sessionStorage` are the real jsdom implementations, not
  mocked, since `recentRigs.ts` and the disclaimer-acknowledged flag's
  actual persistence behavior is exactly what's worth exercising for real.

## By file

| File | Category | Covers |
|---|---|---|
| `src/App.smoke.test.tsx` | Function | Proves the harness itself works (jsdom environment, jest-dom matchers, `App`'s `localStorage`/`sessionStorage` reads on mount) before anything real was written against it. Not meant to catch regressions in `App` itself. |
| `src/App.interaction.test.tsx` | **Interaction** | `App.tsx` has no exported handlers — its ~10 handlers (`startNewRig`, `selectExistingRig`, `onFileSelected`, `extractCurrent`, `skipCurrent`, `scanStandaloneTicket`, `updatePinWeightPct`, `continueReview`, `updateField`, `acknowledgeDisclaimer`) all read/write one shared `wizard` state object via closures, the same shared-mutable-state shape `test_streamlit_app.py` covers on the Python side via `st.session_state`. Driven through the real rendered UI with `@testing-library/user-event`, not by calling handlers directly (they aren't reachable that way). The two cases that scan a photo render as a signed-in Pro user through `scanTestKit.tsx` (and wait for "scans left"), because scanning is gated on the account (#26). Five cases: (1) a full happy path — start a new rig, skip all three image steps, reach Results, and confirm both `recentRigs` (localStorage) and `history` (in-memory) updated from the same `continueReview` call; (2) selecting an existing rig jumps straight to the scale step, skipping truck/trailer entirely — the same "skipped a step it shouldn't have" bug shape Android's `RigCheckNavHostTest` caught on 2026-08-18, here as a regression-shaped test written ahead of any bug, not after one; (3) an extraction error clears once the user skips instead of retrying, not left dangling on `wizard.uploadError`; (4) scanning a tow-vehicle-only ticket fills the stand-alone-weight field and hides the now-unnecessary pin-weight slider; (5) the pin-weight slider's value *leaves App.tsx* as the raw 15–25 whole number, unconverted — `./api` is mocked here, so this only proves App passes the number through, not that `api.ts` itself converts it (that's `src/api.test.ts`, below). A `Disclaimer gate` describe block, added for the #57 test audit, drives the same happy path to Results and asserts the gate directly: `ResultsStep`'s content is absent while the modal is still up and `sessionStorage`'s `rigcheck:disclaimerAcknowledged` key isn't yet `'true'`; acknowledging reveals Results and sets the key; and a second test pre-seeds that key before mounting `App` to confirm the modal does not reappear once it was acknowledged earlier in the session (the real claim behind "persists" — `sessionStorage`, unlike component state, survives a fresh mount). A `Truck GCWR` describe block (#46) drives the optional truck GCWR through the real screens, with Rigs and scale readings taken from the shared `test-vectors/breakdown_cases.json`: a Rig saved before GCWR existed (no `gcwr_lb`) still loads, and its Results have no Combined Rig Weight row and the Safe to Tow subline carries the "GCWR wasn't checked" caveat; a Rig saved with a GCWR restores it when selected, so Results show the Combined row against that GCWR and no caveat; and a GCWR typed on a new Rig's truck review step shows the hint, warns (without blocking) when below the typed GVWR and stops warning once corrected, is used by the Results, and is saved with the Rig in `localStorage`. |
| `src/api.test.ts` | Function + **Contract** | Only `fetch` and the `VITE_SCAN_SERVICE_URL` env are faked, so `api.ts` and `scanImage.ts` run for real. Each `extract*` posts one JSON request to `<service>/v1/scan` with `Authorization: Bearer <account token>`, the right `doc_type`, the photo as base64 with its media type, and the caller's `client_request_id`. Each failure the Scan service names (402 `insufficient_credits`, 401, 503 `auth_unavailable`, 502 `extraction_failed` and `billing_error`, 400) becomes a `ScanError` with a user-facing message that says whether the scan was refunded or not charged (`billing_error` only says the user may not have been charged, since the payment service can apply a charge and then time out); an edge error page, an unreadable success, no connection, `billing_error` and `extraction_failed_no_refund` are `lostResponse` (so a retry reuses the request id); no service address and an unreadable photo send nothing. `SCAN_TIMEOUT_MS` is pinned at 60 s (#112; the Worker's own `timeLimits.test.ts` checks it is longer than the Scan service's 45 s worst case). With fake timers (nothing waits for real), a request that never answers is aborted at `SCAN_TIMEOUT_MS` and fails as a `lostResponse` `timeout` error, a reply whose body stalls after the headers does the same, and a reply one millisecond inside the limit is delivered and leaves no timer running. What the service charges, refunds and dedupes is the Worker's own tests (`workers/scan-proxy/src/scan.test.ts`). |
| `src/scanImage.test.ts` | Function | A small JPEG/PNG/WebP/GIF is sent as it is; an oversize or unsupported photo is redrawn as a smaller JPEG when the browser can (canvas faked, so no real image decoding runs in jsdom), else refused with a `bad_photo` error before anything is sent. |
| `src/scanAttempts.test.ts` | Function | The request id is reused for the same photo while the last answer was lost, and is new once the service has answered (success or a named failure) or the photo changes. |
| `src/scanOutcomes.test.ts` | **Contract** | One test per row and field of the shared `test-vectors/scan_outcomes.json` (the "Scan outcomes" entry of `workers/scan-proxy/CONTEXT.md`), each produced the way the app produces it: the real `extract*` call against a faked `fetch` (and the faked clock for a request that never answers), the real `ScanAttempts`, the real notice. For every Web row: the message the user reads contains the row's phrases, a retry of the same photo keeps or changes the request id as the row says, and `canTryAgain` is what the row says (a delivered Scan with blank fields shows a notice, which has no buttons, so Try again is not checked for it here; `App.scanNotice.test.tsx` covers the screen). `nextStep` is checked by Android only. A field marked pending for Web in the fixture is skipped and shown as skipped. The three-label rule for naming unread fields is checked with made-up labels. |
| `src/visionToolSchema.test.ts` | **Cross-platform interface** | New 2026-10-21 (#148, under epic #147). Every field of `MODULES` in `mockData.ts` (truck, trailer, scale) that is not marked `optional` must be a property of the matching doc type (`truck_tag`, `trailer_tag`, `scale_ticket`) in the shared `test-vectors/vision_tool_schemas.json`, the tool schema the Worker forces on Claude: a name on one side only is never pre-filled and the Scan notice would report it as not read on every scan. A second test pins that the `optional` fields are exactly the manual-only ones, `standalone_weight_lb`, `gcwr_lb` and `axle_count`, so a new optional field cannot slip out of the check. No network. The Python (#140) and Android (#149) slices read the same file. |
| `src/scanFormFields.test.ts` | **Cross-platform interface** | New 2026-10-21 (#163, under epic #147). For each module of `MODULES` in `mockData.ts` (truck, trailer, scale), the set of `(name, type)` pairs equals the matching doc type's (`truck_tag`, `trailer_tag`, `scale_ticket`) `scanned` plus `manual_only` fields in the shared `test-vectors/scan_form_fields.json`, so a field missing on either side, or typed `text` on one side and `number` on the other, fails here. A second test per module pins that the fields marked `optional: true` are exactly the fixture's `manual_only` names. Field order is not checked. Separate from `visionToolSchema.test.ts` so each fails on its own. No network. The Streamlit and Android slices of the epic read the same file. |
| `src/App.scanTimeout.test.tsx` | **Interaction** | A scan the fake Scan service never answers (`neverAnswerNextRequest` in `scanTestKit.tsx`; the request stays open until the app aborts it) is given up on when the fake clock passes `SCAN_TIMEOUT_MS`, for the Truck Tag photo and for the stand-alone ticket scan: the check is blocked while it waits (#103), the "took too long, a retry is not charged twice" message shows, every leaving control is enabled again, and the retry ("Extract Data", or "Try again" for the ticket) carries the same `client_request_id` and is charged once. Only `setTimeout`/`clearTimeout` are faked, after the check is reached, with a minimal `jest` stand-in so the testing library's own settle step advances the fake clock instead of waiting on it forever. |
| `src/App.scan.test.tsx` | **Interaction** | Scanning through the real screens (`scanTestKit.tsx`: fake auth, fake billing, and a fake Scan service that follows the Worker's contract). A Pro user spends exactly one scan and sees the fields and the lower balance; a failed read is refunded and says so; a retry after a lost answer reuses the request id and is charged once; the next photo gets a new id; a stale balance answered with 402 shows "out of scans" with a way to buy more; the tow-vehicle-only ticket scan spends one scan too. Zero scans offers packs and leads back to the same check; a Free user is prompted to upgrade and a signed-out visitor to sign in, with nothing sent; no purchases means "scanning isn't available"; the plan still loading holds the scan back, and a failed load offers Try again. `components/ScanGate.tsx`, `scanAccess.ts` and the scan gating in `ReviewStep.tsx` have no module-level test of their own: this file and `UploadStep.test.tsx` are where they are covered. |
| `src/recentRigs.test.ts` | Function | `loadRecentRigs`: empty array when nothing stored, the stored array when valid, empty array (not a throw) on corrupt JSON or a parsed-but-non-array value. `saveRecentRig`: prepends and persists a new rig; replaces (not duplicates) a same-nickname rig case-insensitively, moving it to the front; caps the list at 5, dropping the oldest; still returns the computed list even if `localStorage.setItem` throws (e.g. quota exceeded) — the in-memory return value staying usable even when persistence silently fails is deliberate behavior worth locking down, not an oversight. |
| `src/wizard/UploadStep.test.tsx` | Module | Fake props, no `App`/network involved. Title/instructions render; Extract Data is disabled with no file, enabled with one, and the drop zone's placeholder swaps to the filename; selecting a file calls `onFileSelected`; Extract Data calls `onExtract`; the error message renders when given; the scale module's two extra pieces (the "No CAT scale ticket?" hint and the second "Build Estimated Model" skip button, both wired to `onSkip`, plus the first skip button's label swapping to "No Image / Enter Weight Manually") are present only for the scale module, absent for every other one. Scan access (#26): the scans left show when the visitor can scan; when they cannot, the way past it replaces Extract Data (Upgrade to Pro calls `onGoAccount`; Try again calls `onRetryScanAccess`). |
| `src/wizard/ReviewStep.test.tsx` | Module | Fake props. Each field renders from `data` (blank when missing); typing calls `onFieldChange(name, isNumber, value)`; the continue button (labelled `module.continueLabel`) calls `onContinue`; the error prop renders. The stand-alone-weight scan section: absent for non-truck modules and absent for the truck module when `onScanStandaloneTicket` isn't passed; its pin-weight slider shows only while `standalone_weight_lb` is unknown, hides once it's set (via `rerender`, not a fresh mount, to prove it's the same data change driving both states); the slider's `onChange` reports the numeric value. Scanning a ticket: shows "Reading…" and disables the button while the promise it's given is pending, re-enables once resolved; a rejection surfaces the scan's own local error text, distinct from the `error` prop — complements `App.interaction.test.tsx`'s standalone-scan case, which only exercises the resolved path. The optional GCWR field (#46): its hint is the input's accessible description, it is absent on the trailer step, the inline warning shows only when the GCWR is below a known GVWR (not when equal, above, blank, or with no GVWR), and typing under the GVWR still reports the value (a warning, not a block). |
| `src/wizard/ResultsStep.test.tsx` | Module | Fake props. Verdict headline/subline render; each breakdown item's label, badge, actual/rated weight, and note (present vs. `null`, via `rerender`) render correctly; the estimated-figures notice shows when any item is `estimated`, hidden when none are — the one thing `App.interaction.test.tsx` never exercises, since its `RESULT` fixture is always non-estimated; "Run Another Check"/"Back to Dashboard" call `onRestart`/`onGoHome`. |
| `src/wizard/RigStep.test.tsx` | Module | Fake props. No rig cards when `recentRigs` is empty; each recent rig's nickname and a manufacturer subtitle render when at least one of truck/trailer has one, the subtitle line omitted entirely when neither does; clicking a card calls `onSelectExisting` with that rig; Start New Rig stays disabled for an empty or whitespace-only nickname, enables once typed, and calls `onStartNew` with the **trimmed** nickname — the interface contract a caller (`App.tsx`'s `startNewRig`) relies on to not receive stray whitespace. |
| `src/auth.test.ts` | Function | `createSupabaseAuthClient` (the one line `App.auth.test.tsx` never reaches, since that suite injects its own fake client directly): returns `null` without calling the SDK when either `VITE_SUPABASE_URL` or `VITE_SUPABASE_PUBLISHABLE_KEY` is unset, and, when both are present, returns the auth slice of the client `supabaseClient.ts`'s `getSupabaseClient` builds by calling the (mocked) `createClient` with both values and the PKCE auth option `{ auth: { flowType: 'pkce' } }` (the app shares that one client with the Garage table, so `getSupabaseClient` has no test of its own beyond this). `@supabase/supabase-js` is mocked and env vars are stubbed explicitly via `vi.stubEnv`, so this never depends on `web/.env.local`'s actual contents. |
| `src/supabaseClient.pkce.test.ts` | Function | The real `@supabase/supabase-js` client (not mocked, `fetch` stubbed) built by `getSupabaseClient`: a session handed over in the URL fragment (`#access_token=...`) is not signed in (#95), and a `?code=` link without this browser's code verifier leaves no session and leaves the code in the URL, which `auth.tsx`'s `takeUnusedLinkProblem` and the Account notice rely on. Each test uses its own project URL so supabase-js's storage key never carries over. |
| `src/App.garage.test.tsx` | **Interaction** | The account-synced Garage (#28), driven through the real screens with a fake Supabase auth client and an in-memory fake of the account's Garage store. Signed in: a finished check saves its Rig to the account and not to `localStorage`; a Rig saved on one "device" appears on a second; the account's Rigs replace the browser's while signed in and the browser's return after sign-out; a failed add is retried once with the same idempotency key and ends with one Rig; a full Garage shows the cap message, still shows the check and saves nothing; any other save failure says so without blocking the check; reusing a Rig already in a full Garage updates it instead of adding; an update that finds its Rig gone falls back to an add; and an older refresh answering late cannot overwrite a newer list. Signed out: Rigs stay in the browser and the account store is never called. The server's own rules are not here; see `src/garageSchema.test.ts`. |
| `src/garageSchema.test.ts` | **Service boundary** | Runs `supabase/migrations/20261010000000_garage_rigs.sql` on a real Postgres (PGlite) as the `authenticated` and `anon` roles, with Supabase's `auth` schema stubbed. Row-level security (own rows only; a signed-out caller gets nothing; no update, hand-over or delete of another account's row; no direct insert); the Free cap of 5 with the cap in the error; accounts counted separately; a retried add (same key) creates one Rig, is not charged again, survives a rename, and is answered with the Rig even once the Garage is full; a nickname already present is refreshed without using capacity; last-used and tag updates work in a full Garage; deleting frees a slot. Cannot run two transactions at once, so concurrent adds are covered by the live `[supabase-tables]` External suite. |
| `src/supabaseGarage.test.ts` | Module | The adapter between the app's Garage store and the table/RPC contract, with the Supabase client faked: `add_rig` gets the key and Rig; `garage_full` becomes a `GarageFullError` carrying the cap (or `null` when the server's detail is unreadable); any other server error stays a plain error. |
| `src/App.history.test.tsx` | **Interaction** | The account-synced History (#29), driven through the real screens with a fake Supabase auth client and an in-memory fake of the account's History store. Signed in: a finished check is saved to the account and listed on the History screen; a check made on one "device" appears on a second; a check made elsewhere appears when History is opened; a failed save is retried once with the same idempotency key and ends with one entry; a save that fails twice says so, and the check's result still shows. Signed out: this visit's checks list on the History screen and the account store is never called; checks made before signing in are not uploaded, the account's own History replaces them on screen, and signing out brings them back. The cap, pruning and row-level rules are not here; see `src/historySchema.test.ts`. |
| `src/historySchema.test.ts` | **Service boundary** | Runs `supabase/migrations/20261022000000_history_entries.sql` on a real Postgres (PGlite) as the `authenticated` and `anon` roles, with Supabase's `auth` schema stubbed. Row-level security (own checks only; a signed-out caller gets nothing; no direct insert; no update or delete by any account); the Free cap of 10 (the 11th add drops the oldest, further adds keep dropping the oldest, accounts are pruned separately, the same Rig's checks stay separate entries, and "oldest" goes by insertion order, not timestamp, so a clock stepping back cannot prune the newest); a retried add (same key) creates one entry and does not prune again at the cap, and the same key from two accounts is two adds; the nickname is stored trimmed, an unknown verdict or blank nickname is refused. Cannot run two transactions at once, so concurrent adds are covered by the live `[supabase-tables]` External suite. |
| `src/supabaseHistory.test.ts` | Module | The adapter between the app's History store and the table/RPC contract, with the Supabase client faked: `add_history_entry` gets the key, the trimmed Rig nickname and the verdict; a server error stays an error so the caller can retry; the list is read newest first and each entry gets the same "Mon DD, YYYY" date a fresh check shows, from the server's timestamp. |
| `src/components/DisclaimerModal.test.tsx` | Module | Renders the disclaimer heading; clicking "I Understand — Continue" calls `onAcknowledge`. Deliberately small — this component has exactly one behavior. |
| `src/screens/History.test.tsx`, `src/screens/Dashboard.test.tsx` | Module | Both cover `verdictBadge.ts`'s `VERDICT_BADGE` map (`pass`→"Safe to Tow"/success, `fail`→"Over Limit"/warning, `partial`→"Partially Checked"/insufficient, `insufficient`→"Not Enough Info"/insufficient), which each file's verdict badge now reads from. **Regression tests for a real bug found 2026-08-21** auditing this suite's coverage: both files previously rendered *any* non-`'pass'` verdict as "Over Limit" with a warning badge — a partial or insufficient check (missing data, not an actual over-limit reading) got the same alarming label as a genuine failure. `History.test.tsx` also covers the title/per-entry rendering and, as of the #57 test audit, every filter pill (`All rigs`, a per-rig pill, `Within limits`, `Over limit`) and the "No checks match this filter." empty state — including that a partial or insufficient entry shows under neither `Within limits` nor `Over limit` (current behavior, asserted as such, not necessarily the last word on where those verdicts "should" sort). `Dashboard.test.tsx` now also covers the recent-rigs grid (card contents, the manufacturer-subtitle join, the truck/trailer line each being omitted when that half of the rig has none), the Recent Checks list (two-item cap, its own subtitle join, the "View history" link appearing only once there is a check), and every click target (`Start New Check`, `View History`, a rig card, "New rig") calling its handler. |
| `src/breakdown.test.ts` | **Cross-platform interface** | The Web port of `compute_breakdown`/`verdict_for` (`breakdown.ts`) against the shared `test-vectors/breakdown_cases.json`, the same cases the Python and Kotlin runners check (34 tests, including the `truck_gcwr` cases: no Combined Rig Weight row without a GCWR, and the Safe to Tow caveat when it was not checked): every Breakdown row, Combined Rig Weight included, has an over-limit case; a case that needs a capability the runner does not know **fails** rather than skips (#55); each row's note and badge and the verdict's headline and subline are asserted, with `note_android` only on the rows Android words differently. `createBreakdown` computes locally with no network call, stamps a "Mon DD, YYYY" date, converts the UI's whole-number pin weight percentage to the fraction the math uses (`test-vectors/pin_weight_pct_contract.json`) and treats a `NaN` reading, a `NaN` GCWR included, like a missing one. |
| `src/nickname.test.ts` | Function | The Rig nickname rule: names differing only by case or surrounding spaces are the same Rig, spaces inside a name are significant, `rigLookup` finds a Rig by that rule, and `rigSubtitle` joins the truck and trailer manufacturers (only one, or empty, when the other is missing). |
| `src/scanError.test.ts` | Function | `ScanError.canTryAgain`: which of the Scan service's error codes offer Try again and which do not, one test per code. |
| `src/App.auth.test.tsx` | **Interaction** | Web accounts through the real screens with an injected fake Supabase auth client: a visitor reaches the free manual-entry flow with no account; sign up, confirm by email, sign in, expose the token and sign out; the email and password fields are empty after sign out, after sign in and after a password reset (a shared browser), and show what was typed while signed out; a session is restored on load; wrong credentials show the error; a password reset email is sent, and its link lands on a new-password form that updates the password; a confirmation or recovery link opened in a browser that did not ask for it, an error redirect in the query string and an expired link in the fragment are each explained and sign nobody in (PKCE, #95); a normal page open says nothing about links; accounts are unavailable when Supabase is not configured. |
| `src/App.billing.test.tsx` | **Interaction** | Buying Pro and scan packs through the real screens with a fake billing client (58 tests): a Free user sees the plan, the scan balance and the Pro paywall with the not-certified statement; checkout opens and closes (the Close control, the browser Back button, before the SDK has opened the modal), and a second checkout cannot start while one is open; after a purchase the user is Pro at once, the starter scans arrive late and are rechecked on an interval (an updating state, the balance once the grant lands, a plain message after the window, a reload request when every check failed, no recheck after sign-out, another account or unmount, a hanging check never wedging the state); a plan load racing the purchase cannot turn the buyer back to Free; a checkout that settles late never hands its Pro, error or cancel notice to the next account; a failed plan load offers Try again and a failed purchase does not; packs are sold to Pro users only, each adds its own scans and never changes the plan, and a Free user is offered Pro only. |
| `src/App.scanInFlight.test.tsx` | **Interaction** | While a Truck Tag photo scan, or a stand-alone ticket scan, is in flight (#103): the check cannot be left or restarted and says why, is free again once the scan answers or fails, and a leave-and-restart attempt keeps the check. |
| `src/App.scanStale.test.tsx` | **Interaction** | A scan that answers after its check is no longer the current one changes nothing in the new check (its fields, its failure, a stand-alone weight) and the balance on screen is still read again. |
| `src/App.scanNotice.test.tsx` | **Interaction** | The review step after a Scan (#115): a Scan that read no field says one was used, offers no Try again and still counts; no second Scan goes out until the user picks a different photo; a Scan that read only some fields names the missing ones; none when every field was read (the optional ones are not counted); the same on the Trailer Tag and the Scale Ticket with that step's own field labels; none when the photo was skipped. |
| `src/revenueCatBilling.test.ts` | Module | `revenueCatBilling.ts`, the adapter over `@revenuecat/purchases-js` (the boundary file of the `revenuecat-web-billing` surface), with the SDK faked (24 tests): configured once with the first account and switched on later sign-ins, once even when two identify calls overlap, ending on the latest account; the lifetime package (or the configured package id) is the Pro offer, and nothing is offered when there is none; Pro comes from the active entitlement and the `SCAN` balance is refetched fresh; the SDK's cancel error is a cancelled outcome and any other error is rethrown; a purchase before an offer is loaded is refused; scan packs are the web-purchasable consumables only, never the Pro package, forgotten when another account is identified; `readBillingConfig` needs the API key and offering id and defaults the entitlement to `pro`. |
| `src/external/externalGuards.test.ts` | Structure | Static guards over the External suite, in `npm test` (30 tests): never collected by `npm test`; no external file creates a user, sends mail, starts a purchase or prints a secret; the wrapper can read each surface's own results (JUnit to `EXTERNAL_RESULTS_FILE`); the Pages test runs as its own project with only the `VITE_SUPABASE_` variables, scrubs any inherited `WEB_EXTERNAL_` variable, refuses fetched script or stylesheet URLs from another origin, and only reads. |
| `src/external/config.test.ts` | Function | `readConfig` for the External suite: every value when present, a missing or empty variable throws naming each one that is missing, a subset can be checked, the RevenueCat Web Billing variables are read on request, and no value ever appears in a message. |
| `src/external/bundleLoader.test.ts` | Function | The Pages journey's loader (`bundleLoader.ts`): follows static and dynamic imports from the entry once each (copes with a chunk importing the entry back and ignores strings that only look like imports), runs a split bundle that uses `import.meta` and `import()` in this process, names the chunk (or the entry) that failed to fetch, threw or has a syntax error, and removes its temporary files on dispose. |
| `src/external/siteShell.test.ts` | Function | The Pages shell checks (`siteShell.ts`): `assetUrls` resolves the module script and stylesheet against the site URL (icons and inline scripts ignored), `bakedSupabaseHosts` lists each distinct host once and reports a placeholder such as `undefined.supabase.co`, `bakedSecretKinds` flags an `sb_secret_` key or a `service_role` JWT without returning its value (and not an anon one), `foreignUrls` treats another scheme, port or lookalike host as another origin, `hostOf`. |

## Known gaps

Each entry says whether it is closed or still open, and an open one names the ticket
that tracks it or says there is none (`tests/test_testing_docs.py` checks this). Refreshed 2026-10-21 (#64)
against the test audit in `docs/test-audit/web.md`.

- ✅ **Closed (#42, #28, #85, #43)**: the audit's worst Web gap, that External
  covered only `supabase-auth`, is closed: four active surfaces (`supabase-auth`,
  `pages-site`, `supabase-tables`, `revenuecat-web-billing`, see "External suite"), and
  the pre-push External gate for a push that deploys Web is installed
  (`.githooks/pre-push`, root `TESTING.md`).
- ✅ **Closed 2026-08-21**: function tests for `recentRigs.ts` and
  `api.ts` in isolation — see `src/recentRigs.test.ts` and
  `src/api.test.ts` above.
- ✅ **Closed 2026-08-21**: the `pin_weight_pct` inter-module interface
  fixture (`test-vectors/pin_weight_pct_contract.json`, now read by
  `src/breakdown.test.ts`; its Python endpoint case went in #135) — see
  the root `TESTING.md`'s cross-platform section.
- ✅ **Closed 2026-08-21**: `ReviewStep`/`UploadStep`/`ResultsStep`
  component-level tests — see the three entries above.
- ✅ **Closed 2026-08-21**: `RigStep`/`DisclaimerModal`/`History`
  component-level tests, plus the `Dashboard`/`History` verdict-badge bug
  found in the process — see the entries above.
- ✅ **Retired 2026-10-19 (#135)**: the `BreakdownItem`/`VerdictInfo`
  response-shape pair (`src/apiShape.test.ts` and the Python endpoint
  test, via `test-vectors/breakdown_response_shape_contract.json`) went
  with the FastAPI app. The keys the UI reads are asserted by the
  golden-vector runner in `src/breakdown.test.ts` (and the Python and
  Kotlin runners).
- **Open (no ticket)**: the three document-type shapes of the `fields`
  the Scan service returns (truck tag, trailer tag, scale ticket, plus
  their nested tire spec) have no contract test with Web; the Worker's
  `docTypes.ts` schemas are the source of truth for them now that the
  Python response models are gone.
- ✅ **Closed 2026-10-04** (test audit #57): `History.tsx`'s filter pills
  and empty state, `Dashboard.tsx`'s rig grid/subtitle join/click
  targets, the Disclaimer gate (`Results` withheld until acknowledged,
  the acknowledgement persisting across a fresh `App` mount), and
  `createSupabaseAuthClient` (with and without the Supabase env vars) —
  see `src/screens/History.test.tsx`, `src/screens/Dashboard.test.tsx`,
  the `Disclaimer gate` block in `src/App.interaction.test.tsx`, and the
  new `src/auth.test.ts` above. (`apiShape.test.ts`, reviewed and kept
  then, was retired in #135.)
- **Deliberately not tested**: `wizard/ProcessingStep.tsx`,
  `components/StepPills.tsx`, `components/PredictiveEstimateNotice.tsx`,
  and the `design-system/` primitives (`Badge`/`Button`/`Card`) — purely
  presentational, no branching that affects correctness, the same
  judgment call already made not to write a dedicated test for Android's
  parallel `EstimatedFiguresNotice.kt`.
