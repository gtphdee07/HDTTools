# Alpha round: your run sheet

Working notes for the Alpha round ([BETA_PLAN.md](../BETA_PLAN.md)). They are temporary: delete this file when the round ends. The general ticket flow is in [ticket-skills.md](ticket-skills.md). **Each ticket's card below is complete: the box on it is the whole first message for the build session (the `/mattpocock-skills:implement` line, the handoff text and the test-round additions), and the numbered steps give every command, in order.** Only work that is not finished is on this page; finished tickets are in their closing comments.

## Where things stand (2026-10-29)

- Checkpoint push done 2026-10-28 (c1f1786; Web is live with it; the Worker was deployed on 2026-10-27). Merged and pushed in it: #179, #174 with its #185 fix, #181, #186, #169, #180, #182, #183, #184, #188 (test tags, with a test-only fix on top), #189 (baseline screenshots and measured bounds), #190 (the Claude Design hand-back and its follow-up for 17 controls), #191 (theme, tokens, shared components and the hand-back validator; merged 2026-10-28, not yet pushed), #192 (Rig picker, Chooser and photo dialog re-skin; merged 2026-10-28, not yet pushed), and the redesign brief and plan edits. The next push is the final one, at the end (see "Pushes").
- **Next, first of all (your decision 2026-10-29): #203** (a run that ends because the emulator died is an infra-abort and gets retried; the watchdog tests fail instead of hanging) runs before any other ticket. #193 to #196 start only after it has merged. Its last check uses the emulator alone.
- **Lane A:** nothing is running. #192 (Rig picker, Chooser, photo dialog) merged 2026-10-28; after #203 the re-skin tickets #193 to #196 are next, one at a time. The whole app already uses #191's new theme and text styles. **Emulator runs are lighter until the end** (your decision 2026-10-28): #191 to #196 are built and merged with only their own test classes run on the emulator; the full suite, device mutation checks and the full layout capture run once at #197. **Lane B:** has nothing left but #203 (first) and the optional #132. **#200** (hang detection) is merged (2026-10-29): a supervised runner with a progress file and watchdog (`scripts/run_supervisor.py`, read with `uv run scripts/run_status.py`), a hook that puts a build session's device commands on it, a watcher (`uv run scripts/run_watch.py`, run it as a Monitor to get the balloon alert) and caps on the review suites. Restart open Claude sessions so the hook loads. The hook approves a lone device command and asks for any other line. **#203** (a run that ends because the emulator died is an infra-abort and gets retried; the watchdog tests should fail, not hang) is filed from the merge review and is now placed first (see above). **#201** (the test planner) is merged (2026-10-28): a ticket's session plan now covers the contexts its diff touches and what depends on them, not every context, so an Android ticket that also edits a script or a Python test no longer plans web, Scan Proxy, the slow set or their stale External surfaces; the full run stays for dependency and lock files, the planner, the ledger and ticket scripts, and `.claude/settings.json`. #193 to #196 and #197 get the narrower plan from `/ticket-finish` without a hand-narrowed set.
- **The design round (#190) is done and merged**: light theme only, same flow and screens, a top app bar with Back. #189's baseline is merged: every inventory element now has a measured size in `ui-inventory.json` (`today_measured`; the estimates in `today` stay as the designer saw them). Only two estimates that were plain numbers differ from the measurement: the bin on the Rig card (48 dp estimated, 40 dp measured; the touch area may still be 48 dp, #197 checks) and the Results bar (6 dp estimated, 26 dp measured, because the tag sits on a larger box).
- Your phone (SM-G996U, adb name `R3CR50G10ML`) has the beta build, versionCode 3. The emulator is `emulator-5554`. Name the one you mean in every adb command.
- The Android re-skin (epic #187) happens before the Alpha: the tester APK is built only after #197 and your sign-off.

## The tickets, in order

Two lanes, one build session each, a **new** session for every ticket. Lane A is Android and runs one ticket at a time (one emulator). Lane B is Web, Worker and tooling (no emulator, no Gradle) and runs beside lane A.

| # | Ticket | Lane | Starts when | Your part |
|---|---|---|---|---|
| first | [#203](#203-hang-detection-follow-up-an-emulator-death-is-an-infra-abort) Hang detection follow-up | B (the emulator alone for its last check) | now, before any other ticket | none |
| 1 to 4 | #193 to #196 re-skin: [entry screens](#193-re-skin-the-truck-tag-trailer-tag-and-scale-ticket-entry-screens), [Disclaimer and Results](#194-re-skin-the-disclaimer-and-results-screens), [History](#195-re-skin-the-history-screen), [Paywall, Account, dialogs](#196-re-skin-the-paywall-account-and-the-two-scan-dialogs) | A | #203 merged | look through the frames first; compare with the designer's picture on your phone |
| 5 | [#197](#197-final-pass-and-sign-off) Final pass and sign-off (it also settles the #202 keyboard-test failure) | A | #193 to #196 merged | check every screen, sign off |
| 6 | [#198](#198-emulator-profiles-for-four-phone-shapes) Emulator profiles on G: for four phone shapes | A | #197 merged and signed off | answer its three decisions, including the Android 26 image download to G: |
| optional | [#132](#132-optional-is-mutation-testing-worth-running-research) Is mutation testing worth running? | any | any time | none |

A ticket starts when the tickets it waits for have merged, not when the round ends. Decisions for all of them are already recorded in DECISIONS comments, so the workers do not ask again.

**How the two lanes stay out of each other's way**
- **Memory:** only lane A may use the emulator or Gradle. Lane B runs vitest, node and pytest only. If the machine runs short of memory, pause lane B.
- **Same files:** `scripts/test_planner_config.json` (any new slow test). Claude merges one ticket at a time and settles any text clash at the merge; the second ticket of a pair may need a refresh onto the new baseline, and Claude says so.
- **Merge order between lanes:** whichever worker finishes first.

## Pushes and External runs

- **Pushes:** the checkpoint push is done (2026-10-28, after the External bundle); the final push comes at the end. Claude asks before it. Web goes live on each push; with no testers yet that is harmless, and the remote then holds a copy of the work.
- The pre-push gate refuses a push that touches `web/`, `workers/scan-proxy/` or `android/` while an External surface is stale (`uv run scripts/external_freshness.py` says which). **All External surfaces were fresh on 2026-10-28** after the bundle (they went stale again the same day: #191 removed a line from `android/gradle/libs.versions.toml`, which marks `revenuecat-android-sdk` and `supabase-auth` stale, and `wrangler` 4.155.0 marks `pages-site` and `scan-proxy-worker` stale; the registry proxy does this about daily, so run the bundle once, right before the final push, and run it in one go: `revenuecat-android-sdk` needs the emulator alone, `scan-proxy-worker` is one paid call) (`pages-site` 9 tests, `revenuecat-android-sdk` 6 tests on the emulator, `scan-proxy-worker` 1 paid call, `anthropic-python` 3 paid calls; ceiling 7 approved). `anthropic-python` makes paid calls (3), not free as earlier notes said. A new `wrangler`, `workerd`, `purchases` or `anthropic` release makes a surface stale again, so before the final push run `external_freshness.py` once more.
- Do not invite testers before the final push and the owner steps below are done.

## Owner steps, in the order they come up

- [x] Signing values in `G:\GradleUserHome\gradle.properties`, APK built, fingerprint matches the notes file, installed on the phone, Google sign-in works (done 2026-10-27; the phone has versionCode 3).
- [x] #186 checked on the phone: the Paywall, the Create button, History and the Truck Tag keyboard (done 2026-10-27).
- [x] The grant tool ran live on one test account (2026-10-27): RevenueCat shows the Pro entitlement (display name "Rig Check Pro", lookup key `pro`, expires in a year) and 20 scans.
- [ ] Run the grant tool for each real tester (dry run, then `--apply`; the account id is in the Supabase dashboard, Authentication, Users; steps in `docs/BUILD_AND_DEPLOY.md`, "Granting a tester"). Leave one tester on Free so someone tests buying Pro.
- [x] #183: the Worker was redeployed (forced, with a recorded reason) and the live suites passed on 2026-10-27.
- [x] The Cloudflare logs show our scan line (2026-10-27): `event: scan, outcome: delivered, doc_type: truck_tag, duration_ms: 4225, refunded: false`. A delivered line has no level label in the dashboard; failures show as `error`. Cloudflare also writes its own `POST /v1/scan` row per request, with the requester's IP and rough location (only you can read it); `invocation_logs = false` in `wrangler.toml` would turn that off, and is yours to decide (see "Things to remember").
- [x] The guide's scan wording is decided (2026-10-27, "Scans use up a scan balance we set for your account. If it runs out, email us and we will add more.") and it now says Android has the same Send feedback link.
- [ ] Read `docs/BETA_TESTER_GUIDE.md` once as a tester would, and on the web tap **Send feedback** (page footer or Account screen) to see the draft addressed to WTIAppDev@gmail.com.
- [x] The Truck and Trailer hint (decided 2026-10-28): the screens say "Tap a field to see its spot on the tag" but tapping a field does nothing yet. No users until the Alpha, so it may stay open while the re-skin is built, **but it must be closed before the Alpha**: #193 builds the designer's focused-field behaviour if it can without #199's stored crops, and #197 has an acceptance criterion that the hint describes what the app really does (with the other #191 gaps: new-element strings, old orange text buttons, the `paywall.toast` drift entry).
- [ ] With the rebuilt APK (after #197), on the phone: the splash screen, the app icon (and the one-colour themed icon with themed icons on) and the Rig picker's scan chip look like `splash__default`, `app_icon__launcher` and `rig_picker__in` in `design-return/annotated/`; **Send feedback** at the foot of the Rig picker and of the sign-in screen opens a draft to WTIAppDev@gmail.com; the Paywall shows the bold "Beta: test payments" line. Optionally crash the app once and check that the next launch asks "RigCheck closed unexpectedly last time. Send details?" (Send opens a draft, Not now deletes the report).
- [x] The design round (#190) ran and its hand-back is merged (2026-10-27).
- [x] The hand-back's four decisions are answered and recorded on #191 (2026-10-27): approve the simplified logo mark (launcher icon and splash); bundle Outfit and DM Sans; keep the scan-balance chip on the Truck screen; defer the pinned label crop to #199.
- [x] The copy in `copy-changes.md` is approved as written (2026-10-27, recorded on #191).
- [x] The follow-up design round (17 controls) is committed and checked (2026-10-27, `design-return/ui-redesign-map-followup.json`): the bin sits at the right end of the Rig card behind a divider; the Paywall toast becomes a Snackbar (you approved; decided on #191 and #196). It added no new strings.
- [ ] **#189's baseline frames** are in `docs/android-redesign/design-built-to-be-checked/` (untracked; Claude hid the folder locally through `.git/info/exclude` so the merge could run; delete it or move it when you are done). Decide whether the designer checks them: Claude's advice is to show the designer only the 412 x 892 frames of the bin on the Rig card and of the Results bar, and to say nothing else changes.
- [ ] Before #193 starts, look through the frames in `docs/android-redesign/design-return/annotated/` (70 now; the 7 new and 20 re-issued ones are listed in `design-return/README.md`, "Follow-up round") and tell Claude any screen you want changed. Anything you do not mention is built as drawn.
- [ ] On each re-skin ticket (#193 to #196): compare the screenshot in the STATUS comment with the designer's picture on your phone before Claude merges it. On #197, check every screen and sign off.
- [ ] After #197 and before the tester APK (decided 2026-10-29): #198 creates emulator profiles on G: for four phone shapes and runs the screen checks on each. Its build session asks you three things, among them whether it may download the Android 26 system image (about 1 to 2 GB, to a path under `G:\Android\Sdk`); close any other emulator session first.
- [ ] After #197 and #198: build the tester APK with a higher `-PappVersionCode` (4 or more; raise it for every APK you send), from `android`: `.\gradlew.bat assembleBeta -PappVersionCode=<n>`. Confirm `keytool -printcert -jarfile app\build\outputs\apk\beta\app-beta.apk` shows the SHA-1 in `G:\Secrets\rigcheck\rigcheck-upload-keystore-NOTES.txt`.
- [ ] Before inviting: add each Alpha tester's Gmail as a Google test user (up to 5); send the APK and the guide.
- [ ] Device checks still open from earlier tickets: add a Rig on Web and see it in the Android picker; finish a check with a full Garage and look at the notice; finish a check on Android and see it in Web's History, then the other way round; compare a History date on the phone with the same entry on Web; delete a Rig on the phone (the bin on its card) and check it is gone on Web, then delete one on Web and check the phone's picker drops it after a refresh (#169 never ran against the live project); on the phone buy Pro with the Test Store and confirm the starter scans arrive.
- [ ] Confirm the Pro price is the same on both products (ADR-0006).
- [ ] Triage #173 (Android History filters); decide #171 (live External coverage of the Android Garage client) before an Android release.
- [ ] Clean up: `.claude/worktrees/ticket-20`, `-40`, `-137`, `-140`, `-148`, `-186` and `-190-mpskills-2902c4` are leftover folders, not worktrees (the last is the design session's folder: git has forgotten it, but another program still holds it, probably the desktop app session; close that session first). Close any dev server or terminal still holding them, then ask Claude to check and remove them (the ticket-20 one was held by a node process).

Not in this round: #40 (Google Play Billing; blocked until a Play Console account exists, see the ticket's DECISIONS and `STATUS: BLOCKED`; ask Claude to rebuild its card when you restart it), #68, #69, #70, #72, #100, #170, #172, #175, #177. After the round: #144, #145, #146, #165, #155 to #159, #138 and #139.

## Run cards

### #203 Hang detection follow-up: an emulator death is an infra-abort

**Lane B, first of everything (your decision 2026-10-29).** Start it before any other ticket; #193 to #196 wait for it. Its last check uses the emulator, alone: nothing else may be using the emulator or Gradle then. Android: the single emulator, one Android ticket at a time.

1. In this main-checkout session type `/ticket-start 203`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-203`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-203` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-203"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #203

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- The end-of-session commands are `uv run scripts/static_checks.py core` and the offline tests that `uv run scripts/test_planner.py` lists. Do not start Gradle or the emulator.
- Only `scripts/`, `tests/`, `docs/` and the testing documents change.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in `tests/TESTING.md`, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: no live External suite and no paid call. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- Exception to the first line above, for the last acceptance criterion only: that one real run needs the single emulator. Start it with `uv run scripts/android_suite_loop.py --boot-only --emulator-arg=-no-window --emulator-arg=-no-audio`, use `adb -s emulator-5554` only (never the owner's phone), run the check under `uv run scripts/run_supervisor.py --device -- ...`, and kill the emulator with `adb -s emulator-5554 emu kill` when done.
- Mutation-check the two watchdog tests as the ticket says, with a subprocess timeout on every run (a mutation that blinds the watchdog makes the tests wait for ever) and every edit restored; name the mutations in the STATUS comment.
- The ticket's decisions are already recorded in its DECISIONS comment: do not ask them again.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 203`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push. Afterwards stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe -s emulator-5554 emu kill`).

**Your part:** nothing, except to leave the emulator and Gradle alone while its last check runs.

### #193 Re-skin the Truck Tag, Trailer Tag and Scale Ticket entry screens

**Lane A.** Start it after **#203** has merged (your decision 2026-10-29); nothing else blocks it (#192 has merged). The four remaining re-skin tickets (#193 to #196) run in any order, one at a time. Android: the single emulator, one Android ticket at a time.

1. In this main-checkout session type `/ticket-start 193`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-193`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-193` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-193"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #193

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The Android end-of-session command is `uv run scripts/android_session_end.py` (JVM tests, coverage floor, detekt; no device).
- A UI test needs the single emulator; no other Android ticket may be running. Start it with `uv run scripts/android_suite_loop.py --boot-only --emulator-arg=-no-window --emulator-arg=-no-audio` (headless: the emulator's window crashed in the host's NVIDIA OpenGL driver on 2026-10-27; it cold-boots the emulator on the software GPU, waits until it is steadily ready and leaves it running; a bare `emulator.exe` command is refused by the guard hook), and kill it when you are done. Run a test class as `uv run scripts/run_supervisor.py --device --output-limit-s 300 -- android/gradlew -p android connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=<fqcn>` (a bare Gradle device command is rewritten to this by the hook). A stalled run is stopped after its evidence is saved and exits 124 (`hung`); that is not a test failure: read `uv run scripts/run_status.py`, then run it once more on a freshly booted emulator.
- Use `adb -s emulator-5554` for every adb command: the owner's phone may be plugged in and must not be touched.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in its context's testing document, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: do not run the live External suite or any paid call. The owner runs the surface from the main checkout after the merge. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- RevenueCat is faked in the Android tests; no live or paid run.
- The Truck and Trailer hint says "Tap a field to see its spot on the tag" but tapping a field does nothing yet: build the designer's focused-field behaviour if it can be built without the stored crops of #199, otherwise list the gap under Not done. See the DECISIONS comment on this ticket.
- Emulator runs are deferred (owner decision 2026-10-28, see the DECISIONS comment on this ticket): on the emulator run only the test classes this ticket's acceptance criteria name, and the screenshots for the owner's comparison; do not run the full `connectedDebugAndroidTest` suite, device mutation checks or the full layout capture (they run once, at #197). Name the classes you ran in the STATUS comment and say "full suite deferred to #197".
- The ticket's decisions are already recorded in its DECISIONS comment: do not ask them again.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 193`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push. Afterwards stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe -s emulator-5554 emu kill`).

**Your part:** before Claude merges it, compare the running-app screenshot in the STATUS comment with the designer's picture for the same state, on your phone.

### #194 Re-skin the Disclaimer and Results screens

**Lane A.** Start it after **#203** has merged (your decision 2026-10-29); nothing else blocks it (#192 has merged). The four remaining re-skin tickets (#193 to #196) run in any order, one at a time. Android: the single emulator, one Android ticket at a time.

1. In this main-checkout session type `/ticket-start 194`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-194`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-194` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-194"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #194

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The Android end-of-session command is `uv run scripts/android_session_end.py` (JVM tests, coverage floor, detekt; no device).
- A UI test needs the single emulator; no other Android ticket may be running. Start it with `uv run scripts/android_suite_loop.py --boot-only --emulator-arg=-no-window --emulator-arg=-no-audio` (headless: the emulator's window crashed in the host's NVIDIA OpenGL driver on 2026-10-27; it cold-boots the emulator on the software GPU, waits until it is steadily ready and leaves it running; a bare `emulator.exe` command is refused by the guard hook), and kill it when you are done. Run a test class as `uv run scripts/run_supervisor.py --device --output-limit-s 300 -- android/gradlew -p android connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=<fqcn>` (a bare Gradle device command is rewritten to this by the hook). A stalled run is stopped after its evidence is saved and exits 124 (`hung`); that is not a test failure: read `uv run scripts/run_status.py`, then run it once more on a freshly booted emulator.
- Use `adb -s emulator-5554` for every adb command: the owner's phone may be plugged in and must not be touched.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in its context's testing document, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: do not run the live External suite or any paid call. The owner runs the surface from the main checkout after the merge. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- RevenueCat is faked in the Android tests; no live or paid run.
- Emulator runs are deferred (owner decision 2026-10-28, see the DECISIONS comment on this ticket): on the emulator run only the test classes this ticket's acceptance criteria name, and the screenshots for the owner's comparison; do not run the full `connectedDebugAndroidTest` suite, device mutation checks or the full layout capture (they run once, at #197). Name the classes you ran in the STATUS comment and say "full suite deferred to #197".
- The ticket's decisions are already recorded in its DECISIONS comment: do not ask them again.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 194`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push. Afterwards stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe -s emulator-5554 emu kill`).

**Your part:** before Claude merges it, compare the running-app screenshot in the STATUS comment with the designer's picture for the same state, on your phone.

### #195 Re-skin the History screen

**Lane A.** Start it after **#203** has merged (your decision 2026-10-29); nothing else blocks it (#192 has merged). The four remaining re-skin tickets (#193 to #196) run in any order, one at a time. Android: the single emulator, one Android ticket at a time.

1. In this main-checkout session type `/ticket-start 195`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-195`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-195` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-195"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #195

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The Android end-of-session command is `uv run scripts/android_session_end.py` (JVM tests, coverage floor, detekt; no device).
- A UI test needs the single emulator; no other Android ticket may be running. Start it with `uv run scripts/android_suite_loop.py --boot-only --emulator-arg=-no-window --emulator-arg=-no-audio` (headless: the emulator's window crashed in the host's NVIDIA OpenGL driver on 2026-10-27; it cold-boots the emulator on the software GPU, waits until it is steadily ready and leaves it running; a bare `emulator.exe` command is refused by the guard hook), and kill it when you are done. Run a test class as `uv run scripts/run_supervisor.py --device --output-limit-s 300 -- android/gradlew -p android connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=<fqcn>` (a bare Gradle device command is rewritten to this by the hook). A stalled run is stopped after its evidence is saved and exits 124 (`hung`); that is not a test failure: read `uv run scripts/run_status.py`, then run it once more on a freshly booted emulator.
- Use `adb -s emulator-5554` for every adb command: the owner's phone may be plugged in and must not be touched.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in its context's testing document, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: do not run the live External suite or any paid call. The owner runs the surface from the main checkout after the merge. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- RevenueCat is faked in the Android tests; no live or paid run.
- Emulator runs are deferred (owner decision 2026-10-28, see the DECISIONS comment on this ticket): on the emulator run only the test classes this ticket's acceptance criteria name, and the screenshots for the owner's comparison; do not run the full `connectedDebugAndroidTest` suite, device mutation checks or the full layout capture (they run once, at #197). Name the classes you ran in the STATUS comment and say "full suite deferred to #197".
- The ticket's decisions are already recorded in its DECISIONS comment: do not ask them again.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 195`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push. Afterwards stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe -s emulator-5554 emu kill`).

**Your part:** before Claude merges it, compare the running-app screenshot in the STATUS comment with the designer's picture for the same state, on your phone.

### #196 Re-skin the Paywall, Account and the two Scan dialogs

**Lane A.** Start it after **#203** has merged (your decision 2026-10-29); nothing else blocks it (#192 has merged). The four remaining re-skin tickets (#193 to #196) run in any order, one at a time. Android: the single emulator, one Android ticket at a time.

1. In this main-checkout session type `/ticket-start 196`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-196`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-196` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-196"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #196

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The Android end-of-session command is `uv run scripts/android_session_end.py` (JVM tests, coverage floor, detekt; no device).
- A UI test needs the single emulator; no other Android ticket may be running. Start it with `uv run scripts/android_suite_loop.py --boot-only --emulator-arg=-no-window --emulator-arg=-no-audio` (headless: the emulator's window crashed in the host's NVIDIA OpenGL driver on 2026-10-27; it cold-boots the emulator on the software GPU, waits until it is steadily ready and leaves it running; a bare `emulator.exe` command is refused by the guard hook), and kill it when you are done. Run a test class as `uv run scripts/run_supervisor.py --device --output-limit-s 300 -- android/gradlew -p android connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=<fqcn>` (a bare Gradle device command is rewritten to this by the hook). A stalled run is stopped after its evidence is saved and exits 124 (`hung`); that is not a test failure: read `uv run scripts/run_status.py`, then run it once more on a freshly booted emulator.
- Use `adb -s emulator-5554` for every adb command: the owner's phone may be plugged in and must not be touched.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in its context's testing document, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: do not run the live External suite or any paid call. The owner runs the surface from the main checkout after the merge. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- RevenueCat is faked in the Android tests; no live or paid run.
- Keep what #186 fixed: nothing under the system bars, Restore purchase reachable with 3-button navigation, and the Paywall's Back control.
- Emulator runs are deferred (owner decision 2026-10-28, see the DECISIONS comment on this ticket): on the emulator run only the test classes this ticket's acceptance criteria name, and the screenshots for the owner's comparison; do not run the full `connectedDebugAndroidTest` suite, device mutation checks or the full layout capture (they run once, at #197). Name the classes you ran in the STATUS comment and say "full suite deferred to #197".
- The ticket's decisions are already recorded in its DECISIONS comment: do not ask them again.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 196`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push. Afterwards stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe -s emulator-5554 emu kill`).

**Your part:** before Claude merges it, compare the running-app screenshot in the STATUS comment with the designer's picture for the same state, on your phone.

### #197 Final pass and sign-off

**Lane A.** Start after **#193 to #196** have all merged. Android: the single emulator, one Android ticket at a time.

1. In this main-checkout session type `/ticket-start 197`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-197`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-197` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-197"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #197

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The Android end-of-session command is `uv run scripts/android_session_end.py` (JVM tests, coverage floor, detekt; no device).
- A UI test needs the single emulator; no other Android ticket may be running. Start it with `uv run scripts/android_suite_loop.py --boot-only --emulator-arg=-no-window --emulator-arg=-no-audio` (headless: the emulator's window crashed in the host's NVIDIA OpenGL driver on 2026-10-27; it cold-boots the emulator on the software GPU, waits until it is steadily ready and leaves it running; a bare `emulator.exe` command is refused by the guard hook), and kill it when you are done. Run a test class as `uv run scripts/run_supervisor.py --device --output-limit-s 300 -- android/gradlew -p android connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=<fqcn>` (a bare Gradle device command is rewritten to this by the hook). A stalled run is stopped after its evidence is saved and exits 124 (`hung`); that is not a test failure: read `uv run scripts/run_status.py`, then run it once more on a freshly booted emulator.
- Use `adb -s emulator-5554` for every adb command: the owner's phone may be plugged in and must not be touched.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in its context's testing document, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: do not run the live External suite or any paid call. The owner runs the surface from the main checkout after the merge. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- RevenueCat is faked in the Android tests; no live or paid run.
- This ticket owns the emulator runs deferred from #191 to #196 (owner decision 2026-10-28, see the DECISIONS comment and the three added acceptance criteria): the full instrumented suite 3 times in a row on a cold boot (`uv run scripts/android_suite_loop.py --runs 3`), the layout capture rerun with `--field after_measured`, and device mutation checks. Bisect any failure to the merge of #191 to #196 that caused it; the last full-suite pass is f8b4645.
- The headless-emulator failure of `RigPickerChooserLayoutTest.theDesignFrame412x892MatchesTheMap` (#202) is one of this ticket's acceptance criteria (owner decision 2026-10-29): re-run that class alone on a cold-booted headless emulator and once on a windowed one, say whether it is a flake, a headless-only limit or a real bug, and bring the suite count in `android/TESTING.md` up to the real size.
- The ticket's decisions are already recorded in its DECISIONS comment: do not ask them again.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 197`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push. Afterwards stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe -s emulator-5554 emu kill`).

**Your part:** check every screen on your phone (3-button navigation, and a large font size once) and sign off. Then #198 (emulator profiles) comes next, and after it the tester APK.

### #198 Emulator profiles for four phone shapes

**Lane A.** Start after **#197** has merged and you have signed off (your decision 2026-10-29); it is done before the tester APK is built. Android: the single emulator, one Android ticket at a time.

1. In this main-checkout session type `/ticket-start 198`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-198`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-198` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-198"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #198

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The Android end-of-session command is `uv run scripts/android_session_end.py` (JVM tests, coverage floor, detekt; no device).
- A UI test needs the single emulator; no other Android ticket may be running. Start it with `uv run scripts/android_suite_loop.py --boot-only --emulator-arg=-no-window --emulator-arg=-no-audio` (headless: the emulator's window crashed in the host's NVIDIA OpenGL driver on 2026-10-27; it cold-boots the emulator on the software GPU, waits until it is steadily ready and leaves it running; a bare `emulator.exe` command is refused by the guard hook), and kill it when you are done. Run a test class as `uv run scripts/run_supervisor.py --device --output-limit-s 300 -- android/gradlew -p android connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=<fqcn>` (a bare Gradle device command is rewritten to this by the hook). A stalled run is stopped after its evidence is saved and exits 124 (`hung`); that is not a test failure: read `uv run scripts/run_status.py`, then run it once more on a freshly booted emulator.
- Use `adb -s emulator-5554` for every adb command: the owner's phone may be plugged in and must not be touched.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in its context's testing document, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: do not run the live External suite or any paid call. The owner runs the surface from the main checkout after the merge. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- RevenueCat is faked in the Android tests; no live or paid run.
- The three emulator profiles must be created inside `ANDROID_AVD_HOME` (`G:\Android\EmulatorHome\avd`), never on C:. The Android 26 system image is a system-tool download: ask the owner with `AskUserQuestion`, with the exact path under `G:\Android\Sdk`, before downloading anything. One emulator at a time, and the device checks run against the re-skinned app. Every failure found becomes its own ticket, not a fix in this one.
- The ticket's `## Decisions` section is still open: ask its three questions with AskUserQuestion before building (the DECISIONS comment on the ticket only records its place in the order), and post the answers as a `DECISIONS` comment.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 198`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push. Afterwards stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe -s emulator-5554 emu kill`).

**Your part:** answer the ticket's three decisions when the session asks, including whether the Android 26 system image may be downloaded and to which path on G:.

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
- `workers/scan-proxy/wrangler.toml`: the next time the Worker needs a deploy anyway, consider (a) the nested `[observability.logs]` form Cloudflare's banner suggests (same behaviour, stops the banner) and (b) `invocation_logs = false`, which stops Cloudflare's own per-request row (it holds each requester's IP and rough location). Any `wrangler.toml` edit makes the `scan-proxy-worker` suite stale: forced deploy, then one paid scan. Decided 2026-10-27: leave both for now.
- Keep the `external-suite-pro` RevenueCat grant non-expiring or far-dated (the Web External suite depends on it).
