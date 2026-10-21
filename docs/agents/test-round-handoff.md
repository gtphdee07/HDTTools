# Test-first round: your run sheet

Working notes for the test-first round (map #49, decisions on #58 and #59). They are temporary: delete this file when the round ends. The general ticket flow is in [ticket-skills.md](ticket-skills.md). **This page is the run sheet: for any ticket, read "How to run one ticket" and then that ticket's card. Everything you copy, type or decide for that ticket is on its card; nothing needs to be looked up elsewhere on this page.** Only work that is not done is on this page; finished tickets are in their closing comments and in the History line at the end.

## What is left, in order

The round's tickets are merged and pushed. What is left is epic #147's tree (below) and the optional #132. #164 is the last check; #161 starts only after it is merged, so it is cut from the updated `MPSkills`. Start the next only after the previous one is merged, so it is cut from the updated `MPSkills`.

| # | What | Kind | Your part | Card |
|---|---|---|---|---|
| 1 | #164 Android checks its scan fields against the fixture | one new JVM test | none | [#164](#164-android-checks-the-fixture) |
| 2 | #161 the planner names all the field checks when a shared vision fixture changes | planner config | none | [#161](#161-planner-names-the-field-checks) |
| then | I close epic #147 with a comment; nothing for you to type | | | |
| optional | #132 is mutation testing worth running? (research) | research, no code change | none | [#132](#132-optional-mutation-testing-research) |

Do not run Gradle in two sessions at once with the emulator up: the machine runs out of memory (see "Things to remember"). The final External run is done (2026-10-21, see History); if #132 changes no code there is nothing more to run, and any later change to a boundary file or pin needs `uv run scripts/external_freshness.py` first.

Not in this round: #40 (blocked on Play Console, see its card), #68, #69, #70, #72, #100. After the round: #144 (record context-level passes automatically), #145 (check that a fresh clone builds on another computer), #146 (check that `pro` is attached to the Pro product), #155 to #159 (static-check gaps: a Python type checker, a shell and PowerShell linter, the Python coverage floor, a Web coverage floor, Android Lint and config files), #138 and #139.

## How to run one ticket

The same six steps every time. The card for the ticket gives the exact command for step 1 and the exact text for step 2.

1. **Start** (this main-checkout session, or any terminal in the main checkout): type the card's `/ticket-start` line. It creates `.claude/worktrees/ticket-N` and prints a paste-ready prompt.
2. **Build**: open a **new** `claude` session in `.claude/worktrees/ticket-N`. Paste the printed prompt as the first message, then paste the card's block directly under it (one message, nothing else added). A new session for every ticket.
3. **Finish**: when the build session says it is done, type `/ticket-finish` in the same session. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**, so the folder can be removed at merge.
4. **Merge**: back in the main checkout session, type `/ticket-merge N` (add `--allow-status` only to go past a `PARTIAL` you have decided to accept). Claude carries out the review: ledger check, reading the diff, mutation checks, merge, closing comment. If it finds a gap (a test, a testing-document row, a planner-config entry) it asks to add it on the branch and merges after you agree.
5. **Push**: Claude asks first, every time. The pre-push gate refuses a push that touches `web/`, `workers/scan-proxy/` or `android/` while an External surface is stale (`uv run scripts/external_freshness.py` says which); the honest way through is a real run (Claude runs the stale suites from the main checkout, asking for a paid-call ceiling first).
6. **Clean up after an Android ticket**: stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe emu kill`) and close any terminal still open in the ticket's folder, then `rmdir` the leftover `.claude/worktrees/ticket-N` if `/ticket-merge` says it could not remove it.

A session-start report (verification debt, #67) prints when each session opens. With the five contexts recorded it says there is nothing to report; it is advisory and you do nothing with it.

## Run cards

### #162 (merged 2026-10-21)

Done: `test-vectors/scan_form_fields.json` (per doc type, the `scanned` and `manual_only` fields with a `text` or `number` type) and the Python tests that check it against the tool schema and Streamlit's `FIELDS`; `CONTEXT-MAP.md` names it. #163 and #164 are now unblocked.

### #163 (merged 2026-10-21)

Done: `web/src/scanFormFields.test.ts` checks every `MODULES` field (name and type) and the optional flags against the shared `scan_form_fields.json`.

### #164 Android checks the fixture

- **Step 1:** `/ticket-start 164` (#162 is merged). Add `--not-android` if another Android ticket is running; this one needs no emulator.
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
- A new test file must be named in its context's testing document, and a new
  `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Do not edit `android/app/build.gradle.kts`: it pins an External surface.
- No live or paid runs.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->`
  markers.
```

- **Your part:** none beyond the usual steps. Last of the three checks; #161 follows it.

### #161 planner names the field checks

- **Step 1:** `/ticket-start 161` (after #162, #163 and #164 are merged; GitHub blocks it until then). Last ticket of the tree.
- **Step 2 block:**

```
Test-round additions:
- For a full Python run use `uv run pytest -n auto --maxprocesses=8` (about 45 s).
  The slow tooling tests are left out of planner runs unless the diff touches
  what they check.
- Judge each test by whether it would find or prevent a real bug and whether it
  adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in its context's testing document, and a new
  `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Only `scripts/test_planner_config.json` and the planner's tests change.
- No live or paid runs.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->`
  markers.
```

- **Your part:** none beyond the usual steps. After it merges, ask Claude to close epic #147.

### #132 (optional) mutation-testing research

- **Step 1:** `/ticket-start 132`. Lowest priority; production code is not changed. Skip it if the round is running long.
- **Step 2 block:**

```
Test-round additions:
- Research only: write one file under `docs/research/` and change no production code.
- No live or paid runs.
```

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
- Reuse the Android External runner (`android\test-external.ps1`,
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

## Things to remember

- `--maxprocesses=8` caps `-n auto` because 24 workers ran this machine out of memory. Even at 8, the Python suite occasionally errors in tests that create a real git repo (`git init` or `git worktree add` exits 3221225773 or "WinError 1455: paging file too small") when the emulator, Gradle and other sessions are up (about 3 in 16 runs). It is memory, not a regression; re-run.
- The `medium_phone` AVD's Graphics is Software (set 2026-10-21). The `-gpu swangle_indirect` start line in the cards stays and does not depend on it.
- An emulator that `android_suite_loop.py` or a session started holds its `emulator.log` open and blocks deleting the ticket folder after `/ticket-merge`: step 6 above. Empty leftover folders from earlier tickets (`.claude/worktrees/ticket-137`, `ticket-140`, `ticket-148`, `ticket-40` and others) can be removed with `rmdir` once no terminal is open in them.
- Paid prompts from a non-interactive shell: `cmd /c "echo y| powershell -NoProfile -File workers\scan-proxy\test-external.ps1 -MaxPaidCalls N"` (piping several `'y'` lines from PowerShell declines the first prompt and records `skipped`, which spends nothing and leaves the surface stale). Claude does this, with your ceiling.
- Every new test file must be named in its context's testing document, and every new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise. Build sessions have missed this twice, so the merge review adds the row or entry and asks first.
- The planner treats `*.md`, `docs/*` and `ClaudePlans/*` as docs-only (plans nothing), follows `shares_with` and `depends_on` links to downstream contexts, and does not list a deleted test file. Config choices on #66 are recorded in its DECISIONS comment.
- Open follow-up from the #130 merge: one more test case for the prefix-matching direction in `scripts/coverage_lib.py` (allow `ScanApiClient`, leave `ScanApiClientKt` unlisted); add it when a ticket next touches that file.
- Keep the `external-suite-pro` RevenueCat grant non-expiring or far-dated (the Web External suite depends on it).

## History (for reference; nothing to do)

- **Merged in the round:** #134, #129, #130, #41, #128, #43, #127, #66, #44, #84, #115, #135, #124, #136, #142, #131, #133, #143, #137, #67, #75, #39, #105, #64, #140, #148, #152, #151, #150, #153, #160, #149, #162, #163 (#141 closed as a duplicate, #154 as a duplicate of #153).
- **Pushed** up to 1f60cc3 on 2026-10-21 (the whole round, with the External pass records).
- **Final External run, 2026-10-21 (ceiling 10, 7 paid calls used):** `pages-site` (9 tests), `anthropic` (5), `scan-proxy-worker` (7), `worker-token-verification` (5), `anthropic-python` (5), `revenuecat-android-sdk` (6); all passed and all ten active surfaces are fresh.
- **External runs, owner-approved:** 2026-10-19 sanity run of seven stale surfaces; 2026-10-20 and 2026-10-21 re-runs and the first runs of `anthropic`, `anthropic-python`, the Android SDK surface and the Pro entitlement test; all passed, with the records in `scripts/dashboard_data/external_status.json`.
- **Verification debt (#67):** a committed SessionStart hook in `.claude/settings.json`; all five contexts have a recorded pass (a new machine or fresh clone needs the one-time commands in [verification-debt.md](verification-debt.md) again; #144 will automate it).
