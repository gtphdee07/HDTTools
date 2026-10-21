# Test-first round: your run sheet

Working notes for the test-first round (map #49, decisions on #58 and #59). They are temporary: delete this file when the round ends. The general ticket flow is in [ticket-skills.md](ticket-skills.md). **This page is the run sheet: for any ticket, read "How to run one ticket" and then that ticket's card. Everything you copy, type or decide for that ticket is on its card; nothing needs to be looked up elsewhere on this page.** Only work that is not done is on this page; finished tickets are in their closing comments and in the History line at the end.

## What is left, in order

The only build tickets left are #149 and the optional #132. Start the next only after the previous one is merged, so it is cut from the updated `MPSkills`.

| # | What | Kind | Your part | Card |
|---|---|---|---|---|
| 1 (any time) | #149 Android scan field keys against the shared tool schema | one new JVM test, a row in `android/TESTING.md` | none | [#149](#149-android-scan-field-keys-against-the-shared-tool-schema) |
| optional | #132 is mutation testing worth running? (research) | research, no code change | none | [#132](#132-optional-mutation-testing-research) |
| 3 | The final External run, then one push | live runs, asks you first | give a paid-call ceiling and go-ahead | [Final External run and push](#final-external-run-and-push) |
| later | #147 the field-name epic | three decisions, one `CONTEXT-MAP.md` line | decide with Claude after #149 | [#147](#147-the-epic-not-built-as-a-ticket-now) |

#149 touches only `android/TESTING.md` and a new test. `/ticket-start` counts any Android ticket as holding the emulator; #149 is JVM-only, so if another Android ticket is running when you start it, add `--not-android`. Do not run Gradle in two sessions at once with the emulator up: the machine runs out of memory (see "Things to remember").

Not in this round: #40 (blocked on Play Console, see its card), #68, #69, #70, #72, #100. After the round: #144 (record context-level passes automatically), #145 (check that a fresh clone builds on another computer), #146 (check that `pro` is attached to the Pro product), #155 to #159 (static-check gaps: a Python type checker, a shell and PowerShell linter, the Python coverage floor, a Web coverage floor, Android Lint and config files), #138 and #139.

## How to run one ticket

The same six steps every time. The card for the ticket gives the exact command for step 1 and the exact text for step 2.

1. **Start** (this main-checkout session, or any terminal in the main checkout): type the card's `/ticket-start` line. It creates `.claude/worktrees/ticket-N` and prints a paste-ready prompt.
2. **Build**: open a **new** `claude` session in `.claude/worktrees/ticket-N`. Paste the printed prompt as the first message, then paste the card's block directly under it (one message, nothing else added). A new session for every ticket.
3. **Finish**: when the build session says it is done, type `/ticket-finish` in the same session. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**, so the folder can be removed at merge.
4. **Merge**: back in the main checkout session, type `/ticket-merge N` (add `--allow-status` only to go past a `PARTIAL` you have decided to accept). Claude carries out the review: ledger check, reading the diff, mutation checks, merge, closing comment. If it finds a gap (a test, a testing-document row, a planner-config entry) it asks to add it on the branch and merges after you agree.
5. **Push**: not per ticket for now. See "Final External run and push" below.
6. **Clean up after an Android ticket**: stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe emu kill`) and close any terminal still open in the ticket's folder, then `rmdir` the leftover `.claude/worktrees/ticket-N` if `/ticket-merge` says it could not remove it.

A session-start report (verification debt, #67) prints when each session opens. With the five contexts recorded it says there is nothing to report; it is advisory and you do nothing with it.

## Run cards

### #149 Android scan field keys against the shared tool schema

- **Step 1:** `/ticket-start 149` (add `--not-android` if it says another Android ticket holds the emulator; this one needs no emulator).
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

### #132 (optional) mutation-testing research

- **Step 1:** `/ticket-start 132`. Lowest priority; production code is not changed. Skip it if the round is running long.
- **Step 2 block:**

```
Test-round additions:
- Research only: write one file under `docs/research/` and change no production code.
- No live or paid runs.
```

### #147 (the epic): not built as a ticket now

It is labelled `needs-triage` and carries three decisions for you (whether a shared `scan_form_fields.json` fixture is added, whether field types are pinned, and its close gate). Its children #140 and #148 are merged and #149 is above; none of them needs those answers. Once #149 is merged, the decisions are a short conversation with Claude in the main session, and the only edit left is one line in `CONTEXT-MAP.md`. If you answer "add the shared fixture", that becomes a new ticket touching all three surfaces, and it should wait until the rest of the round is finished.

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

## Final External run and push

Nothing has been pushed since a76a31f: `MPSkills` is 20 commits ahead of `origin/MPSkills`, and 9 changed files are under `web/`, `workers/scan-proxy/` or `android/`. The pre-push gate refuses that push while External surfaces in those platforms' chains are stale, so everything goes up in one push after the run below (pushing also rebuilds Web, which this push changes in tests and documents only, plus `web/vite.config.ts`).

Stale now (`uv run scripts/external_freshness.py`, 2026-10-21), and why:

| Surface | Why stale | Cost | How it runs |
|---|---|---|---|
| `anthropic` (Worker) | `@anthropic-ai/sdk` 1.0.0 published after the last pass; its pins also changed (#160) | 3 paid calls | Worker wrapper `workers\scan-proxy\test-external.ps1 -MaxPaidCalls N` |
| `anthropic-python` | `anthropic` 2.0.0 published after the last pass; `pyproject.toml` and `uv.lock` also changed (#160) | 3 paid calls | the Python vision test, shared golden data with the Worker's |
| `pages-site` | `web/vite.config.ts` changed (a lint fix from #150) | free | `web\test-external.ps1` |
| `revenuecat-android-sdk` | `com.revenuecat.purchases:purchases` 10.29.0 published | free; needs one emulator with Google Play Services | `android\test-external.ps1` |
| `scan-proxy-worker` and `worker-token-verification` | `workers/scan-proxy/package.json` changed on purpose (#160: ruff and oxlint moved into the lockfiles) | 1 paid call and free | the Worker wrapper, same run as `anthropic` |

Suggested ceiling: 7 paid calls (3 + 3 + 1). Order: build #149 (and #132 if you want it) first, so one run covers everything. Then:

1. Run `uv run scripts/external_freshness.py` in the main checkout and compare with the table (registries can publish new versions at any time).
2. Tell Claude "run the External suites" and give the paid-call ceiling. Claude asks, runs from the main checkout (starting the emulator for the Android surface), and commits the pass records in `scripts/dashboard_data/external_status.json`. A new major SDK version may fail; that is worth learning before the push depends on it.
3. Claude re-runs `external_gate.py check` for web, scan-proxy and android right before asking to push, then asks. Answer once; it pushes the whole branch.

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

- **Merged in the round:** #134, #129, #130, #41, #128, #43, #127, #66, #44, #84, #115, #135, #124, #136, #142, #131, #133, #143, #137, #67, #75, #39, #105, #64, #140, #148, #152, #151, #150, #153, #160 (#141 closed as a duplicate, #154 as a duplicate of #153).
- **Pushed** up to a76a31f on 2026-10-21; later commits are local.
- **External runs, owner-approved:** 2026-10-19 sanity run of seven stale surfaces; 2026-10-20 and 2026-10-21 re-runs and the first runs of `anthropic`, `anthropic-python`, the Android SDK surface and the Pro entitlement test; all passed, with the records in `scripts/dashboard_data/external_status.json`.
- **Verification debt (#67):** a committed SessionStart hook in `.claude/settings.json`; all five contexts have a recorded pass (a new machine or fresh clone needs the one-time commands in [verification-debt.md](verification-debt.md) again; #144 will automate it).
