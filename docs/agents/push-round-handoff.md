# Push round: your run sheet (Worker A and Worker B)

Working notes for getting the repo to a state where it can be pushed and the dashboard statistics are current. They are temporary: delete this file and its generator (`scripts/gen_push_round_handoff.py`) when the round ends. It is the sibling of [test-round-handoff.md](test-round-handoff.md), which keeps the Alpha owner steps (tester APK, testers, the phone checks); this sheet is only the way to the push. The general ticket flow is in [ticket-skills.md](ticket-skills.md). **Each ticket's card below is complete: the box on it is the whole first message for the build session, and the numbered steps give every command, in order.**

**Words used here:** *Worker A* and *Worker B* are two build sessions that run side by side (A needs the emulator, B does not). The Cloudflare Worker that reads scans is called the *Scan Proxy* in this sheet, to keep the two apart.

## Where things stand (2026-11-05)

- **Last push** c1f1786 (2026-10-28). `MPSkills` is 100 or so commits ahead; the diff since then touches `android/` (the re-skin and its tests), `docs/`, `scripts/`, `tests/` and `.claude/`, and nothing under `web/` or `workers/`, so a push now would redeploy a Web identical to the live one.
- **Merged since the last push:** the re-skin (#191 to #197, #199), the device matrix (#198), the hang detection (#200, #203), the tester script (#205) and the destructive-command guard (#207, live check done). The launch-readiness plan (tickets #210 to #221, in `docs/BETA_PLAN.md`) is documents only.
- **What "the statistics" are.** `dashboard.svg` (the README graphic) is built from two things: the **measured results** (pass rates and coverage per context, saved in `scripts/dashboard_data/test_results.json`, last measured **2026-10-04**) and the **External surfaces** (their recorded passes in `scripts/dashboard_data/external_status.json`, last bundle 2026-10-28). The pre-commit hook rebuilds the graphic from the saved files on every commit to `MPSkills`; it measures nothing. So both files must be refreshed by real runs, then committed.
- **External state:** 8 of the 10 active surfaces are stale (`uv run scripts/external_freshness.py`): `anthropic-python`, `anthropic`, `pages-site`, `revenuecat-android-sdk`, `revenuecat-web-billing`, `scan-proxy-worker`, `supabase-auth`, `supabase-tables`. Most are stale only because a new release of their provider's library came out. The pre-push gate blocks this push on three of them (the Android chain: `revenuecat-android-sdk`, `scan-proxy-worker`, `supabase-auth`); you chose to refresh all eight so the dashboard is green.
- **Your decisions, 2026-11-05:** #222 and #223 stay in the Beta chain (not in this round); before the push merge #206, #225, #224 (Worker A) and #175 (Worker B); refresh all eight External surfaces.

## What "ready to push" means

1. #206, #225, #224 (Worker A) and #175 (Worker B) are merged, each reviewed with `/ticket-merge`.
2. #175's Cloudflare steps are done (2026-11-05), so a push of `MPSkills` makes only a preview and cannot change the live site (see "Owner steps").
3. On the final merged tree, with the emulator alone: the full device suite and the unit suites ran and the measured results are saved.
4. The External bundle ran for all eight surfaces and `uv run scripts/external_freshness.py` shows nothing stale (`google-play-billing` is `planned` and never blocks).
5. The two data files and `dashboard.svg` are committed on `MPSkills`, the tree is clean, and the gate says go.
6. Claude asks you, and you say yes to the push.

## The tickets, in order

Two build sessions at once, a **new** session for every ticket. Worker A is Android and runs one ticket at a time (one emulator). Worker B is tooling and runs beside it (no emulator, no Gradle).

| Order | Ticket | Worker | Starts when | Your part |
|---|---|---|---|---|
| A1 | [#206](#206-android-login-lands-on-the-front-page-not-account) Login lands on the front page | A | now | none while it builds; a phone check after the merge (see owner steps) |
| A2 | [#225](#225-threebuttonnavigationtest-on-android-80) `ThreeButtonNavigationTest` on Android 8.0 | A | #206 is merged and its emulator is stopped | none |
| A3 | [#224](#224-compose-device-tests-on-android-17) Compose device tests on Android 17 | A | #225 is merged and its emulator is stopped | none |
| B1 | [#175](#175-web-publishes-from-a-release-branch) Web publishes from a release branch | B | now | answer its three decisions; then the Cloudflare steps after the merge |

**Why this order in Worker A:** #206 changes what testers see first, and is small. #225 is a few lines in a test helper. #224 changes a test library that every Compose test uses, so it goes last: if it fails or is blocked, the other two are already in.

**How the two workers stay out of each other's way**
- **Memory:** only Worker A may use the emulator or Gradle. Worker B runs pytest and git only. If the machine runs short of memory, pause Worker B.
- **Same files:** #225 and #224 both edit the "Device matrix (Tier 1)" section of `android/TESTING.md` (the #225 note and configuration 3's row); #175 and #206 share nothing. Claude merges one ticket at a time and settles any text clash at the merge; the later of #225 and #224 may need a refresh onto the new baseline, and Claude says so.
- **Merge order between workers:** whichever finishes first.
- **The emulator is used four times** (#206, #225, #224, then the final runs below), never two at once. Close Android Studio and any other emulator before each.

## After the last merge: statistics, External bundle, push

This is Claude's work in the main checkout, with the emulator alone and nothing else running. Claude delegates the long runs to a sub-agent and reports; you are asked at two points (marked **you**).

1. `git status` is clean on `MPSkills`, and `uv run scripts/external_freshness.py` is run for the list. New provider releases make a surface stale again almost every day, so this list is taken fresh, here, not from this page.
2. **Measured results** (the slowest step; Claude measures and reports its time): start `medium_phone` as in the cards, then run `uv run scripts/run_supervisor.py --suite --output-limit-s 600 -- uv run scripts/generate_dashboard.py --refresh`. It re-runs every context's tests (Core, Streamlit, Web, Android JVM and the full instrumented suite on the one attached emulator, Scan Proxy), saves `scripts/dashboard_data/test_results.json` and rebuilds `dashboard.svg`. A hung run (exit 124) is run once more; a failing test is a real finding and stops the round for you to decide. Stop the emulator afterwards.
3. **External bundle** (the surfaces and their cost):

   | Command (from the repo root) | Surfaces it runs | Cost |
   |---|---|---|
   | `.\web\test-external.ps1` | `pages-site`, `revenuecat-web-billing`, `supabase-auth`, `supabase-tables` | free |
   | `cmd /c "echo y| powershell -NoProfile -File workers\scan-proxy\test-external.ps1 -MaxPaidCalls 4"` | `scan-proxy-worker` (1 paid scan), `anthropic` (3 paid calls) | up to 4 paid calls (two paid surfaces: if the wrapper asks to confirm once per surface, Claude answers each) |
   | `cmd /c "echo y| powershell -NoProfile -File test-external.ps1 -MaxPaidCalls 3"` | `anthropic-python` | up to 3 paid calls |
   | `.\android\test-external.ps1` (start `medium_phone` first, the emulator alone) | `revenuecat-android-sdk` | free |

   **you:** the paid ceiling. The three paid surfaces add up to 7 calls, the ceiling you approved at the last bundle; Claude asks again before running, and does not run past the number you give. A wrapper runs only the surfaces that are stale, so a surface that went stale after step 1 is covered by running the wrapper again, which is cheap. If a wrapper reports a failure, it is recorded as `fail`, the surface stays blocking, and Claude brings it to you before anything else.
4. `uv run scripts/external_freshness.py` again: nothing stale. Then `uv run scripts/external_gate.py check --platform android` and `--platform web` (they only read the record): both pass.
5. Commit `scripts/dashboard_data/test_results.json`, `scripts/dashboard_data/external_status.json` and `dashboard.svg` on `MPSkills` (the pre-commit hook regenerates the graphic from them). Never from a `ticket-*` branch.
6. **you:** Claude asks before the push. `git push` runs the gate (`core.hooksPath` must be `.githooks`; Claude checks it). After the push: `git rev-list --count origin/MPSkills..MPSkills` is 0, the push made a Pages **preview** (if #175's Cloudflare steps are done) and the live site is unchanged; the dashboard in the README shows the new statistics.

## Owner steps, in the order they come up

- [x] (Done: recorded on #175, `release`, gate only the release branch, previews stay on.) When #175's build session asks, answer its three decisions: the name of the release branch (recommended `release`), whether a push of `MPSkills` is still gated (recommended: gate only the release branch), whether previews of `MPSkills` stay on (recommended yes; the preview addresses must then be in Supabase's Redirect URLs list).
- [ ] #175 is merged (2026-11-05, b517d77). **Done 2026-11-05:** `release` created on `origin` at c1f1786 through the GitHub API (Claude, with your yes; no gate override recorded), the `CLAUDE.md` line added, Pages' production branch switched to `release` (you), Supabase's Redirect URLs checked (you; `https://*.rigcheck-web.pages.dev/**` is in the list). **Still to observe:** that the round's push of `MPSkills` makes only a preview and leaves the live site unchanged (Claude reminds you after the push), and, at a later release, the first promotion with `scripts/promote_release.py`. The original text of this step (the ticket's "Owner actions needed" has the exact steps): create the `release` branch on `origin` **at the commit that is live today (c1f1786)**, set Pages' production branch to it in the Cloudflare dashboard, check that a push of `MPSkills` makes only a preview, and that the first promotion changes the production site. Do this **before** the final push, so the push cannot change the live site. Apply the one `CLAUDE.md` line the build session posts.
- [ ] **Carried to the end of the Alpha set (#206 merged 2026-11-05 at b75528b; not a blocker for the push):** when the APK is rebuilt at the end of the Alpha set (`.\gradlew.bat assembleBeta -PappVersionCode=<n>`, 4 or more), check on the phone that a real **Continue with Google** sign-in lands where it was started: on the front page when you start it from the Rig picker's account row or balance chip, and back on the check's own screen when you start it from inside a check (a Scan error's "Sign in", or buying Scans while signed out). A device test cannot drive Google's own screen, so this is the only check of the Google path; the password path is covered by tests. Report any other result on #206's thread or as a new ticket. While you are on the phone, also try a password sign-in from the picker.
- [ ] Before the External bundle: close Android Studio and every other emulator or Claude session that has one running; have `web/.env.local` and the keys the wrappers read in place (a wrapper fails with the name of a missing one, and does not skip it).
- [ ] Set the paid-call ceiling when Claude asks (see step 3 above), and say go for the push.
- [ ] Clean up the empty `.claude/worktrees/ticket-197` and `ticket-198` folders after a reboot (something still holds them), and the older leftovers listed on the other sheet.

**Not in this round (decided):** #222 and #223 (font 2.0 on a 360 x 640 dp phone; Beta chain), #209 and #208 (guard follow-ups), #170, #171, #204, #210 to #221 (launch gates and owner steps), and every Alpha owner step (tester APK, adding testers, guide): those stay on [test-round-handoff.md](test-round-handoff.md) and [BETA_PLAN.md](../BETA_PLAN.md). If you want one of them before the push, say so and Claude adds a card.

## Run cards

### #206 Android login lands on the front page, not Account

**Worker A (1 of 3).** Starts now. Smallest and most visible of the three, so it goes first. Android: the single emulator, one Android ticket at a time.

1. In this main-checkout session type `/ticket-start 206`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-206`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-206` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-206"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #206

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The Android end-of-session command is `uv run scripts/android_session_end.py` (JVM tests, coverage floor, detekt; no device).
- A UI test needs the single emulator; no other Android ticket may be running. Start it with `uv run scripts/android_suite_loop.py --boot-only --emulator-arg=-no-window --emulator-arg=-no-audio` (headless: the emulator's window crashed in the host's NVIDIA OpenGL driver on 2026-10-27; it cold-boots the emulator on the software GPU, waits until it is steadily ready and leaves it running; a bare `emulator.exe` command is refused by the guard hook), and kill it when you are done. Run a test class as `uv run scripts/run_supervisor.py --device --output-limit-s 300 -- android/gradlew -p android connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=<fqcn>` (a bare Gradle device command is rewritten to this by the hook). A stalled run is stopped after its evidence is saved and exits 124 (`hung`); that is not a test failure: read `uv run scripts/run_status.py`, then run it once more on a freshly booted emulator. A run whose command ends because the emulator died is labelled `infra-abort` (reason `device lost after the command ended`, evidence saved) and is handled the same way; a run that ends `test-failed` with a healthy device is a real failure and is never retried.
- Use `adb -s emulator-5554` for every adb command: the owner's phone may be plugged in and must not be touched.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in its context's testing document, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: do not run the live External suite or any paid call. The owner runs the surface from the main checkout after the merge. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- RevenueCat is faked in the Android tests; no live or paid run.
- Process notes from #193 (it ran about nine device runs, five avoidable; each run costs 2 to 4 minutes): (a) pass `-Pandroid.testInstrumentationRunnerArguments.layoutScreenshots=true` on the FIRST layout run: `testsupport/LayoutChecks.kt` (`LayoutStateRunner`) then writes each state's PNG to `/data/local/tmp/<folder>/<frame>/` on the device, which survives Gradle's uninstall; pull with `MSYS_NO_PATHCONV=1 adb -s emulator-5554 pull /data/local/tmp/<folder> <dir>`. (b) Before writing the test, list the designer's frames for your screens (`annotation-legends.json`), make one test state per frame, and scroll each scrolled frame's state to the element its frame is scrolled to, so the screenshot matches the designer's PNG. (c) Put every touched class, shared components and test tooling included, in ONE run with `class=a,b,c`. (d) Apply all mutations together in one run and revert. (e) Aim for three device runs: layout alone to find failures, fix, then one final combined run with screenshots on the committed tree. (f) Read results from `android/app/build/outputs/androidTest-results/connected/debug/TEST-*.xml` (Gradle's console tail is too short). (g) Shared tooling fixed in #193: the test activity pans for the keyboard but `MainActivity` resizes (the runner now sets `adjustResize`), the touch-target check no longer reads clipped bounds, and a `testTag` after `.padding(...)` measures the content inside the padding (put the tag first when the map's size is the whole box). (h) In a worktree the Bash guard refuses compound commands (use script files), `cd` persists between calls (use absolute paths), and Git Bash rewrites `/sdcard` paths (set `MSYS_NO_PATHCONV=1`).
- Read every comment on the ticket before you start: the Deputy's triage comment adds acceptance criteria that are not in the ticket body.
- Cause, read from `android/app/src/main/java/com/rigcheck/app/ui/navigation/RigCheckNavHost.kt` (about lines 176 to 197): the Account tab shows `AccountScreen` while `AccountState.SignedOut` and the signed-in standing once it becomes `AccountState.SignedIn`, and nothing navigates when it flips, so the user stays on the Account tab. Fix it by going to the front page (the Rig picker, `RigCheckRoute.RigPicker`) on the change from signed out to signed in, and only on that change.
- Do not jump on every visit: opening the app already signed in, or tapping the Account tab while signed in, must still show the account page. Back from the front page must not return to the sign-in form (use `popUpTo`).
- Google sign-in returns through the same state change, so test the change itself. A device test cannot drive Google's own screen: say in your STATUS what stays manual for the owner (a sign-in with Google on the phone).
- Existing tests to keep green: `AccountScreenTest` and `RigCheckNavHostTest`. Run your own classes only (the full suite runs once at the end of the round, not per ticket). Do not change any Gradle or `libs.versions.toml` file: a change there makes two External surfaces stale.
- Start the emulator profile the ticket names with `uv run scripts/android_suite_loop.py --boot-only --avd <profile> --emulator-arg=-no-window --emulator-arg=-no-audio` (the profiles are `medium_phone`, `rc_small_phone_api36`, `rc_pixel_9_pro_xl_api37` and `rc_pixel_3a_api26`, all on G:; see "Device matrix (Tier 1)" in `android/TESTING.md`), one emulator at a time, and kill it with `adb -s emulator-5554 emu kill` before starting the next. With only one emulator running it is always `emulator-5554`.
- A failure in the first test that types a Rig nickname (`enterNickname`, `RigCheckNavHostTest`, `ScanInFlightNavigationTest`) on a freshly booted emulator can be the cold-start keyboard wait of #125 (up to 30 s): read the time of the failing test before you decide it is real, and say in your STATUS which it was.
- The ticket's decisions are already recorded in its DECISIONS comment: do not ask them again.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 206`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push. Afterwards stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe -s emulator-5554 emu kill`).

**Your part:** after the merge, on the phone: sign in with a password, then with Continue with Google, and check you land on the front page.

### #225 `ThreeButtonNavigationTest` on Android 8.0

**Worker A (2 of 3).** Starts when #206 is merged and its emulator is stopped. Android: the single emulator, one Android ticket at a time.

1. In this main-checkout session type `/ticket-start 225`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-225`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-225` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-225"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #225

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The Android end-of-session command is `uv run scripts/android_session_end.py` (JVM tests, coverage floor, detekt; no device).
- A UI test needs the single emulator; no other Android ticket may be running. Start it with `uv run scripts/android_suite_loop.py --boot-only --emulator-arg=-no-window --emulator-arg=-no-audio` (headless: the emulator's window crashed in the host's NVIDIA OpenGL driver on 2026-10-27; it cold-boots the emulator on the software GPU, waits until it is steadily ready and leaves it running; a bare `emulator.exe` command is refused by the guard hook), and kill it when you are done. Run a test class as `uv run scripts/run_supervisor.py --device --output-limit-s 300 -- android/gradlew -p android connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=<fqcn>` (a bare Gradle device command is rewritten to this by the hook). A stalled run is stopped after its evidence is saved and exits 124 (`hung`); that is not a test failure: read `uv run scripts/run_status.py`, then run it once more on a freshly booted emulator. A run whose command ends because the emulator died is labelled `infra-abort` (reason `device lost after the command ended`, evidence saved) and is handled the same way; a run that ends `test-failed` with a healthy device is a real failure and is never retried.
- Use `adb -s emulator-5554` for every adb command: the owner's phone may be plugged in and must not be touched.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in its context's testing document, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: do not run the live External suite or any paid call. The owner runs the surface from the main checkout after the merge. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- RevenueCat is faked in the Android tests; no live or paid run.
- Process notes from #193 (it ran about nine device runs, five avoidable; each run costs 2 to 4 minutes): (a) pass `-Pandroid.testInstrumentationRunnerArguments.layoutScreenshots=true` on the FIRST layout run: `testsupport/LayoutChecks.kt` (`LayoutStateRunner`) then writes each state's PNG to `/data/local/tmp/<folder>/<frame>/` on the device, which survives Gradle's uninstall; pull with `MSYS_NO_PATHCONV=1 adb -s emulator-5554 pull /data/local/tmp/<folder> <dir>`. (b) Before writing the test, list the designer's frames for your screens (`annotation-legends.json`), make one test state per frame, and scroll each scrolled frame's state to the element its frame is scrolled to, so the screenshot matches the designer's PNG. (c) Put every touched class, shared components and test tooling included, in ONE run with `class=a,b,c`. (d) Apply all mutations together in one run and revert. (e) Aim for three device runs: layout alone to find failures, fix, then one final combined run with screenshots on the committed tree. (f) Read results from `android/app/build/outputs/androidTest-results/connected/debug/TEST-*.xml` (Gradle's console tail is too short). (g) Shared tooling fixed in #193: the test activity pans for the keyboard but `MainActivity` resizes (the runner now sets `adjustResize`), the touch-target check no longer reads clipped bounds, and a `testTag` after `.padding(...)` measures the content inside the padding (put the tag first when the map's size is the whole box). (h) In a worktree the Bash guard refuses compound commands (use script files), `cd` persists between calls (use absolute paths), and Git Bash rewrites `/sdcard` paths (set `MSYS_NO_PATHCONV=1`).
- The helper is `android/app/src/androidTest/java/com/rigcheck/app/testsupport/NavigationMode.kt` (`use3Buttons()`). On Android 8.0 to 9 (API 26 to 28) there is no `navigation_mode` setting (`settings get secure navigation_mode` prints `null`) and no navigation overlay, and the phone always shows the on-screen bar, so the device is already on 3-button navigation: treat a missing setting as "already 3-button", with nothing to change and nothing to restore. Check every caller of `use3Buttons()` still works.
- On API 29 and up the helper must behave exactly as before (enable the overlay, wait for the mode to read `0`, restore the old mode afterwards).
- Device runs, one emulator at a time: `ThreeButtonNavigationTest` on `rc_pixel_3a_api26` (API 26), then again on `medium_phone` (API 36). Record the API 26 result in the "Device matrix (Tier 1)" section of `android/TESTING.md` in place of the #225 note.
- Start the emulator profile the ticket names with `uv run scripts/android_suite_loop.py --boot-only --avd <profile> --emulator-arg=-no-window --emulator-arg=-no-audio` (the profiles are `medium_phone`, `rc_small_phone_api36`, `rc_pixel_9_pro_xl_api37` and `rc_pixel_3a_api26`, all on G:; see "Device matrix (Tier 1)" in `android/TESTING.md`), one emulator at a time, and kill it with `adb -s emulator-5554 emu kill` before starting the next. With only one emulator running it is always `emulator-5554`.
- Do not change any Gradle or `libs.versions.toml` file.
- The ticket's decisions are already recorded in its DECISIONS comment: do not ask them again.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 225`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push. Afterwards stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe -s emulator-5554 emu kill`).

**Your part:** none.

### #224 Compose device tests on Android 17

**Worker A (3 of 3).** Starts when #225 is merged and its emulator is stopped. It changes a test library every Compose test uses, so it goes last. Android: the single emulator, one Android ticket at a time.

1. In this main-checkout session type `/ticket-start 224`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-224`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-224` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-224"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #224

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The Android end-of-session command is `uv run scripts/android_session_end.py` (JVM tests, coverage floor, detekt; no device).
- A UI test needs the single emulator; no other Android ticket may be running. Start it with `uv run scripts/android_suite_loop.py --boot-only --emulator-arg=-no-window --emulator-arg=-no-audio` (headless: the emulator's window crashed in the host's NVIDIA OpenGL driver on 2026-10-27; it cold-boots the emulator on the software GPU, waits until it is steadily ready and leaves it running; a bare `emulator.exe` command is refused by the guard hook), and kill it when you are done. Run a test class as `uv run scripts/run_supervisor.py --device --output-limit-s 300 -- android/gradlew -p android connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=<fqcn>` (a bare Gradle device command is rewritten to this by the hook). A stalled run is stopped after its evidence is saved and exits 124 (`hung`); that is not a test failure: read `uv run scripts/run_status.py`, then run it once more on a freshly booted emulator. A run whose command ends because the emulator died is labelled `infra-abort` (reason `device lost after the command ended`, evidence saved) and is handled the same way; a run that ends `test-failed` with a healthy device is a real failure and is never retried.
- Use `adb -s emulator-5554` for every adb command: the owner's phone may be plugged in and must not be touched.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in its context's testing document, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: do not run the live External suite or any paid call. The owner runs the surface from the main checkout after the merge. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- RevenueCat is faked in the Android tests; no live or paid run.
- Process notes from #193 (it ran about nine device runs, five avoidable; each run costs 2 to 4 minutes): (a) pass `-Pandroid.testInstrumentationRunnerArguments.layoutScreenshots=true` on the FIRST layout run: `testsupport/LayoutChecks.kt` (`LayoutStateRunner`) then writes each state's PNG to `/data/local/tmp/<folder>/<frame>/` on the device, which survives Gradle's uninstall; pull with `MSYS_NO_PATHCONV=1 adb -s emulator-5554 pull /data/local/tmp/<folder> <dir>`. (b) Before writing the test, list the designer's frames for your screens (`annotation-legends.json`), make one test state per frame, and scroll each scrolled frame's state to the element its frame is scrolled to, so the screenshot matches the designer's PNG. (c) Put every touched class, shared components and test tooling included, in ONE run with `class=a,b,c`. (d) Apply all mutations together in one run and revert. (e) Aim for three device runs: layout alone to find failures, fix, then one final combined run with screenshots on the committed tree. (f) Read results from `android/app/build/outputs/androidTest-results/connected/debug/TEST-*.xml` (Gradle's console tail is too short). (g) Shared tooling fixed in #193: the test activity pans for the keyboard but `MainActivity` resizes (the runner now sets `adjustResize`), the touch-target check no longer reads clipped bounds, and a `testTag` after `.padding(...)` measures the content inside the padding (put the tag first when the map's size is the whole box). (h) In a worktree the Bash guard refuses compound commands (use script files), `cd` persists between calls (use absolute paths), and Git Bash rewrites `/sdcard` paths (set `MSYS_NO_PATHCONV=1`).
- Cause, from the ticket: Espresso 3.5.1 (`espressoCore` in `android/gradle/libs.versions.toml`) reflects into `InputManager.getInstance()`, which Android 17 (API 37) removed, so every Compose UI test fails on `rc_pixel_9_pro_xl_api37` before it checks anything. Find the `androidx.test` versions that work on API 37 from the primary release pages (developer.android.com, `androidx.test`), and change only what is needed (`espresso-core`, and the runner, `ui-test-junit4` or `uiautomator` only if the failure points there). Test dependencies only: the shipped app and `android/app/build.gradle.kts` `implementation` lines do not change.
- If no released version works on API 37, stop: post `STATUS: BLOCKED` with what you found and the options (wait for a release, a workaround, an exclusion), and do not force a pre-release into the build.
- Device runs, one emulator at a time, `SystemBarsTest` and `PaywallScreenTest`: on `rc_pixel_9_pro_xl_api37` (must now run, pass or fail on its merits), on `medium_phone` (API 36) and on `rc_pixel_3a_api26` (API 26), both of which still pass 35 of 35. Because the bump touches every Compose test, run the full instrumented suite once on `medium_phone` as well (`uv run scripts/android_suite_loop.py --runs 1 --retry-infra-abort`) and say the count in your STATUS (it was 436 tests at #197).
- Record the result in the "Device matrix (Tier 1)" section of `android/TESTING.md` (configuration 3). A failure on its merits on API 37 is a finding: file it as its own ticket, do not fix the app here (#222 and #223 stay in the Beta chain).
- Start the emulator profile the ticket names with `uv run scripts/android_suite_loop.py --boot-only --avd <profile> --emulator-arg=-no-window --emulator-arg=-no-audio` (the profiles are `medium_phone`, `rc_small_phone_api36`, `rc_pixel_9_pro_xl_api37` and `rc_pixel_3a_api26`, all on G:; see "Device matrix (Tier 1)" in `android/TESTING.md`), one emulator at a time, and kill it with `adb -s emulator-5554 emu kill` before starting the next. With only one emulator running it is always `emulator-5554`.
- A change to `libs.versions.toml` makes the External surfaces `revenuecat-android-sdk` and `supabase-auth` stale. They are already stale and run in the final bundle: do not run them yourself.
- The ticket's decisions are already recorded in its DECISIONS comment: do not ask them again.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 224`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push. Afterwards stop the emulator (`G:\Android\Sdk\platform-tools\adb.exe -s emulator-5554 emu kill`).

**Your part:** none.

### #175 Web publishes from a release branch

**Worker B.** Starts now, beside Worker A (no emulator, no Gradle: pytest and git only).

1. In this main-checkout session type `/ticket-start 175`. It assigns the ticket to you and creates the folder `.claude/worktrees/ticket-175`; if it stops, it says why.
2. Open a **new** Claude session in `G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-175` (in a terminal: `cd "G:\Claude Experiment\VSCode\VSCodeProj\MattPocock\HDTTools\.claude\worktrees\ticket-175"`, then `claude`). Paste everything in the box below as its **first message**, as one message with nothing added.

```
/mattpocock-skills:implement #175

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.

Test-round additions:
- The end-of-session commands are `uv run scripts/static_checks.py core` and the offline tests that `uv run scripts/test_planner.py` lists. Do not start Gradle or the emulator.
- Only `scripts/`, `tests/`, `docs/` and the testing documents change.
- Judge each test by whether it would find or prevent a real bug and whether it adds run time; do not add tests only to raise a coverage number.
- A new test file must be named in `tests/TESTING.md`, and a new `slow`-marked test file in `scripts/test_planner_config.json`; two tests fail otherwise.
- Live runs: no live External suite and no paid call. Do not commit changes to `scripts/dashboard_data/external_status.json` or `dashboard.svg` from the branch.
- Never edit text between `<!-- HUMAN-WRITTEN ... -->` and `<!-- END HUMAN-WRITTEN -->` markers.
- Besides `scripts/` and `tests/`, this ticket changes `.githooks/pre-push`, `scripts/external_gate.py` and the pages under `docs/` (`docs/BUILD_AND_DEPLOY.md` sections 5 and 6, "External release gate" in `TESTING.md`, and any `docs/agents/` page that says a push to `MPSkills` publishes Web). Do not edit `CLAUDE.md`: post the one line to add as the ticket asks.
- Test the promote command and the gate against throwaway git repositories only. Never push, never create the release branch on `origin`, never touch the Cloudflare dashboard: those are the owner's steps, and the ticket's "Owner actions needed" lists them exactly.
- The gate's rule today is that a push of `MPSkills` whose diff touches `web/`, `workers/scan-proxy/` or `android/` needs the External surfaces of that chain fresh. Keep that behaviour for whatever the decisions leave gated, and say in your STATUS which pushes are gated after your change, because the owner's push at the end of this round goes through it.
- The ticket's `## Decisions` section is still open (the name of the release branch, whether a push of `MPSkills` stays gated, whether previews of `MPSkills` stay on): ask its three questions with AskUserQuestion before building, and post the answers as a `DECISIONS` comment.
```

3. When that session says it is done, type `/ticket-finish` in it. At the end it asks whether to move the shell out of the worktree into the main checkout; answer **Yes**.
4. Back in this main-checkout session type `/ticket-merge 175`. Claude reviews the work, adds any missing test or testing-document row (asking you first), merges, and asks before any push.

**Your part:** answer the three decisions when the session asks; after the merge do the Cloudflare steps in "Owner steps".


## Things to remember

- Each card's step 3 (`/ticket-finish`) runs the offline suites once on the ticket and remembers the pass; step 4 (`/ticket-merge`) is Claude's review. Claude adds any missing test or testing-document row at the merge and asks you first.
- The destructive-command guard (#207) asks before a delete, move or overwrite whose target is a variable, a wildcard, `~` or outside the project. A held command from a build session's sub-agent is refused, not asked. A `$VAR` assigned a literal on the line above still asks (noted on #209): answer Yes when you can see the literal.
- Build sessions must write the literal scratch path, or use their Write and Edit tools, instead of `printf >` or `sed -i` for files outside the project.
- `--maxprocesses=8` caps `-n auto` because 24 workers ran this machine out of memory; with the emulator and Gradle up, a Python test that creates a real git repo can fail with a memory error (about 3 in 16 runs). It is memory, not a regression: run it again.
- An emulator a session started holds its `emulator.log` open and blocks deleting the ticket folder after `/ticket-merge`: stop the emulator and close any terminal open in the ticket's folder, then `rmdir` the leftover.
- The External bundle goes stale daily: it is run once, at the end, with the emulator alone and the paid ceiling you set.
- The scripts never push. A push needs your yes every time. Pages now publishes Web from `release` (switched 2026-11-05), so a push of `MPSkills` makes only a preview.
