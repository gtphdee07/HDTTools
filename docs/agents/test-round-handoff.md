# Test-first round: your run sheet

Working notes for the test-first round (map #49, decisions on #58 and #59). They are temporary: delete this file when the round ends. The general ticket flow is in [ticket-skills.md](ticket-skills.md). **This page is the run sheet: for any ticket, read "How to run one ticket" and then that ticket's card. Everything you copy, type or decide for that ticket is on its card; nothing needs to be looked up elsewhere on this page.**

## What is left, in order

One ticket at a time. Start the next only after the previous one is merged, so it is cut from the updated `MPSkills`.

| # | Ticket | Kind | Your part before or after | Card |
|---|---|---|---|---|
| 1 | #75 Android External suite with a funded Supabase test account | Android, emulator, 2 paid scans | confirm the two paid scans | [#75](#75-android-external-suite-with-a-funded-test-account-in-build) |
| 2 | #39 RevenueCat Android SDK surface | Android, emulator, adds the first Android External runner | the live run after the merge | [#39](#39-revenuecat-android-sdk-surface) |
| 3 | #40 Google Play Billing surface | Android, emulator with Play Services, builds on #39's runner | the live run after the merge | [#40](#40-google-play-billing-surface) |
| 4 | #105 prove the RevenueCat `pro` entitlement | Web, free live run | **a RevenueCat dashboard step first** | [#105](#105-prove-the-revenuecat-pro-entitlement) |
| 5 | #64 refresh each context's testing document | docs | none | [#64](#64-refresh-the-testing-documents) |
| optional | #132 is mutation testing worth running? (research) | research, no code change | none | [#132](#132-optional-mutation-testing-research) |

After #64: a final run of whichever External surfaces went stale again (`uv run scripts/external_freshness.py` first, from the main checkout; Claude asks before each live run and before pushing). Deferred, not in this round: #68, #69, #70, #72, #100. After the round: #144 (record context-level passes automatically) and #145 (check that a fresh clone builds on another computer).

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

### #75 Android External suite with a funded test account (in build)

- **Step 1:** `/ticket-start 75` (already done).
- **Step 2 block** (paste under the printed prompt):

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
  -gpu swangle_indirect` (the AVD's default host graphics caused the aborts #127
  traced), wait for `sys.boot_completed`, and kill it when you are done.
- Live runs: acceptance criterion 1 names `.\test-weekly.ps1`, which makes two paid
  Claude scans. Ask the owner with AskUserQuestion to confirm the two paid scans
  (ceiling 2 paid calls) before you run it; never run it without that answer.
  Do not commit any change to `scripts/dashboard_data/external_status.json` or
  `dashboard.svg` from the ticket branch.
```

- **If #75 was already started with the generic "No live or paid runs" line** (the old version of this page said that for every ticket): tell the session "Exception for this ticket: criterion 1 names the live run. Ask me with AskUserQuestion to confirm the two paid scans, then run `.\test-weekly.ps1` with a ceiling of 2 paid calls." Without the run it will finish as `PARTIAL` on criterion 1, which you can accept at merge with `--allow-status` and run later.
- **Your part:** confirm the two paid scans when the session asks. Check that `WEB_EXTERNAL_TEST_EMAIL` and `WEB_EXTERNAL_TEST_PASSWORD` are set in the environment or in `web/.env.local` (`/ticket-start` copies `web/.env.local` into the worktree); a missing value fails the run naming the variable.
- **Merge note:** the review does not run paid scans. It re-runs the free tests and checks the rest by reading.

### #39 RevenueCat Android SDK surface

- **Step 1:** `/ticket-start 39`. Only one Android ticket may be in flight; start it after #75 is merged.
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
- No Android External runner exists yet: this ticket adds the first one, and #40
  will reuse it. Keep it small and documented, and say in the STATUS how the
  wrapper requires a device.
- Live runs: do not run the live External suite or any paid call. The owner runs
  the surface from the main checkout after the merge. Do not commit changes to
  `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
```

- **Your part:** after the merge, run the new Android External runner the ticket documents (it needs the emulator; Claude can start and run it with your go-ahead and a paid-call ceiling if the ticket's maximum is above 0).

### #40 Google Play Billing surface

- **Step 1:** `/ticket-start 40 --android` (its text names neither Android nor an `android/` path, so `/ticket-start` needs the flag). Start it after #39 is merged.
- **Step 2 block:** the same as #39's, with the runner line replaced by:

```
- Reuse the Android External runner #39 added; do not write a second one. The
  emulator image is `google_apis_playstore`, so Play Services is available.
```

- **Your part:** after the merge, the live run as for #39.

### #105 prove the RevenueCat `pro` entitlement

- **Before step 1 (your part):** in the RevenueCat dashboard (sandbox project), grant the `pro` entitlement as a promotional, non-expiring entitlement to the app user id `external-suite-pro`. No purchase. It is unverified that the sandbox customer page offers a promotional grant; if it does not, tell the session when it asks, because the ticket then needs another way to give a fixture user `pro`.
- **Step 1:** `/ticket-start 105`.
- **Step 2 block:**

```
Test-round additions:
- For a full Python run use `uv run pytest -n auto --maxprocesses=8` (about 45 s).
  The slow tooling tests are left out of planner runs unless the diff touches
  what they check.
- Judge each test by whether it would find or prevent a real bug and whether it
  adds run time; do not add tests only to raise a coverage number.
- Live runs: do not run the live External suite. It is free, and the owner runs it
  from the main checkout after the merge (`powershell web\test-external.ps1`).
  Do not commit changes to `scripts/dashboard_data/external_status.json` or
  `dashboard.svg` from the branch.
```

- **Your part after the merge:** the free live run of `powershell web\test-external.ps1` (Claude can run it with your go-ahead).

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
- Set the `medium_phone` AVD's Graphics to Software in Device Manager (`G:\Android\EmulatorHome\avd\medium_phone.avd\config.ini`, `hw.gpu.mode`). Not yet confirmed done. The `-gpu swangle_indirect` start line above does not depend on it; a plain `gradlew connectedDebugAndroidTest` or `android/release.ps1` against a default-graphics emulator can still abort.
- An emulator that `android_suite_loop.py` or a session started holds its `emulator.log` open and blocks deleting the ticket folder after `/ticket-merge`: step 6 above.
- If an assigned ticket is wrongly counted as holding the emulator (its title says Android but it never uses it), start the next with `--emulator-free <M>` naming it.
- Paid prompts from a non-interactive shell: `cmd /c "echo y| powershell -NoProfile -File workers\scan-proxy\test-external.ps1 -MaxPaidCalls N"` (piping several `'y'` lines from PowerShell declines the first prompt and records `skipped`, which spends nothing and leaves the surface stale). Claude does this, with your ceiling.
- The planner treats `*.md`, `docs/*` and `ClaudePlans/*` as docs-only (plans nothing), follows `shares_with` and `depends_on` links to downstream contexts, and does not list a deleted test file. Config choices on #66 are recorded in its DECISIONS comment.
- Open follow-up from the #130 merge: one more test case for the prefix-matching direction in `scripts/coverage_lib.py` (allow `ScanApiClient`, leave `ScanApiClientKt` unlisted); add it when a ticket next touches that file.

## History (for reference; nothing to do)

- **Merged:** #134, #129, #130, #41, #128, #43, #127, #66, #44, #84, #115, #135, #124, #136, #142, #131, #133, #143, #137, #67 (#141 closed as its duplicate). Follow-ups filed along the way: #138 (Worker preview deploy), #139 (cache the gate's registry lookups), #140 (Streamlit `FIELDS` vs the Claude extractor keys), #144, #145.
- **Pushed** up to d0ea7b7 on 2026-10-20 (plus handoff-note commits), including #115's changed Web scan wording, which the owner approved.
- **External runs, owner-approved:** 2026-10-19 sanity run of seven stale surfaces (4 paid calls; commit 95ae133); 2026-10-20 re-run of `pages-site` and `scan-proxy-worker` after a wrangler release (1 paid call); 2026-10-20 first runs of `anthropic` (Worker) and `anthropic-python` (6 paid calls, commit 615e552), both against `test-vectors/vision_external_cases.json` and `ExampleDocs/golden_fields.json`. All passed.
- **Verification debt (#67):** a committed SessionStart hook in `.claude/settings.json`; all five contexts have a recorded pass from 2026-10-20 at d0ea7b7 (a new machine or fresh clone needs the one-time commands in [verification-debt.md](verification-debt.md) again; #144 will automate it).
