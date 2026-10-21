# Test-first round: your run sheet

Working notes for the test-first round (map #49, decisions on #58 and #59). They are temporary: delete this file when the round ends. The general ticket flow is in [ticket-skills.md](ticket-skills.md). **This page is the run sheet: for any ticket, read "How to run one ticket" and then that ticket's card. Everything you copy, type or decide for that ticket is on its card; nothing needs to be looked up elsewhere on this page.**

## What is left, in order

One ticket at a time. Start the next only after the previous one is merged, so it is cut from the updated `MPSkills`.

| # | Ticket | Kind | Your part before or after | Card |
|---|---|---|---|---|
| 1 | #160 pin ruff and oxlint in the lockfiles instead of in commands | tooling, makes `scan-proxy-worker` and `worker-token-verification` stale on purpose | answer 2 questions the build session asks; the next External run covers the cost | [#160](#160-pin-ruff-and-oxlint-in-the-lockfiles) |
| optional | #132 is mutation testing worth running? (research) | research, no code change | none | [#132](#132-optional-mutation-testing-research) |

The order is #160, then the final External run (#150, #151, #152 and #153 are merged). #151 and #152 are the two Scan Proxy failures the #64 build session found (knip since #43, the coverage gate since #75); the merged testing documents already cite them by number. #150 was blocked by both on GitHub (now merged) because its new session-end commands would otherwise fail on day one, and it also closes the wider gap: nothing ran these checks, and some code is in no check's scope. None of the four changes a `package.json`, so none makes an External surface stale. #154 was closed as a duplicate of #153.

### A second lane, beside the chain above (field-name checks, epic #147)

A second `claude` session can build these while the chain runs, because they touch different files. They merge one at a time through the main checkout like everything else.

| Order | Ticket | Files | Card |
|---|---|---|---|
| 1 | #140 Streamlit `FIELDS` against the shared tool schema | `tests/test_ocr_output_key_contracts.py`, one line of `tests/TESTING.md` | merged 2026-10-21 |
| 2 | #148 Web `MODULES` field names against the shared tool schema | one new Vitest file, a row in `web/TESTING.md` | merged 2026-10-21 |
| 3 | #149 Android `ScanFieldMapping` keys against the shared tool schema | one new JVM test, a row in `android/TESTING.md` | [#149](#149-android-scan-field-keys-against-the-shared-tool-schema) |
| later | #147 the epic | owner decisions, one `CONTEXT-MAP.md` line | not built now: see the note after the cards |

Where it can collide with the chain: `tests/test_testing_docs.py` requires every test file to be named in its context's testing document, so #148 and #149 each edit `web/TESTING.md` or `android/TESTING.md`, the same files #150 and #153 edit (a different part of each, so git usually merges them; if not, the merge review resolves it). #149 is JVM-only, but `/ticket-start` counts any Android ticket as holding the emulator, so finish #149 before #153 starts (or start #149 with `--not-android` if #153 is already running). Do not run Gradle in two sessions at once with the emulator up: the machine runs out of memory (see "Things to remember").

After #153 (and #132 if you run it): a final run of whichever External surfaces went stale again (`uv run scripts/external_freshness.py` first, from the main checkout; Claude asks before each live run and before pushing). Deferred, not in this round: #40 (blocked on Play Console), #68, #69, #70, #72, #100. After the round: #144 (record context-level passes automatically) and #145 (check that a fresh clone builds on another computer).

## How to run one ticket

The same six steps every time. The card for the ticket gives the exact command for step 1 and the exact text for step 2.

1. **Start** (this main-checkout session, or any terminal in the main checkout): type the card's `/ticket-start` line. It creates `.claude/worktrees/ticket-N` and prints a paste-ready prompt.
2. **Build**: open a **new** `claude` session in `.claude/worktrees/ticket-N`. Paste the printed prompt as the first message, then paste the card's block directly under it (one message, nothing else added). A new session for every ticket.
3. **Finish**: when the build session says it is done, type `/ticket-finish` in the same session. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**, so the folder can be removed at merge.
4. **Merge**: back in the main checkout session, type `/ticket-merge N` (add `--allow-status` only to go past a `PARTIAL` you have decided to accept). Claude carries out the review: ledger check, reading the diff, mutation checks, merge, closing comment. If it finds a gap in the tests it asks for one added test and commits it on the branch.
5. **Push**: Claude asks first, every time. It never pushes by itself. Pushing `MPSkills` rebuilds Web, and the pre-push gate refuses a push that touches `web/`, `workers/scan-proxy/` or `android/` while an External surface is stale (`uv run scripts/external_freshness.py` says which; the honest ways through are a real run or `EXTERNAL_GATE_FORCE_REASON="why" git push`, which is recorded on the dashboard).
6. **Clean up after an Android ticket**: stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe emu kill`) and close any terminal still open in the ticket's folder, then `rmdir` the leftover `.claude/worktrees/ticket-N` if `/ticket-merge` says it could not remove it.

A session-start report (verification debt, #67) prints when each session opens. With the five contexts recorded it says there is nothing to report; it is advisory and you do nothing with it.

## Run cards

### #75 (merged 2026-10-20)

Done: `android/test-weekly.ps1` signs in the funded Supabase test account and the Android External suite ran `OK (6 tests)` with two paid scans. Nothing more to do for it.

### #39 (merged 2026-10-21)

Done: the `revenuecat-android-sdk` surface and the first Android External runner, `android\test-external.ps1` (needs one attached emulator with Google Play Services; free). Its six tests passed on 2026-10-21 and the pass is recorded. #40 adds its tests to this runner.

### #40 Google Play Billing surface (BLOCKED, not part of this round)

The #40 session found no Google Play Console account and no Play product: `lifetime` and `consumable` exist only on RevenueCat's Test Store, and the app uses the Test Store key, so it never calls `BillingClient`. You chose to block the ticket until Play Console exists (`DECISIONS` and `STATUS: BLOCKED` on #40, which keep the measured `BillingClient` behaviour for whoever resumes). `google-play-billing` stays `planned` and blocks nothing. **To restart it:** register Play Console, create at least one in-app product (the Play side of `lifetime` or `consumable`), then use the steps and block below.

- **Step 1:** `/ticket-start 40 --android` (its text names neither Android nor an `android/` path, so `/ticket-start` needs the flag). 
- **Step 2 block:**

```
Test-round additions:
- For a full Python run use `uv run pytest -n auto --maxprocesses=8` (about 45 s).
  The slow tooling tests are left out of planner runs unless the diff touches
  what they check.
- Judge each test by whether it would find or prevent a real bug and whether it
  adds run time; do not add tests only to raise a coverage number.
- If you add or move a class in `domain`, `data` or `ui`, classify it in
  `android/coverage-logic.toml` (allow-list, or waiver with a reason). The JVM
  coverage floor is 95% over the allow-listed decision logic. The Android
  end-of-session command is `uv run scripts/android_session_end.py` (JVM tests,
  coverage floor, detekt; no device).
- This needs the single emulator; no other Android ticket may be running. Start it
  with `G:\Android\Sdk\emulator\emulator.exe -avd medium_phone -no-snapshot-save
  -gpu swangle_indirect`, wait for `sys.boot_completed`, and kill it when you are
  done.
- Reuse the Android External runner #39 added (`android\test-external.ps1`,
  `scripts/run_external_android.py`): add a class named `*ExternalTest.kt` tagged
  `@ExternalSurface("google-play-billing")` next to the existing one, and do not
  write a second runner. The emulator image is `google_apis_playstore`, so Play
  Services is available.
