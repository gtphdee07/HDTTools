# Test-first round: your run sheet

Working notes for the test-first round (map #49, decisions on #58 and #59). They are temporary: delete this file when the round ends. The general ticket flow is in [ticket-skills.md](ticket-skills.md). **This page is the run sheet: for any ticket, read "How to run one ticket" and then that ticket's card. Everything you copy, type or decide for that ticket is on its card; nothing needs to be looked up elsewhere on this page.** Only work that is not done is on this page; finished tickets are in their closing comments and in the History line at the end.

## What is left, in order

The test round and the truck GCWR chain are done and pushed. The work now is the **shared accounts chain** (epic #15): #146 and #29 are merged and pushed (cf305df); #31 is merged and pushed (6ab852d), and #32 is merged and pushed (04490db; the Android lane is done); #101 and #20 are merged and pushed (bd69ac0); #27 and #30 are merged and pushed (6ea870c). The live `revenuecat-rest` check passed (the `pro` entitlement has the Web paywall's product attached), so all push gates are clear. Claude asks before each push (Web goes live on a push).

Order of the table: a row starts when the ticket it names has merged. #20 was narrowed to Google only (Apple stays with #77). Web goes live on every push of `MPSkills`, so Claude asks first, and runs the stale External suites before the push.

| # | What | Kind | Your part | Card |
|---|---|---|---|---|
| optional | #132 is mutation testing worth running? (research) | research, no code change | none | [#132](#132-optional-mutation-testing-research) |

#46 and #47 can build at the same time (different surfaces, and only #47 touches the emulator). Do not run Gradle in two sessions at once with the emulator up: the machine runs out of memory (see "Things to remember"). The final External run is done (2026-10-21, see History); if #132 changes no code there is nothing more to run, and any later change to a boundary file or pin needs `uv run scripts/external_freshness.py` first.

Not in this round: #40 (blocked on Play Console, see its card), #68, #69, #70, #72, #100. After the round: #144 (record context-level passes automatically), #145 (check that a fresh clone builds on another computer), #146 (check that `pro` is attached to the Pro product), #165 (TESTING.md: name the scan-form-fields planner interface), #155 to #159 (static-check gaps: a Python type checker, a shell and PowerShell linter, the Python coverage floor, a Web coverage floor, Android Lint and config files), #138 and #139.

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

### #45 (merged 2026-10-22)

Done: the truck GCWR in the core math, the Verdict rule, the shared fixture (`test-vectors/breakdown_cases.json`, 7 new `gcwr_*` cases) and the Streamlit field. Until #46 and #47 merge, Web's and Android's golden-vector tests fail on `MPSkills` by design; **nothing is pushed until both are merged.** Your decision: the caveat clause shows whenever the Combined row was not checked (recorded on #46 and #47).

### #46 (merged 2026-10-22)

Done: Web's optional GCWR field, hint and below-GVWR warning, the TypeScript breakdown and Verdict following the shared fixture, and the Rig round trip.

### #47 (merged 2026-10-22)

Done: Android's optional GCWR field, hint and below-GVWR warning, the Kotlin breakdown and Verdict following the shared fixture, and the Rig round trip. The fixture now passes in Python, Web and Android.

### #168 (merged 2026-10-22)

Done: Android's Results screen shows the Verdict subline under the headline in the verdict pill, so the GCWR caveat is visible there as on Web. The pill is now a full-width row (20 dp corners): look at it on a device if the look matters.

### #146 (merged 2026-10-22)

Done: the Worker External test that checks the `pro` entitlement has the Web paywall's product attached, read with the second read-only key (`REVENUECAT_CONFIG_READ_KEY`). Run live on 2026-10-22: 11 of 11 passed (free), so the dashboard attachment is proven.

### #29 (merged 2026-10-22)

Done: History sync on Web (migration `20261022000000_history_entries.sql` applied by you; the live `supabase-tables` suite passed 18 of 18, and `pages-site` 9 of 9). Two tests for the late-reply guards were added after the merge.

### #30 (merged 2026-10-22)

Done: Pro raises the Garage and History caps (Free 5 Rigs / 10 checks, Pro 25 / 50 as placeholders in the `plan_caps` table), with an upgrade prompt. The app reports the plan to the database (your decision). You applied `supabase/migrations/20261023000000_plan_caps.sql`, the live `supabase-tables` suite passed (20/20) and the push is out (6ea870c).

### #20 (merged 2026-10-22)

Done: "Continue with Google" on Web (sign in and create account), PKCE, errors in the usual style, and a failed Google return is named as Google's. Your by-hand check on the local dev server showed email and Google reach the same account. The live `supabase-auth` suite passed (9/9, including the Google first hop). **Still yours, after the push:** try Continue with Google once on https://rigcheck-web.pages.dev (if you land back signed out with the Google message, add `https://rigcheck-web.pages.dev/**` to the Supabase Redirect URLs); if the Google consent screen is in Testing mode, each tester's Google account must be a test user. The folder `.claude/worktrees/ticket-20` could not be deleted because a node process (probably your dev server from the Google check) still holds it; stop it, then run `cmd /c rmdir /s /q "\\?\G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-20"`.

### #27 (merged 2026-10-22)

Done: Android shows the account's plan (Pro or Free, from the `pro` entitlement, so a Pro bought on Web counts) on the Paywall, and a cross-surface test pins the SCAN currency and the entitlement across the Worker, Android and Web. Checked read-only: the Android Test Store `lifetime` product and the Web product are both attached to `pro`. **Still yours:** confirm the Pro price is the same on both products (ADR-0006); a real two-client purchase and balance check; look at the new plan line on the Paywall on a device.

### #101 (merged 2026-10-22)

Done: the Android Paywall offers Pro (and no packs) to a Free account and the scan packs (and not Pro) to a Pro account, told apart by the package type RevenueCat reports. Checked read-only: the default Offering has the `$rc_lifetime` package (Web and Android Test Store products, both on `pro`) and one Android pack (`consumable`). **Still yours:** on a device, buy Pro and confirm the starter scans are in the balance (the real purchase chain is not automated); look at the "Unlock Pro" and packs screens. The Android External suite runs at the next bundle (two of its tests now render the Paywall as Pro).

### #31 (merged 2026-10-22)

Done: Android reads and writes the account's Garage (the same Rigs as Web, the plan's cap enforced by the database, a retried add creates one Rig), with a notice and a Pro offer on the Results screen when the Garage is full. The full instrumented suite (174) passes on the merged tree. **Still yours:** on a device, add a Rig on Web and see it in the Android picker; finish a check with a full Garage and look at the notice. Follow-ups filed: #169 (delete a Rig on Android), #170 (import the phone's Rigs on first sign-in), #171 (live External coverage of Android's Garage client; decide before an Android release).

### #32 (merged 2026-10-23)

Done: Android has a History screen over the account's History (the same checks as Web, newest first, the plan's cap enforced by the database), each finished check is saved once, and a Free account at the cap is told what each plan keeps. The full instrumented suite (184) passes on the merged tree. **Still yours:** a by-hand round trip on the real project (finish a check on Android and see it in Web's History, then the other way round); decide the date question in #172 (Web shows UTC, Android the phone's local day); triage #173 (Android History filters).

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

