# Test-first round: your run sheet

Working notes for the test-first round (map #49, decisions on #58 and #59). They are temporary: delete this file when the round ends. The general ticket flow is in [ticket-skills.md](ticket-skills.md). **This page is the run sheet: for any ticket, read "How to run one ticket" and then that ticket's card. Everything you copy, type or decide for that ticket is on its card; nothing needs to be looked up elsewhere on this page.**

## What is left, in order

One ticket at a time. Start the next only after the previous one is merged, so it is cut from the updated `MPSkills`.

| # | Ticket | Kind | Your part before or after | Card |
|---|---|---|---|---|
| 1 | #64 refresh each context's testing document | docs | none | [#64](#64-refresh-the-testing-documents) |
| 2 | #150 static checks (typecheck, lint, dead code, coverage floor) never run: put each context's into its session-end command and clear what they find | tooling + small fixes | answer 4 questions the build session asks | [#150](#150-static-checks-never-run) |
| 3 | #154 the Android repeat-run script runs the live External test that Gradle excludes | tooling, uses the emulator once | go-ahead to start the emulator for the acceptance run | [#154](#154-android-repeat-run-script-excludes) |
| optional | #132 is mutation testing worth running? (research) | research, no code change | none | [#132](#132-optional-mutation-testing-research) |

#150 comes right after #64 because it edits the same testing documents (it is blocked by #64 on GitHub) and because it should land before the final External run: it changes no `package.json`, so it makes no External surface stale, and the checks it adds then cover everything the round changed. Found while merging the round: Scan Proxy knip fails since #43, Scan Proxy coverage is 99.84% against a 100% floor, and nothing ran either.

After #154 (and #132 if you run it): a final run of whichever External surfaces went stale again (`uv run scripts/external_freshness.py` first, from the main checkout; Claude asks before each live run and before pushing). Deferred, not in this round: #40 (blocked on Play Console), #68, #69, #70, #72, #100. After the round: #144 (record context-level passes automatically) and #145 (check that a fresh clone builds on another computer).

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

### #64 refresh the testing documents

- **Step 1:** `/ticket-start 64`.
- **Step 2 block:**

```
Test-round additions:
- For a full Python run use `uv run pytest -n auto --maxprocesses=8` (about 45 s).
  The slow tooling tests are left out of planner runs unless the diff touches
  what they check.
- Counts and commands in the documents must match a real run of the free, offline
  suites; run them and quote what they print. No live or paid runs.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->`
  markers.
```

### #150 static checks never run

- **Step 1:** `/ticket-start 150`, only after #64 is merged (GitHub blocks it until then).
- **Step 2 block:**

```
Test-round additions:
- For a full Python run use `uv run pytest -n auto --maxprocesses=8` (about 45 s).
  The slow tooling tests are left out of planner runs unless the diff touches
  what they check.
- Judge each test by whether it would find or prevent a real bug and whether it
  adds run time; do not add tests only to raise a coverage number.
- Do not edit `web/package.json` or `workers/scan-proxy/package.json`: they pin
  three External surfaces, and a change makes them stale. Use `knip.json` and other
  config files instead.
- The ticket has four Decisions: ask them with AskUserQuestion before building.
- The ticket cannot be READY TO MERGE until every context's new session-end command
  exits 0 on that context's whole tree; quote the real output for all five in the
  STATUS comment.
- No live or paid runs, no emulator needed (the Android check already exists).
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->`
  markers.
```

- **Your part:** answer the four decisions the build session asks (where the checks run, whether warnings fail, new tools, Python coverage floor timing). Each has a recommended first option.

### #154 Android repeat-run script excludes

- **Step 1:** `/ticket-start 154` (it names `android/` paths, so the Android flag should be detected; add `--android` if it says the ticket is not Android). Run it after #150 is merged and no other Android ticket is running.
- **Step 2 block:**

```
Test-round additions:
- For a full Python run use `uv run pytest -n auto --maxprocesses=8` (about 45 s).
  The slow tooling tests are left out of planner runs unless the diff touches
  what they check.
- Judge each test by whether it would find or prevent a real bug and whether it
  adds run time; do not add tests only to raise a coverage number.
- This needs the single emulator for the acceptance run only; no other Android
  ticket may be running. Start it with `G:\Android\Sdk\emulator\emulator.exe -avd
  medium_phone -no-snapshot-save -gpu swangle_indirect`, wait for
  `sys.boot_completed`, and kill it when you are done.
- Live runs: do not run the live External suite or any paid call. Do not commit
  changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg`
  from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->`
  markers.
```

- **Your part:** none beyond the usual steps; stop the emulator afterwards (step 6).

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

- **Merged:** #134, #129, #130, #41, #128, #43, #127, #66, #44, #84, #115, #135, #124, #136, #142, #131, #133, #143, #137, #67, #75, #39, #105 (#141 closed as its duplicate). Follow-ups filed along the way: #138 (Worker preview deploy), #139 (cache the gate's registry lookups), #140 (Streamlit `FIELDS` vs the Claude extractor keys), #144, #145, #146, #150 and #154 (both now in the round; #154 is `scripts/android_suite_loop.py` also running the excluded live `RevenueCatAndroidSdkExternalTest`: 154 tests reported, 6 failing, against an offline suite of 148).
- **Pushed** up to d0ea7b7 on 2026-10-20 (plus handoff-note commits), including #115's changed Web scan wording, which the owner approved.
- **External runs, owner-approved:** 2026-10-19 sanity run of seven stale surfaces (4 paid calls; commit 95ae133); 2026-10-20 re-run of `pages-site` and `scan-proxy-worker` after a wrangler release (1 paid call); 2026-10-20 first runs of `anthropic` (Worker) and `anthropic-python` (6 paid calls, commit 615e552), both against `test-vectors/vision_external_cases.json` and `ExampleDocs/golden_fields.json`. All passed.
- **Verification debt (#67):** a committed SessionStart hook in `.claude/settings.json`; all five contexts have a recorded pass from 2026-10-20 at d0ea7b7 (a new machine or fresh clone needs the one-time commands in [verification-debt.md](verification-debt.md) again; #144 will automate it).