- Live runs: do not run the live External suite or any paid call. The owner runs
  the surface from the main checkout after the merge. Do not commit changes to
  `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
```

- **Your part:** after the merge, the live run (`android\test-external.ps1` with the emulator
  up; Claude can start the emulator and run it with your go-ahead and a paid-call
  ceiling if the ticket's maximum is above 0).

### #105 (merged 2026-10-21)

Done: Web's External suite proves an entitlement named exactly `pro` exists (the fixture user `external-suite-pro`); the live run passed (33 tests) and can fail. The clause "attached to the Pro product" could not be proven without a purchase or a secret key and was accepted as is; #146 will check it in the Worker's External project. Keep the `external-suite-pro` grant non-expiring or far-dated.

### #64 (merged 2026-10-21)

Done: the five testing documents match real runs (Python 1586 passed + 4 xfail, Web 547 + 3 skipped, Scan Proxy 150, Android JVM 176 and instrumented 148), closed gaps are no longer listed as open, and `tests/test_testing_docs.py` pins the shape that drifts (every test file named, links, scripts, gap statuses). It found three problems and filed #151, #152 and #153, which are the next tickets below.

### #152 (merged 2026-10-21)

Done: `workers/scan-proxy/knip.json` lists `uv` under `ignoreBinaries`, so `npm run check:dead-code` exits 0 again with `package.json` untouched. Persistent tests in `tests/test_scan_proxy_knip_config.py` cover the real exit code, that `knip.json` is no External surface's pin or boundary file, and the testing document's wording.

### #151 (merged 2026-10-21)

Done: you chose to keep the 100% floor and exclude the run-as-script guard in `liveTokenCli.ts` with a `/* node:coverage ignore next 3 */` comment; Scan Proxy coverage is 100.00% of lines again, and `tests/test_scan_proxy_coverage_guard.py` pins the ignored range to exactly that guard.

### #150 (merged 2026-10-21)

Done: `uv run scripts/static_checks.py core|streamlit|web|scan-proxy` (and Android's `android_session_end.py`) are each context's session-end command, listed by the planner, run by `/ticket-finish` and recorded in the ledger. Every one exits 0 on its whole tree; a checked-in baseline holds the 16 accepted Web lint warnings; the inventory is `docs/agents/static-checks.md`. ruff and oxlint were pinned in the commands at first; #160 moved them into the lockfiles. Follow-ups #155 to #159 hold the gaps nothing covers yet.

### #153 (merged 2026-10-21)

Done: the repeat-run script leaves out the weekly class and every `@ExternalSurface` class, found the way the External runner finds them, so a real loop run is `OK (148 tests)`. You decided `--expected-tests` stays opt-in; the documented loop command passes `--expected-tests 148`.

### #148 (merged 2026-10-21)

Done: `web/src/visionToolSchema.test.ts` checks every non-optional `MODULES` field name against the shared tool schema, and pins that the optional fields are exactly the manual-only ones.

### #149 Android scan field keys against the shared tool schema

- **Step 1:** `/ticket-start 149` (finish it before #153 starts; if #153 is already running, add `--not-android`).
- **Step 2 block:**

```
Test-round additions:
- For a full Python run use `uv run pytest -n auto --maxprocesses=8` (about 45 s).
  The slow tooling tests are left out of planner runs unless the diff touches
  what they check.
- Judge each test by whether it would find or prevent a real bug and whether it
  adds run time; do not add tests only to raise a coverage number.
- If you add or move a class in `domain`, `data` or `ui`, classify it in
  `android/coverage-logic.toml`. This ticket adds a test only. The Android
  end-of-session command is `uv run scripts/android_session_end.py` (JVM tests,
  coverage floor, detekt; no device, no emulator needed).
- A new test class must be named in `android/TESTING.md` (`tests/test_testing_docs.py`
  checks it): add its row there.
- No live or paid runs.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->`
  markers.
```

- **Your part:** none beyond the usual steps.

### #147 (the epic): not built as a ticket now

It is labelled `needs-triage` and carries three decisions for you (whether a shared `scan_form_fields.json` fixture is added, whether field types are pinned, and its close gate). Its three children (#140, #148, #149) stand alone and do not need those answers. Once the children are merged, the decisions are a short conversation with Claude in the main session, and the only edit left is one line in `CONTEXT-MAP.md`. If you answer "add the shared fixture", that becomes a new ticket touching all three surfaces, and it should wait until the chain above is finished.

### #160 pin ruff and oxlint in the lockfiles

- **Step 1:** `/ticket-start 160`, after #153 is merged and before the final External run.
- **Step 2 block:**

```
Test-round additions:
- For a full Python run use `uv run pytest -n auto --maxprocesses=8` (about 45 s).
  The slow tooling tests are left out of planner runs unless the diff touches
  what they check.
- This ticket edits `pyproject.toml`, `uv.lock` and `workers/scan-proxy/package.json` on purpose. It will
  make External surfaces stale: list which ones (`uv run scripts/external_freshness.py`) and the paid-call
  cost in the STATUS comment. Do not run any live suite from the branch.
- The ticket has two Decisions: ask them with AskUserQuestion before building.
- A new slow-marked test file must be named in `scripts/test_planner_config.json`, and a new test file in
  its context's testing document (`tests/test_testing_docs.py`).
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->`
  markers.
```

- **Your part:** answer the two decisions (the recommended option is first).

### #132 (optional) mutation-testing research

- **Step 1:** `/ticket-start 132`. Lowest priority; production code is not changed. Skip it if the round is running long.
- **Step 2 block:**

```
Test-round additions:
- Research only: write one file under `docs/research/` and change no production code.
- No live or paid runs.
```

## Things to remember

- `--maxprocesses=8` caps `-n auto` because 24 workers ran this machine out of memory. Even at 8, the Python suite occasionally errors in tests that create a real git repo (`git init` or `git worktree add` exits 3221225773 or "WinError 1455: paging file too small") when the emulator, Gradle and other sessions are up (about 3 in 16 runs). It is memory, not a regression; re-run.
- The `medium_phone` AVD's Graphics is set to Software in Device Manager (done 2026-10-21; `G:\Android\EmulatorHome\avd\medium_phone.avd\config.ini`, `hw.gpu.mode`). The `-gpu swangle_indirect` start line above stays in the cards and does not depend on it.
- An emulator that `android_suite_loop.py` or a session started holds its `emulator.log` open and blocks deleting the ticket folder after `/ticket-merge`: step 6 above.
- If an assigned ticket is wrongly counted as holding the emulator (its title says Android but it never uses it), start the next with `--emulator-free <M>` naming it.
- Paid prompts from a non-interactive shell: `cmd /c "echo y| powershell -NoProfile -File workers\scan-proxy\test-external.ps1 -MaxPaidCalls N"` (piping several `'y'` lines from PowerShell declines the first prompt and records `skipped`, which spends nothing and leaves the surface stale). Claude does this, with your ceiling.
- The planner treats `*.md`, `docs/*` and `ClaudePlans/*` as docs-only (plans nothing), follows `shares_with` and `depends_on` links to downstream contexts, and does not list a deleted test file. Config choices on #66 are recorded in its DECISIONS comment.
- Open follow-up from the #130 merge: one more test case for the prefix-matching direction in `scripts/coverage_lib.py` (allow `ScanApiClient`, leave `ScanApiClientKt` unlisted); add it when a ticket next touches that file.

## History (for reference; nothing to do)

- **Merged:** #134, #129, #130, #41, #128, #43, #127, #66, #44, #84, #115, #135, #124, #136, #142, #131, #133, #143, #137, #67, #75, #39, #105, #64, #140, #148, #152, #151, #150, #153 (#141 closed as its duplicate). Follow-ups filed along the way: #138 (Worker preview deploy), #139 (cache the gate's registry lookups), #140 (Streamlit `FIELDS` vs the Claude extractor keys), #144, #145, #146, #150, #151, #152 and #153 (all now in the round; #153 is `scripts/android_suite_loop.py` also running the excluded live `RevenueCatAndroidSdkExternalTest`: 154 tests reported, 6 failing, against an offline suite of 148).
- **Pushed** up to d0ea7b7 on 2026-10-20 (plus handoff-note commits), including #115's changed Web scan wording, which the owner approved.
- **External runs, owner-approved:** 2026-10-19 sanity run of seven stale surfaces (4 paid calls; commit 95ae133); 2026-10-20 re-run of `pages-site` and `scan-proxy-worker` after a wrangler release (1 paid call); 2026-10-20 first runs of `anthropic` (Worker) and `anthropic-python` (6 paid calls, commit 615e552), both against `test-vectors/vision_external_cases.json` and `ExampleDocs/golden_fields.json`. All passed.
- **Verification debt (#67):** a committed SessionStart hook in `.claude/settings.json`; all five contexts have a recorded pass from 2026-10-20 at d0ea7b7 (a new machine or fresh clone needs the one-time commands in [verification-debt.md](verification-debt.md) again; #144 will automate it).
