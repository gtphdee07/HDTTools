# Test audit: Scan Proxy (`workers/scan-proxy/`)

Audited 2026-10-04 at commit `354c3d9` on `MPSkills`, against `docs/test-audit/rules.md`. Read-only; only offline commands were run (`npm test`, `npm run test:sanity`, `npm run typecheck`, `npm run test:coverage`, `npm run check:dead-code`). No External suite, wrapper, deploy or provider call was run.

## 1. Summary

1. Worst gap: the Worker has no token verification yet and no test anticipating it (#21/#23); `app_user_id` is caller-supplied and trusted (`src/request.ts:28`, `src/scan.ts:54`).
2. The two old External suites (`src/release/`, `src/weekly/`) are untagged, unrecorded per surface, and cover Anthropic and the deployed Worker with no freshness tracking; only `revenuecat-rest` is in the manifest. `anthropic`, `scan-proxy Worker` and Cloudflare packages are not watched.
3. `workers/scan-proxy/TESTING.md` is stale: it still lists the "spend throws" gap, "no timeout" and "no idempotency" as open, but all three are fixed and tested (`src/scan.ts:52-61`, `src/revenuecat.ts:38`, `src/scan.test.ts:185,226-273`). It also has a stray `X` line and a cut-off sentence at its end.
4. Offline suite is healthy and measured: 57/57 pass in about 0.4 s (1.5 s wall), typecheck clean, knip clean, coverage 100 percent line/branch/function on all 7 source files, so the 100 percent baseline still holds.
5. Run levels: file-level has no wrapper command (needs raw `node --test <file>`), context-level is one command (`npm test`), release-level is not one command (three PowerShell/npm paths, one never recorded).

## 2. Inventory

Measured, `workers/scan-proxy`, all in `src/`.

| TESTING.md category | Files and counts | Command | Runtime | Needs |
|---|---|---|---|---|
| 1 Function unit | `http.test.ts` (4), `request.test.ts` (15), `docTypes.test.ts` (4), plus the small pure cases in the others | `npm test` | included below | nothing |
| 2 Interaction | None as a named group. `scan.test.ts` (14) is the nearest: `runScan` control flow with fake `ScanDeps` and call-order/idempotency-key sharing | `npm test` | | nothing |
| 3 Module (public surface) | `revenuecat.test.ts` (9, fetch mocked), `claude.test.ts` (5, fetch mocked at the SDK HTTP boundary), `index.test.ts` (6, real `defaultScanDeps` wiring through `worker.fetch`) | `npm test` | | nothing |
| 4 Inter-module | `docTypes.test.ts` field-name check against Android's `ScanFieldMapping.kt` (asserts schema keys only; does not read the Kotlin file); `index.test.ts` is the Worker-internal wiring contract | `npm test` | | nothing |
| 5 External | 3 suites, see below | see below | not measured | secrets, network, money |

Totals measured: 57 tests in 7 files. `npm test` = `node --test src/*.test.ts` (`package.json:6`), 57 pass, duration 361 ms. `npm run test:sanity` (the Minor suite, name pattern `[sanity]`) = 9 tests, 9 pass. Minor can be run alone: yes.

Counts by file (grep of top-level `test(`): claude 5, docTypes 4, http 4, index 6, request 15, revenuecat 9, scan 14.

External suites (not run):

| Suite | Path | Tests | Command | What it needs | Cost | Tagged |
|---|---|---|---|---|---|---|
| Direct provider ("Release") | `src/release/scan.release.test.ts` | 5 (hard stop without both keys unless `SKIP_KEYS=1`) | `npm run test:release` or `.\test-release.ps1 [-SkipKeys]` | `ANTHROPIC_API_KEY`, `REVENUECAT_SECRET_KEY` in the shell | about $0.01 for one billed Claude call; RevenueCat calls net zero | no |
| Through our service ("Weekly") | `src/weekly/scan.weekly.test.ts` (hard-coded workers.dev URL, line 24) | 4 | `.\test-weekly.ps1` or `npm run test:weekly`; `pretest:weekly` runs `typecheck` then `wrangler deploy` (`package.json:13`) | wrangler login/Cloudflare credentials for the deploy, network; no local provider key | 2 billed Claude calls plus 2 SCAN credits per run (TESTING.md says "one real Claude call" per success case); the corrupted-image case is free | no |
| Per surface | `src/external/revenuecatRest.external.test.ts`, runner `src/external/run.ts` | 6, all tagged `[revenuecat-rest]` | `.\test-external.ps1 [-Skip]` or `npm run test:external` | `REVENUECAT_SECRET_KEY` (v2, Customer information read and write) | free ledger adjustments; `max_paid_calls` 0 | yes |

Recorded results (`scripts/dashboard_data/external_status.json`): `scan_proxy.weekly` passed 2026-08-24; there is no `scan_proxy.release` entry at all (the Release suite has never been recorded as run, via the wrapper); `surfaces.revenuecat-rest` passed 2026-10-04 at `51dc229`.

Note on the Weekly suite: running it deploys the Worker to production as a side effect of the npm pre-script, and `test-weekly.ps1` does not mention that. Anyone running `npm run test:weekly` to "just test" will deploy.

## 3. Code coverage

Measured with `npm run test:coverage` (Node built-in), offline:

| File | Line % | Branch % | Funcs % |
|---|---|---|---|
| claude.ts | 100 | 100 | 100 |
| docTypes.ts | 100 | 100 | 100 |
| http.ts | 100 | 100 | 100 |
| index.ts | 100 | 100 | 100 |
| request.ts | 100 | 100 | 100 |
| revenuecat.ts | 100 | 100 | 100 |
| scan.ts | 100 | 100 | 100 |
| all files | 100 | 100 | 100 |

The 100 percent baseline in `TESTING.md` holds, with 57 tests now (the doc's "57" count still matches by coincidence: the doc's tests were replaced by new timeout/idempotency tests, not added). Uncovered files or functions: none. Caveats (judgement): `src/types.ts` has no executable code; `src/external/run.ts` is the only non-test source outside the glob and is not covered (it is the External runner, and is itself covered only by `tests/test_external_wrapper.py` in Python, not checked here). Coverage is line/branch of mocked code; it says nothing about the real provider contracts.

`npm run typecheck` (tsc --noEmit): clean. `npm run check:dead-code` (knip): clean, no output.

## 4. Feature coverage

| Feature / requirement | Verifying test | Status |
|---|---|---|
| Scan success: Spend once, extract, return fields | `scan.test.ts:33` `[sanity]`; `index.test.ts:61` through real wiring | covered |
| Scan failure: extraction fails, Refund, `extraction_failed` | `scan.test.ts:84`; `index.test.ts:78` (real wiring, exactly 2 RevenueCat calls) | covered |
| Doc types (truck_tag, trailer_tag, scale_ticket) | `scan.test.ts:275`; `docTypes.test.ts` (completeness, required-matches-properties, Android field names, unique toolName) | covered |
| Request validation | `request.test.ts` (15 cases incl. wrong types, arrays, null media_type, unknown fields, `client_request_id`) | covered |
| Router: POST /v1/scan only, 404, bad JSON 400, parse error passthrough | `index.test.ts:96-116` | covered |
| Idempotency Key: client-supplied id, stable across retries | `scan.test.ts:226,244`; fallback `:260` | covered |
| Idempotency Key: same key for Spend and Refund; Refund key suffix `-refund` | `scan.test.ts:156`; `revenuecat.test.ts:38` | covered |
| Timeouts (10 s RevenueCat, 20 s Anthropic) | `revenuecat.test.ts:123`, `claude.test.ts:105` (assert the configured value, not an actual abort) | covered by configuration check only |
| Real timeout abort behavior | none (neither mock tests an actual abort firing) | none |
| Account-token verification, no trusted user id (#21) | none; not built | none (not yet implemented) |
| Doc type and model choice (`claude-sonnet-5`, `src/claude.ts:13`) | `claude.test.ts:38` asserts model in the request; no test that the model still exists at Anthropic (that is the live suite's job) | offline asserted, live only in the untagged release suite |
| Multi-caller (Web through the shared service, #26) | none | none (not yet) |

Money-critical path, Spend and Refund failure modes:

| Failure mode | Behavior (file:line) | Test |
|---|---|---|
| Spend returns 422 | 402 `insufficient_credits`, Claude never called (`scan.ts:64`) | `scan.test.ts:52`; `revenuecat.test.ts:63` |
| Spend returns other non-OK status | 502 `billing_error`, Claude never called (`scan.ts:70`) | `scan.test.ts:68` |
| Spend throws (network failure, timeout) | now caught: 502 `billing_error` (`scan.ts:53-61`) | `scan.test.ts:185`. `revenuecat.test.ts:94` still shows `spendCredit` itself rejects, as designed |
| Extraction throws (incl. timeout) | Refund, 502 `extraction_failed` (`scan.ts:85`) | `scan.test.ts:84,208` |
| Refund returns `ok:false` | 502 `extraction_failed_no_refund` (`scan.ts:103`) | `scan.test.ts:122` |
| Refund throws | caught by `.catch(() => null)`, same `_no_refund` response (`scan.ts:93`) | `scan.test.ts:105` |
| Non-JSON error body from RevenueCat | body is `null`, not thrown (`revenuecat.ts:41`) | `revenuecat.test.ts:76` |
| Duplicate Spend after a lost response | RevenueCat's Idempotency-Key; not provable offline | live only: `revenuecatRest` journey test (same-key retries change nothing) |

The documented known gap in `TESTING.md` ("a spend call that throws is not caught") is no longer true: it was closed (commit `6c59f05`, "Close scan-proxy's timeout and idempotency gaps") and `scan.test.ts:185` now pins the fix. The doc was not updated, see section 6.

Untested edge: when both Spend succeeds and `extractFields` succeeds but `json(...)` somehow fails, nothing is refunded; judged not realistic, noted only. Another gap (judgement): a Spend that returns 200 but with an unexpected body is treated as success without inspecting the body; the `revenuecatRest` live suite covers the real shape, no offline test does.

## 5. Interface coverage

Our interfaces:

| Interface | Test |
|---|---|
| `POST /v1/scan` request contract (`ScanRequest`: app_user_id, doc_type, image_base64, media_type, optional client_request_id) | `request.test.ts`, `index.test.ts` |
| `POST /v1/scan` response envelope (`ok`, `code`, `message`, `fields`, `doc_type`, codes `bad_request`, `insufficient_credits`, `billing_error`, `extraction_failed`, `extraction_failed_no_refund`, `not_found`) | per-code tests in `scan.test.ts`, `index.test.ts`, `http.test.ts`; no single test lists the full code set as a contract |
| Cross-platform: schema field names vs Android `ScanFieldMapping.kt` | `docTypes.test.ts` (hard-codes expected keys; nothing reads the Kotlin file or a shared fixture, so it can drift on the Android side without failing here) |
| Cross-platform: Android client `ScanApiClient` contract (60 s read timeout) | `claude.test.ts:105` asserts 20 s only as a literal; no test ties it to Android's value |
| Module-to-module: `scan.ts` <-> `revenuecat.ts` / `claude.ts` through `ScanDeps` | `scan.test.ts` (fakes), `index.test.ts` (real wiring) |
| Web as a second caller | none (#26 not built) |

Their interfaces:

| Interface | Offline test | Live test | Watched in `scripts/external_manifest/surfaces/` |
|---|---|---|---|
| RevenueCat REST v2 virtual currency (`revenuecat.ts`) | `revenuecat.test.ts` (fetch mocked) | `src/external/revenuecatRest.external.test.ts` (tagged) plus a subset in `src/release/` | `revenuecat-rest.json`: boundary file `revenuecat.ts`, no pins, no registry packages, `max_paid_calls` 0, platforms scan-proxy and android |
| Anthropic Messages API via `@anthropic-ai/sdk` (`claude.ts`) | `claude.test.ts` (fetch mocked) | `src/release/` (2 tests, untagged) and 3 of the 4 `src/weekly/` tests (untagged) | no manifest entry; #37 plans it |
| Deployed Worker at workers.dev (`/v1/scan`) | none | `src/weekly/` (untagged) | no manifest entry; #41 plans it |
| Cloudflare Workers runtime (`compatibility_date = "2026-08-01"` in `wrangler.toml:3`, wrangler, workerd) | none; TESTING.md lists "Workers-runtime-specific behavior (vitest-pool-workers)" as a deliberate gap and says the Worker uses no Workers-only APIs. It does use `AbortSignal.timeout`, `crypto.randomUUID` and a dynamic `import()`, all of which run in Node tests, not in workerd | none | no |
| RevenueCat project config (`proj07f52826`, currency `SCAN`) | none (value is hard-coded in the live tests as well as `wrangler.toml`) | yes in all live suites | no |

Packages a "their side changed" check should watch, none currently watched for this context:

- Anthropic: npm `@anthropic-ai/sdk` (pinned `^0.71.0`, installed 0.71.2). The caret on a 0.x version only allows patch updates, so a new minor will not arrive by `npm install` but still counts as a provider release under ADR-0008 and should mark the surface stale. The model id `claude-sonnet-5` is hard-coded (`claude.ts:13`) and is not a package, so a model deprecation is invisible to the registry proxy.
- Cloudflare: npm `wrangler` (`^4.0.0`, installed 4.123.0), `workerd` (via wrangler; lock requires `>1.20260305.0`; `allowScripts` pins `workerd@1.20260811.1` in `package.json:34`), `@cloudflare/workers-types` (`^5.20260811.1`, installed 5.20260817.1), plus the `compatibility_date` in `wrangler.toml` as a watched pin (#41 already says this).
- RevenueCat: there is no client library in this Worker. The manifest correctly lists no packages; REST v2 changes are invisible to the proxy. The only freshness input is edits to `revenuecat.ts`. Consider (suggestion) watching `purchases-android` (Maven) as a stand-in, since the Android SDK and REST share the dashboard config; the `revenuecat-rest` manifest lists `android` as a platform already.

## 6. Spec check

- **Stale documentation (TESTING.md contradicts the code and tests):** `workers/scan-proxy/TESTING.md` still says in "What each test covers" that `spendCredit itself rejecting propagates out of runScan rather than being caught`, and in "Known gaps" that there is "No timeout on the Anthropic/RevenueCat fetch calls" and "No request-level idempotency across client retries". All three were closed in commit `6c59f05` and have tests (`scan.test.ts:185,208,226,244,260`; `revenuecat.test.ts:123`; `claude.test.ts:105`). Also: `revenuecat.test.ts:94` is described as documenting a gap, but it is now the expected behavior (scan.ts catches it). The Minor/Major/External table and the `test-weekly.ps1` note are fine.
- **TESTING.md final section is damaged:** the "Per-surface External suite" section ends mid-sentence ("The Anthropic cases in `src/release/` are a" then a lone `X` line). This looks like a bad edit; the rest of the paragraph (about the Anthropic cases) is missing. Not edited, since read-only.
- **Tests that lag the specs:** #21 acceptance criteria (missing, malformed, expired, wrongly-signed tokens rejected; valid token spends the right account; existing behavior unchanged; tested at the HTTP boundary with RevenueCat, Anthropic and Supabase faked) have no test yet. The offline `index.test.ts` already has the shape for the "tested at the HTTP boundary with fakes" criterion, but its `fetch` mock only routes RevenueCat and Anthropic, so there is no Supabase fake, and `index.test.ts` has no injection point for it (the code header notes there is "no injection point at this layer").
- **Tests that exceed the specs:** `client_request_id` and the timeouts are tested, though ADR-0003 does not mention them; no conflict.
- **Spec contradiction to watch (judgement):** under #21 the caller-supplied `app_user_id` should stop being trusted, so `request.test.ts` cases asserting that a blank or missing `app_user_id` is rejected, and `scan.test.ts` and `index.test.ts` bodies containing `app_user_id`, will all need to change at once; the same applies to `weekly/` and `release/` which send `app_user_id` directly (`scan.weekly.test.ts:25-32`). Those live suites will fail against a verifying Worker, and they will need a valid token for `weekly-test-user`, which needs the Supabase test user (`scripts/wizard_web_external_test_user.sh`) to map to a RevenueCat customer. That mapping does not exist yet.
- **ADR-0008 vs current practice:** ADR-0008 says "Existing scan-proxy and Android External suites need surface tags added, and each must be reviewed against the four depths". Review for RevenueCat was done (#38; recorded in TESTING.md). Review for Anthropic (#37) and the Worker (#41) is still open, so `release/` and `weekly/` stay untagged by design; their ticket text says both will be reviewed then.
- **Stale cost note:** `scan.weekly.test.ts` header says "No local secrets needed" (true), but it needs wrangler credentials for `pretest:weekly`, a prerequisite that is not mentioned in the file.
- **Freshness gate not wired in:** ADR-0008 says a git pre-push hook, the Worker deploy wrapper and the Android release step run the freshness check. `.git/hooks` holds only samples, no `.githooks/` directory exists, and `package.json` `deploy` is bare `wrangler deploy`. So, today, nothing stops `npm run deploy` or `npm run test:weekly`'s pre-script from deploying with stale surfaces. (Measured: absence of files; I did not read `external_freshness.py` beyond a grep.)

## 7. Rule fit

1. **Scope ladder (file, context, application).**
   - File: no named command. `node --test src/scan.test.ts` works directly (documented nowhere); `npm test` hard-codes the glob so an extra file argument cannot be forwarded cleanly (`npm test -- src/scan.test.ts` would append after the glob and run both). Supportable, but needs a convenience script or documented raw command.
   - Context: yes, `npm test` (Major) plus `npm run typecheck`, `npm run test:coverage`, `npm run check:dead-code`. These are four commands, not one; no `npm run check:all`.
   - Application: out of this context's hands (root-level).
2. **Per issue.** Minor alone: yes (`npm run test:sanity`, 9 tests). Major alone: yes (`npm test`). Targeted test for an issue: ordinary `node --test <file> --test-name-pattern`. Inter-module interface tests: only the `docTypes.test.ts` Android field check exists; the Android side has no counterpart in this Worker's suite. External for a changed boundary file: `.\test-external.ps1` (only the stale surface runs), which covers RevenueCat only; for `claude.ts` changes there is no tagged Anthropic suite, so diff-driven External cannot be targeted, only the whole untagged Release suite.
3. **Session end.** Offline context run is about 2 s and needs nothing; supports rule 3 fully. Blockers: none for offline. Note that the Worker has no device tests.
4. **Release.** Rule 4 says a full run of every category, including paid External tests, for the Worker (wrangler deploy). Today that is three separate paths: `.\test-release.ps1` (needs both keys), `.\test-weekly.ps1` (deploys first, needs wrangler auth), and `.\test-external.ps1`, plus the offline commands. There is no single command; the Release suite has never recorded a result; `deploy` itself runs no gate. Not one command today.
5. **Web gate.** Web depends on the shared Worker (ADR-0003, #26); the manifest has no Web-to-Worker chain entry and the Worker token surface is "planned". Not testable for this context today.

## 8. Incremental complexity (cheapest to dearest)

| # | Step | Command | Time | Cost and prerequisites |
|---|---|---|---|---|
| 1 | One test file | `node --test src/scan.test.ts` (from `workers/scan-proxy`) | under 1 s | nothing |
| 2 | Minor suite | `npm run test:sanity` | under 1 s (9 tests) | nothing |
| 3 | Major suite | `npm test` | 0.4 s test time, about 1.5 s wall (57 tests) | nothing |
| 4 | Typecheck | `npm run typecheck` | a few seconds | nothing |
| 5 | Coverage | `npm run test:coverage` | a few seconds | nothing |
| 6 | Dead code | `npm run check:dead-code` | a few seconds | nothing |
| 7 | Free live, per-surface | `.\test-external.ps1` | seconds (only if RevenueCat is stale; 6 tests) | `REVENUECAT_SECRET_KEY`; free ledger calls; network |
| 8 | Direct provider (Release) | `.\test-release.ps1` | tens of seconds, not measured | both keys; one billed Claude call (about $0.01); owner confirmation required under rule 6 |
| 9 | Through the deployed Worker (Weekly) | `.\test-weekly.ps1` | about a minute or more with deploy, not measured | deploys to production; wrangler auth; 2 billed Claude calls and 2 SCAN credits; owner confirmation required |
| 10 | Release run (rule 4) | steps 3-9 together | not measured | everything above; no single wrapper |

None of steps 7-9 were run by this audit.

## 9. Gaps and suggested tickets

| Title | Source | Size |
|---|---|---|
| Update `workers/scan-proxy/TESTING.md`: remove the closed gaps (spend throws, no timeout, no idempotency), fix the truncated tail and stray `X` line | section 6 | small |
| Add a file-level and a context-level command (for example `npm run test:file -- <path>` and a single `check` script that chains test, typecheck, coverage, knip) | rule 1, section 7 | small |
| Make `pretest:weekly`'s deploy explicit: add a warning to `test-weekly.ps1`, or split a no-deploy `test:weekly:only`, and make the deploy step run the ADR-0008 freshness check | rules 4, 5; section 6 | small |
| Add the untagged Release and Weekly suites to the per-surface framework: tag and register `anthropic` (#37) and `scan-proxy-worker` (#41) with watched packages `@anthropic-ai/sdk`, `wrangler`, `workerd`, `@cloudflare/workers-types` and the `compatibility_date` pin | rule 7, section 5 | medium (already ticketed as #37, #41) |
| Record the Release suite's result (it has never been recorded via the wrapper) | section 2 | small |
| Add offline account-token tests at the HTTP boundary with Supabase faked (missing, malformed, expired, wrong signature, valid, unchanged Spend/Refund/idempotency), written before or with #21 | #21, section 4 | medium |
| Plan the migration of `release/` and `weekly/` and `request.test.ts` away from caller-supplied `app_user_id` (needs a token for the weekly test user) | #21, #23, section 6 | medium |
| Add a shared contract test for the response-code set and doc-type field names, ideally using a fixture file Android's tests also read (like `test-vectors/`), instead of hard-coded keys in `docTypes.test.ts` | section 5, category 4 | medium |
| Add a Workers-runtime smoke test (workerd via `wrangler dev` or vitest-pool-workers), or accept the documented gap explicitly, to catch Cloudflare runtime changes | section 5 | medium |
| Add a test that an actual timeout abort fires and maps correctly (both the RevenueCat and Anthropic paths), not just that the option is set | section 4 | small |
| Decide on RevenueCat watched packages (for example Maven `purchases-android` as a drift proxy) | rule 7, section 5 | small |
| Add one shared check that `claude.ts`'s `MODEL` still exists at Anthropic (cheap `models.list` or retrieve call, free) as part of the Anthropic surface | section 4 | small |