- **Merged in the round:** #134, #129, #130, #41, #128, #43, #127, #66, #44, #84, #115, #135, #124, #136, #142, #131, #133, #143, #137, #67, #75, #39, #105, #64, #140, #148, #152, #151, #150, #153, #160, #149, #162, #163, #164, #161 (epic #147 closed; #141 closed as a duplicate, #154 as a duplicate of #153).
- **Pushed** up to 18dfb8a on 2026-10-22 (also the security follow-ups #166 and #167 and the truck GCWR chain #45, #46, #47 and #168, with their External pass records; the earlier push, up to 1f87869 on 2026-10-21, was the whole round, epic #147, and the External pass records; a second External run that day re-passed `anthropic` and `anthropic-python` for new SDK releases, 6 paid calls).
- **Final External run, 2026-10-21 (ceiling 10, 7 paid calls used):** `pages-site` (9 tests), `anthropic` (5), `scan-proxy-worker` (7), `worker-token-verification` (5), `anthropic-python` (5), `revenuecat-android-sdk` (6); all passed and all ten active surfaces are fresh.
- **External runs, owner-approved:** 2026-10-19 sanity run of seven stale surfaces; 2026-10-20 and 2026-10-21 re-runs and the first runs of `anthropic`, `anthropic-python`, the Android SDK surface and the Pro entitlement test; all passed, with the records in `scripts/dashboard_data/external_status.json`.
- **Verification debt (#67):** a committed SessionStart hook in `.claude/settings.json`; all five contexts have a recorded pass (a new machine or fresh clone needs the one-time commands in [verification-debt.md](verification-debt.md) again; #144 will automate it).
