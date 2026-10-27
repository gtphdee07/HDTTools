# Alpha round: your run sheet

Working notes for the Alpha round ([BETA_PLAN.md](../BETA_PLAN.md)). They are temporary: delete this file when the round ends. The general ticket flow is in [ticket-skills.md](ticket-skills.md). **Each ticket's card below is complete: the box on it is the whole first message for the build session (the `/mattpocock-skills:implement` line, the handoff text and the test-round additions), and the numbered steps give every command, in order.** Only work that is not finished is on this page; finished tickets are in their closing comments.

## Where things stand (2026-10-27)

- Merged and not yet pushed (52 commits ahead of `origin/MPSkills`, last push 8d91a96): #179, #174 with its #185 fix, #181, #186, #169, #180, #182, #183, and the redesign brief and plan edits. Pushes are checkpoints: Claude asks after #189 and again at the end (see "Pushes").
- **Lane A:** nothing is running; #184 is next. **Lane B:** has nothing left but the optional #132.
- Your phone (SM-G996U, adb name `R3CR50G10ML`) has the beta build, versionCode 3. The emulator is `emulator-5554`. Name the one you mean in every adb command.
- The Android re-skin (epic #187) happens before the Alpha: the tester APK is built only after #197 and your sign-off.

## The tickets, in order

Two lanes, one build session each, a **new** session for every ticket. Lane A is Android and runs one ticket at a time (one emulator). Lane B is Web, Worker and tooling (no emulator, no Gradle) and runs beside lane A.

| # | Ticket | Lane | Starts when | Your part |
|---|---|---|---|---|
| 1 | [#184](#184-android-crash-capture) Android crash capture | A | nothing blocks it | none |
| 2 | [#188](#188-a-test-tag-on-every-android-ui-element-redesign-step-1) A test tag on every UI element | A | #184 merged | none |
| 3 | [#189](#189-baseline-screenshots-and-measured-bounds-redesign-step-2) Baseline screenshots (emulator alone) | A | #188 merged | copy the PNGs for the designer |
| 4 | [#190](#190-the-design-round-yours-no-build-session) The Claude Design round | you | #189 merged | the whole ticket |
| 5 | [#191](#191-theme-tokens-and-shared-components-from-the-design) Theme, tokens, shared components | A | #190 committed | none |
| 6 to 10 | #192 to #196 re-skin: [Rig picker and Chooser](#192-re-skin-the-rig-picker-chooser-and-photo-source-dialog), [entry screens](#193-re-skin-the-truck-tag-trailer-tag-and-scale-ticket-entry-screens), [Disclaimer and Results](#194-re-skin-the-disclaimer-and-results-screens), [History](#195-re-skin-the-history-screen), [Paywall, Account, dialogs](#196-re-skin-the-paywall-account-and-the-two-scan-dialogs) | A | #191 merged | compare with the designer's picture on your phone |
| 11 | [#197](#197-final-pass-and-sign-off) Final pass and sign-off | A | #192 to #196 merged | check every screen, sign off |
| optional | [#132](#132-optional-is-mutation-testing-worth-running-research) Is mutation testing worth running? | any | any time | none |

A ticket starts when the tickets it waits for have merged, not when the round ends. Decisions for all of them are already recorded in DECISIONS comments, so the workers do not ask again.

**How the two lanes stay out of each other's way**
- **Memory:** only lane A may use the emulator or Gradle. Lane B runs vitest, node and pytest only. If the machine runs short of memory, pause lane B.
- **Same files:** `docs/BETA_TESTER_GUIDE.md` (#184 adds a line), `scripts/test_planner_config.json` (any new slow test). Claude merges one ticket at a time and settles any text clash at the merge; the second ticket of a pair may need a refresh onto the new baseline, and Claude says so.
- **Merge order between lanes:** whichever worker finishes first.

## Pushes and External runs

- **Pushes:** a checkpoint push after #189 has merged (before the design round) and a final push at the end. Claude asks before each. Web goes live on each push; with no testers yet that is harmless, and the remote then holds a copy of the work.
- The pre-push gate refuses a push that touches `web/`, `workers/scan-proxy/` or `android/` while an External surface is stale (`uv run scripts/external_freshness.py` says which). Claude runs the stale suites from the main checkout first, asking for a paid-call ceiling before any paid run: `revenuecat-android-sdk` (free; stale since #174; needs the emulator, so no Android ticket may be running, #189 included), `pages-site` (free; `web/.env.production` changed) and `anthropic-python` (free; new SDK releases). `scan-proxy-worker` and `anthropic` were run live on 2026-10-27 after the forced Worker deploy and passed (4 paid calls), so the Worker gate is clear.
- Do not invite testers before the final push and the owner steps below are done.

## Owner steps, in the order they come up

- [x] Signing values in `G:\GradleUserHome\gradle.properties`, APK built, fingerprint matches the notes file, installed on the phone, Google sign-in works (done 2026-10-27; the phone has versionCode 3).
- [x] #186 checked on the phone: the Paywall, the Create button, History and the Truck Tag keyboard (done 2026-10-27).
- [x] The grant tool ran live on one test account (2026-10-27): RevenueCat shows the Pro entitlement (display name "Rig Check Pro", lookup key `pro`, expires in a year) and 20 scans.
- [ ] Run the grant tool for each real tester (dry run, then `--apply`; the account id is in the Supabase dashboard, Authentication, Users; steps in `docs/BUILD_AND_DEPLOY.md`, "Granting a tester"). Leave one tester on Free so someone tests buying Pro.
- [x] #183: the Worker was redeployed (forced, with a recorded reason) and the live suites passed on 2026-10-27.
- [ ] Open the Cloudflare logs once (Workers & Pages, rigcheck-scan-proxy, Logs) and look for a `"event":"scan"` line (the live suite's scans wrote some).
- [ ] #182 has merged (Send feedback on the Rig picker and the sign-in screen; "Beta: test payments" on the Paywall; the phone shows them after the rebuilt APK). After #184: read `docs/BETA_TESTER_GUIDE.md` once, check its Android steps against the real app, and send yourself a feedback email from each app. Decide the guide's wording "No limit on how many scans one account can make" (a tester's scan balance still runs out; "no daily limit" is closer).
- [ ] After #189 merges: run the design round (#190) as its card says, and commit the hand-back.
- [ ] On each re-skin ticket (#192 to #196): compare the screenshot in the STATUS comment with the designer's picture on your phone before Claude merges it. On #197, check every screen and sign off.
- [ ] After #197: build the tester APK with a higher `-PappVersionCode` (4 or more; raise it for every APK you send), from `android`: `.\gradlew.bat assembleBeta -PappVersionCode=<n>`. Confirm `keytool -printcert -jarfile app\build\outputs\apk\beta\app-beta.apk` shows the SHA-1 in `G:\Secrets\rigcheck\rigcheck-upload-keystore-NOTES.txt`.
- [ ] Before inviting: add each Alpha tester's Gmail as a Google test user (up to 5); send the APK and the guide.
- [ ] Device checks still open from earlier tickets: add a Rig on Web and see it in the Android picker; finish a check with a full Garage and look at the notice; finish a check on Android and see it in Web's History, then the other way round; compare a History date on the phone with the same entry on Web; delete a Rig on the phone (the bin on its card) and check it is gone on Web, then delete one on Web and check the phone's picker drops it after a refresh (#169 never ran against the live project); on the phone buy Pro with the Test Store and confirm the starter scans arrive.
- [ ] Confirm the Pro price is the same on both products (ADR-0006).
- [ ] Triage #173 (Android History filters); decide #171 (live External coverage of the Android Garage client) before an Android release.
- [ ] Clean up: `.claude/worktrees/ticket-20`, `-40`, `-137`, `-140`, `-148` and `-186` are leftover folders, not worktrees. Close any dev server or terminal still holding them, then ask Claude to check and remove them (the ticket-20 one was held by a node process).

Not in this round: #40 (Google Play Billing; blocked until a Play Console account exists, see the ticket's DECISIONS and `STATUS: BLOCKED`; ask Claude to rebuild its card when you restart it), #68, #69, #70, #72, #100, #170, #172, #175, #177. After the round: #144, #145, #146, #165, #155 to #159, #138 and #139.

## Run cards

### #184 Android crash capture

**Lane A, next.** Nothing blocks it. Android: the single emulator, one Android ticket at a time.

1. In this main-checkout session type `/ticket-start 184`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-184`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-184` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-184"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #184

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The Android end-of-session command is `uv run scripts/android_session_end.py` (JVM tests, coverage floor, detekt; no device).
- A UI test needs the single emulator; no other Android ticket may be running. Start it with `G:\Android\Sdk\emulator\emulator.exe -avd medium_phone -no-snapshot-save -gpu swangle_indirect -no-audio -no-window` (headless: the emulator's window crashed in the host's NVIDIA OpenGL driver on 2026-10-27), wait for `sys.boot_completed`, and kill it when you are done.
- Use `adb -s emulator-5554` for every adb command: the owner's phone may be plugged in and must not be touched.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in its context's testing document, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: do not run the live External suite or any paid call. The owner runs the surface from the main checkout after the merge. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- RevenueCat is faked in the Android tests; no live or paid run.
- Save the report on the phone; ask once on the next launch; nothing is sent until the tester taps Send; no Firebase. The report holds the stack trace, app version, Android version and device model, and no email, token, password, account id or user-entered Rig data.
- Send to the feedback address constant that #182 added (`FEEDBACK_EMAIL` in `ui/util/Feedback.kt`; `FeedbackLink` in `ui/components` is the control); if it is not in this branch, stop and say so.
- The ticket's decisions are already recorded in its DECISIONS comment: do not ask them again.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 184`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push. Afterwards stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe -s emulator-5554 emu kill`).

**Your part:** none.

### #188 A test tag on every Android UI element (redesign step 1)

**Lane A.** Start after **#184** has merged, so its new controls are tagged here (#169 has merged). This touches every screen and test, so no other Android ticket may be open while it runs. Android: the single emulator, one Android ticket at a time.

1. In this main-checkout session type `/ticket-start 188`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-188`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-188` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-188"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #188

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The Android end-of-session command is `uv run scripts/android_session_end.py` (JVM tests, coverage floor, detekt; no device).
- A UI test needs the single emulator; no other Android ticket may be running. Start it with `G:\Android\Sdk\emulator\emulator.exe -avd medium_phone -no-snapshot-save -gpu swangle_indirect -no-audio -no-window` (headless: the emulator's window crashed in the host's NVIDIA OpenGL driver on 2026-10-27), wait for `sys.boot_completed`, and kill it when you are done.
- Use `adb -s emulator-5554` for every adb command: the owner's phone may be plugged in and must not be touched.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in its context's testing document, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: do not run the live External suite or any paid call. The owner runs the surface from the main checkout after the merge. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- RevenueCat is faked in the Android tests; no live or paid run.
- The only production change is `testTag` additions and one `UiTags` object. Bring `docs/android-redesign/ui-inventory.json` up to date first for what #186, #169, #182 and #184 added. Tests that assert wording itself keep their text checks and are named in the STATUS comment.
- The ticket's decisions are already recorded in its DECISIONS comment: do not ask them again.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 188`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push. Afterwards stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe -s emulator-5554 emu kill`).

**Your part:** none.

### #189 Baseline screenshots and measured bounds (redesign step 2)

**Lane A.** Start after **#188** has merged. The emulator must be **alone**: no other Android ticket and no External run at the same time. Android: the single emulator, one Android ticket at a time.

1. In this main-checkout session type `/ticket-start 189`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-189`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-189` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-189"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #189

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The Android end-of-session command is `uv run scripts/android_session_end.py` (JVM tests, coverage floor, detekt; no device).
- A UI test needs the single emulator; no other Android ticket may be running. Start it with `G:\Android\Sdk\emulator\emulator.exe -avd medium_phone -no-snapshot-save -gpu swangle_indirect -no-audio -no-window` (headless: the emulator's window crashed in the host's NVIDIA OpenGL driver on 2026-10-27), wait for `sys.boot_completed`, and kill it when you are done.
- Use `adb -s emulator-5554` for every adb command: the owner's phone may be plugged in and must not be touched.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in its context's testing document, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: do not run the live External suite or any paid call. The owner runs the surface from the main checkout after the merge. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- RevenueCat is faked in the Android tests; no live or paid run.
- The PNGs are build output and are not committed; the merged measurements are. Do not call any paid service.
- The ticket's decisions are already recorded in its DECISIONS comment: do not ask them again.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 189`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push. Afterwards stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe -s emulator-5554 emu kill`).

**Your part:** after the merge, copy the 412 x 892 PNGs from the build output to the Claude Design session for #190, and agree the checkpoint push with Claude (see "Pushes" below).

### #190 The design round (yours; no build session)

**Starts when #189 has merged** (decision, 2026-10-27: wait for the real frames, so the designer sees the finished Alpha screens). Lane A pauses until the hand-back is committed.

1. In this main-checkout session tell Claude: "ask me the #190 decisions". It asks the two still open (is a dark theme in scope? how far may the design change navigation?) and records all three in a DECISIONS comment on #190.
2. Attach to the Claude Design session: `docs/android-redesign/REDESIGN_BRIEF.md` (its section 10 holds your 2026-10-27 phone feedback: splash, app icon, signed-in status, sign out, bigger scan chip, "0 scans"), `docs/android-redesign/ui-inventory.json`, `web/public/logo.png`, `web/src/design-system/tokens.css`, the three `android/app/src/main/res/drawable/ref_*.jpg` photos, the address https://rigcheck-web.pages.dev, and the 412 x 892 PNGs from #189. Do not attach `ANDROID_DESIGN_BRIEF.md`.
3. Commit what the design hands back to `docs/android-redesign/design-return/` (the list is in section 6 of the brief). Tell Claude when it is committed; #191 starts after that.

### #191 Theme, tokens and shared components from the design

**Lane A.** Start after the #190 hand-back is committed. Android: the single emulator, one Android ticket at a time.

1. In this main-checkout session type `/ticket-start 191`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-191`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-191` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-191"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #191

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The Android end-of-session command is `uv run scripts/android_session_end.py` (JVM tests, coverage floor, detekt; no device).
- A UI test needs the single emulator; no other Android ticket may be running. Start it with `G:\Android\Sdk\emulator\emulator.exe -avd medium_phone -no-snapshot-save -gpu swangle_indirect -no-audio -no-window` (headless: the emulator's window crashed in the host's NVIDIA OpenGL driver on 2026-10-27), wait for `sys.boot_completed`, and kill it when you are done.
- Use `adb -s emulator-5554` for every adb command: the owner's phone may be plugged in and must not be touched.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in its context's testing document, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: do not run the live External suite or any paid call. The owner runs the surface from the main checkout after the merge. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- RevenueCat is faked in the Android tests; no live or paid run.
- The platform splash screen and the app icon come from the designer's assets; the credit chip is bigger (touch target 48 dp or more) and shows "0 scans" when signed out. See the DECISIONS comment on this ticket.
- The ticket's decisions are already recorded in its DECISIONS comment: do not ask them again.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 191`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push. Afterwards stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe -s emulator-5554 emu kill`).

**Your part:** none.

### #192 Re-skin the Rig picker, Chooser and photo-source dialog

**Lane A.** Start after **#191** has merged. The five re-skin tickets (#192 to #196) run in any order, one at a time. Android: the single emulator, one Android ticket at a time.

1. In this main-checkout session type `/ticket-start 192`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-192`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-192` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-192"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #192

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The Android end-of-session command is `uv run scripts/android_session_end.py` (JVM tests, coverage floor, detekt; no device).
- A UI test needs the single emulator; no other Android ticket may be running. Start it with `G:\Android\Sdk\emulator\emulator.exe -avd medium_phone -no-snapshot-save -gpu swangle_indirect -no-audio -no-window` (headless: the emulator's window crashed in the host's NVIDIA OpenGL driver on 2026-10-27), wait for `sys.boot_completed`, and kill it when you are done.
- Use `adb -s emulator-5554` for every adb command: the owner's phone may be plugged in and must not be touched.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in its context's testing document, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: do not run the live External suite or any paid call. The owner runs the surface from the main checkout after the merge. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- RevenueCat is faked in the Android tests; no live or paid run.
- The Rig picker header shows whether you are signed in and as which account, and gives a way to sign out. See the DECISIONS comment on this ticket. The sign-out and the account label already exist; this is placement, not new logic.
- The ticket's decisions are already recorded in its DECISIONS comment: do not ask them again.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 192`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push. Afterwards stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe -s emulator-5554 emu kill`).

**Your part:** before Claude merges it, compare the running-app screenshot in the STATUS comment with the designer's picture for the same state, on your phone.

### #193 Re-skin the Truck Tag, Trailer Tag and Scale Ticket entry screens

**Lane A.** Start after **#191** has merged. The five re-skin tickets (#192 to #196) run in any order, one at a time. Android: the single emulator, one Android ticket at a time.

1. In this main-checkout session type `/ticket-start 193`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-193`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-193` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-193"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #193

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The Android end-of-session command is `uv run scripts/android_session_end.py` (JVM tests, coverage floor, detekt; no device).
- A UI test needs the single emulator; no other Android ticket may be running. Start it with `G:\Android\Sdk\emulator\emulator.exe -avd medium_phone -no-snapshot-save -gpu swangle_indirect -no-audio -no-window` (headless: the emulator's window crashed in the host's NVIDIA OpenGL driver on 2026-10-27), wait for `sys.boot_completed`, and kill it when you are done.
- Use `adb -s emulator-5554` for every adb command: the owner's phone may be plugged in and must not be touched.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in its context's testing document, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: do not run the live External suite or any paid call. The owner runs the surface from the main checkout after the merge. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- RevenueCat is faked in the Android tests; no live or paid run.
- The ticket's decisions are already recorded in its DECISIONS comment: do not ask them again.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 193`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push. Afterwards stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe -s emulator-5554 emu kill`).

**Your part:** before Claude merges it, compare the running-app screenshot in the STATUS comment with the designer's picture for the same state, on your phone.

### #194 Re-skin the Disclaimer and Results screens

**Lane A.** Start after **#191** has merged. The five re-skin tickets (#192 to #196) run in any order, one at a time. Android: the single emulator, one Android ticket at a time.

1. In this main-checkout session type `/ticket-start 194`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-194`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-194` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-194"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #194

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The Android end-of-session command is `uv run scripts/android_session_end.py` (JVM tests, coverage floor, detekt; no device).
- A UI test needs the single emulator; no other Android ticket may be running. Start it with `G:\Android\Sdk\emulator\emulator.exe -avd medium_phone -no-snapshot-save -gpu swangle_indirect -no-audio -no-window` (headless: the emulator's window crashed in the host's NVIDIA OpenGL driver on 2026-10-27), wait for `sys.boot_completed`, and kill it when you are done.
- Use `adb -s emulator-5554` for every adb command: the owner's phone may be plugged in and must not be touched.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in its context's testing document, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: do not run the live External suite or any paid call. The owner runs the surface from the main checkout after the merge. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- RevenueCat is faked in the Android tests; no live or paid run.
- The ticket's decisions are already recorded in its DECISIONS comment: do not ask them again.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 194`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push. Afterwards stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe -s emulator-5554 emu kill`).

**Your part:** before Claude merges it, compare the running-app screenshot in the STATUS comment with the designer's picture for the same state, on your phone.

### #195 Re-skin the History screen

**Lane A.** Start after **#191** has merged. The five re-skin tickets (#192 to #196) run in any order, one at a time. Android: the single emulator, one Android ticket at a time.

1. In this main-checkout session type `/ticket-start 195`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-195`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-195` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-195"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #195

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The Android end-of-session command is `uv run scripts/android_session_end.py` (JVM tests, coverage floor, detekt; no device).
- A UI test needs the single emulator; no other Android ticket may be running. Start it with `G:\Android\Sdk\emulator\emulator.exe -avd medium_phone -no-snapshot-save -gpu swangle_indirect -no-audio -no-window` (headless: the emulator's window crashed in the host's NVIDIA OpenGL driver on 2026-10-27), wait for `sys.boot_completed`, and kill it when you are done.
- Use `adb -s emulator-5554` for every adb command: the owner's phone may be plugged in and must not be touched.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in its context's testing document, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: do not run the live External suite or any paid call. The owner runs the surface from the main checkout after the merge. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- RevenueCat is faked in the Android tests; no live or paid run.
- The ticket's decisions are already recorded in its DECISIONS comment: do not ask them again.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 195`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push. Afterwards stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe -s emulator-5554 emu kill`).

**Your part:** before Claude merges it, compare the running-app screenshot in the STATUS comment with the designer's picture for the same state, on your phone.

### #196 Re-skin the Paywall, Account and the two Scan dialogs

**Lane A.** Start after **#191** has merged. The five re-skin tickets (#192 to #196) run in any order, one at a time. Android: the single emulator, one Android ticket at a time.

1. In this main-checkout session type `/ticket-start 196`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-196`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-196` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-196"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #196

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The Android end-of-session command is `uv run scripts/android_session_end.py` (JVM tests, coverage floor, detekt; no device).
- A UI test needs the single emulator; no other Android ticket may be running. Start it with `G:\Android\Sdk\emulator\emulator.exe -avd medium_phone -no-snapshot-save -gpu swangle_indirect -no-audio -no-window` (headless: the emulator's window crashed in the host's NVIDIA OpenGL driver on 2026-10-27), wait for `sys.boot_completed`, and kill it when you are done.
- Use `adb -s emulator-5554` for every adb command: the owner's phone may be plugged in and must not be touched.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in its context's testing document, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: do not run the live External suite or any paid call. The owner runs the surface from the main checkout after the merge. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- RevenueCat is faked in the Android tests; no live or paid run.
- Keep what #186 fixed: nothing under the system bars, Restore purchase reachable with 3-button navigation, and the Paywall's Back control.
- The ticket's decisions are already recorded in its DECISIONS comment: do not ask them again.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 196`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push. Afterwards stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe -s emulator-5554 emu kill`).

**Your part:** before Claude merges it, compare the running-app screenshot in the STATUS comment with the designer's picture for the same state, on your phone.

### #197 Final pass and sign-off

**Lane A.** Start after **#192 to #196** have all merged. Android: the single emulator, one Android ticket at a time.

1. In this main-checkout session type `/ticket-start 197`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-197`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-197` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-197"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #197

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The Android end-of-session command is `uv run scripts/android_session_end.py` (JVM tests, coverage floor, detekt; no device).
- A UI test needs the single emulator; no other Android ticket may be running. Start it with `G:\Android\Sdk\emulator\emulator.exe -avd medium_phone -no-snapshot-save -gpu swangle_indirect -no-audio -no-window` (headless: the emulator's window crashed in the host's NVIDIA OpenGL driver on 2026-10-27), wait for `sys.boot_completed`, and kill it when you are done.
- Use `adb -s emulator-5554` for every adb command: the owner's phone may be plugged in and must not be touched.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in its context's testing document, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: do not run the live External suite or any paid call. The owner runs the surface from the main checkout after the merge. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- RevenueCat is faked in the Android tests; no live or paid run.
- The ticket's decisions are already recorded in its DECISIONS comment: do not ask them again.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 197`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push. Afterwards stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe -s emulator-5554 emu kill`).

**Your part:** check every screen on your phone (3-button navigation, and a large font size once) and sign off. Then build the tester APK.

### #132 (optional) Is mutation testing worth running? Research

**Any lane.** Lowest priority; production code is not changed. Skip it if the round is running long.

1. In this main-checkout session type `/ticket-start 132`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-132`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-132` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-132"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #132

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- Research only: write one file under `docs/research/` and change no production code.
- No live or paid runs.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 132`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push.

**Your part:** read the research file it writes under `docs/research/` after the merge.

## Things to remember

- `--maxprocesses=8` caps `-n auto` because 24 workers ran this machine out of memory. Even at 8, the Python suite occasionally errors in tests that create a real git repo (`git init` or `git worktree add` exits 3221225773 or "WinError 1455: paging file too small") when the emulator, Gradle and other sessions are up (about 3 in 16 runs). It is memory, not a regression; re-run.
- The `medium_phone` AVD's Graphics is Software (set 2026-10-21). The `-gpu swangle_indirect` start line in the cards stays and does not depend on it.
- An emulator that a session started holds its `emulator.log` open and blocks deleting the ticket folder after `/ticket-merge`: stop the emulator and close any terminal open in the ticket's folder, then `rmdir` the leftover `.claude/worktrees/ticket-N` if `/ticket-merge` says it could not remove it.
- Paid prompts from a non-interactive shell: `cmd /c "echo y| powershell -NoProfile -File workers\scan-proxy\test-external.ps1 -MaxPaidCalls N"` (piping several `'y'` lines from PowerShell declines the first prompt and records `skipped`, which spends nothing and leaves the surface stale). Claude does this, with your ceiling.
- Every new test file must be named in its context's testing document, and every new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise. Build sessions have missed this twice, so the merge review adds the row or entry and asks first.
- The planner treats `*.md`, `docs/*` and `ClaudePlans/*` as docs-only (plans nothing), follows `shares_with` and `depends_on` links to downstream contexts, and does not list a deleted test file.
- Keep the `external-suite-pro` RevenueCat grant non-expiring or far-dated (the Web External suite depends on it).
