# Artemis (google/artemis) for on-phone testing: what it is, how to install it, how to fit it into the ticket skills, how to write test cases with it

Research only. Nothing was installed, cloned, run or called, and no repo code or ticket was changed to produce this. All sources were read on 2026-10-26 and are cited as a URL or a path inside the `google/artemis` repository. Each claim is marked **Confirmed** (stated by the source), **Indirect** (inferred from first-party code or metadata) or **UNCONFIRMED** (not shown by any source I read). The owner has not decided to adopt it; this file records the options and a recommended order if the answer is yes.

## Recommendation (short)

Use Artemis as an **exploration aid and a small pre-release smoke pack, never as a gate.** It is an AI agent, so a run is paid, slow and not repeatable; the tests that count stay deterministic Compose tests. Its own rules file says the same: explore with Artemis, then write deterministic test code. Install it by hand, pinned to a commit, in a folder outside the repo on G:, with its own Gemini key and spend cap, on the emulator first. Do not run its one-click script, and do not run `artemis mcp --install` (both write system tools or global config). The project is young and unversioned, so expect no support (see Risks).

## Evidence

| Fact | Source | Status |
|---|---|---|
| Apache-2.0; created 2026-08-13; last push 2026-10-01; no releases and no tags (pin a commit: the `main` head read was `351ca8422f`); about 15,000 stars; 61 open issues on the issues page (165 counting pull requests); issue #192 asks "Was this project abandoned?" | https://github.com/google/artemis, https://github.com/google/artemis/releases, GitHub API (`repos/google/artemis`, `commits`, `tags`) | Confirmed |
| Turns plain-language instructions into Android actions; needs a real phone with USB debugging, or an emulator; Python 3.12 or newer | README, `pyproject.toml` (`requires-python >=3.12`) | Confirmed |
| Interfaces: CLI (`uv run artemis run "..." --profile flash\|pro`), web console on `http://localhost:8000`, an MCP server with the tools `mobile_run_task`, `mobile_manage_task`, `mobile_get_device_state`, `mobile_inspect_trace`, `mobile_diagnose`, and a Python SDK `artemis-client` that talks to the local daemon over HTTP | README, `mcp_server/README.md`, `packages/artemis-client/README.md` | Confirmed |
| **Flash** is one reactive loop, about 3 to 5 s a step, with no plan and **no pre-execution safety net**. **Pro** is a planner, operator and checker, about 15 to 40 s a step, with a safety net and `verification_level` off, final (default), checkpoints or strict; plans carry verify and assert items | README, `mcp_server/rules.md` | Confirmed |
| Model providers: Google Gemini (default `gemini-3.8-flash` in `config/artemis.jsonc`), OpenAI, Anthropic, OpenRouter, xAI, and a local-Ollama preset | `.env.example`, `config/artemis.jsonc` | Confirmed |
| Screenshots, UI element lists and session video go to the configured provider; the config has no telemetry switch. `pyproject.toml` declares a `posthog` dependency; code search found no use of it | `config/artemis.jsonc`, `pyproject.toml`, GitHub code search | Confirmed (declared); **UNCONFIRMED** (used) |
| `start.bat` only launches `scripts/start.ps1`, which installs `Google.PlatformTools`, `Gyan.FFmpeg`, `Genymobile.scrcpy` and Node through winget (may need Administrator), downloads uv, patches a file inside `node_modules`, and offers to write MCP config and agent rules into IDE folders (for Claude, `~/.claude/rules/artemis.md`, a global file every project reads) | `start.bat`, `scripts/start.ps1` | Confirmed |
| The first task installs an "Artemis Accessibility Helper" on the phone (a permanent notification and an Accessibility entry). `ARTEMIS_HELPER_AUTO_INSTALL=false` stops that; `artemis helper install`, `status` and `uninstall` manage it; the README says it listens only on the phone and sends nothing elsewhere | README, `.env.example` | Confirmed |
| `mcp_server/rules.md` tells the agent to explore with Artemis first, then write **deterministic** test code with explicit waits ("Runnable Code Principle"), locating by id or text before coordinates ("Dynamic-First, Coordinate-Fallback") | `mcp_server/rules.md` | Confirmed |
| "99%+ on AndroidWorld" is the project's own claim; the README names no model, profile or run count | README | Confirmed (as a claim); **UNCONFIRMED** (as a result) |
| The SDK documents no assertion helpers and no pytest example; the daemon has no built-in authentication (the docs suggest an SSH tunnel) | `packages/artemis-client/README.md` | Confirmed |
| Environment variables: `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPEN_ROUTER_API_KEY`, `XAI_API_KEY`, `ARTEMIS_HIERARCHY_BACKEND` (auto, helper, uiautomator), `ARTEMIS_HELPER_AUTO_INSTALL`, `ARTEMIS_KEEP_DEVICE_AWAKE`, `ARTEMIS_DEFAULT_PROFILE` (flash default), `ADB_HOST`, `ADB_PORT`, `ADB_DEVICE_SERIAL` | `.env.example` | Confirmed |
| A device runs one task at a time (a per-device lock); different devices run in parallel | `mcp_server/README.md`, `mcp_server/rules.md` | Confirmed |

This machine on 2026-10-26: `adb` is at `G:\Android\Sdk\platform-tools` but not on `PATH`; `uv` and Node 24 are present; `scrcpy` and `ffmpeg` are not; the `medium_phone` emulator (`emulator-5554`) was running; C: had 49 GB free (90% full) and G: 1.3 TB.

## Plan A: installation (Windows, no `start.bat`)

Manual and pinned, in a folder outside the repo, because the one-click script installs system tools and writes global config, which `CLAUDE.md` requires asking about, and C: is space-constrained.

1. **Ask first, with the exact path** (`AskUserQuestion`): `G:\Tools\artemis`. Approving this file is not the install approval.
2. `git clone https://github.com/google/artemis.git G:\Tools\artemis`, then `git checkout 351ca8422f`; record the SHA. No update unless the owner asks.
3. **Read before running:** search `artemis/` and `third_party/mobile_use` locally for `posthog` and any outbound call. If it sends data anywhere, stop and report.
4. `uv sync` inside the clone (its own `.venv`). Skip the Angular console and the Node build; the CLI and the MCP server do not need them.
5. `.env` inside the clone (never in this repo): `GEMINI_API_KEY` typed by the owner (never printed or pasted into chat), `ARTEMIS_HELPER_AUTO_INSTALL=false`, `ARTEMIS_DEFAULT_PROFILE=flash`. Put `G:\Android\Sdk\platform-tools` on `PATH` for the session.
6. **Spend cap:** the Gemini key (owner decision, 2026-10-26: a separate Gemini key, never the Worker's Anthropic key, whose $30 monthly limit protects the scan service) gets its own budget and alert in Google's billing before the first run.
7. **Device order:** the emulator first. A real phone only if it is a dedicated test phone, because the helper is an Accessibility service and screenshots go to Google. Install the helper by hand with `artemis helper install`.
8. **Smoke:** `uv run artemis doctor`; then `uv run artemis run "Open Settings and tell me the Android version" --profile flash`; then one RigCheck screen on the emulator. Record the cost of each run.
9. **Claude Code hookup:** `claude mcp add --scope local`, pointing at the clone's `.venv` Python with `-m mcp_server` and the clone as the working directory. That lives in the owner's user config, not in git. Do not run `artemis mcp --install` (it writes global rules). Reload the MCP server after any `.env` change. The README gives no Claude Code snippet, so this command form is **UNCONFIRMED** until tried.
10. **Rollback:** `artemis helper uninstall`, delete `G:\Tools\artemis`, revoke the key.

Optional later, each with its own ask: portable `scrcpy` and `ffmpeg` on G: (video features), and the web console.

## Plan B: fitting it into `/ticket-start`, `/ticket-finish` and `/ticket-merge`

Artemis is non-deterministic, paid and needs a device, so it is **evidence, never a gate**. `docs/agents/ticket-skills.md` already has the slot: device and paid runs are `not run here` or `manual`, and the verification ledger records only deterministic passes.

| Where | Change |
|---|---|
| New `docs/agents/artemis.md` | Where Artemis is installed, the safety rules below, how to start a run, and the scenario-card format. Adapt `mcp_server/rules.md` here rather than installing it globally. |
| `/ticket-start` (`scripts/ticket_start.py`) | For an Android ticket (the existing `--android` detection) the handoff line adds one sentence pointing at `docs/agents/artemis.md`. An Artemis run counts as using the single emulator, so the existing "emulator in use" check must treat it so (Artemis also has its own per-device lock). Tested in `tests/test_ticket_start.py`. |
| Ticket body | An optional `## On-device scenarios` section holding scenario cards, written like `## Decisions`. |
| `/ticket-finish` (`scripts/ticket_finish.py`) | If the ticket has that section, the STATUS report gets a "device exploration" row: scenarios run, trace ids, bugs filed, and one line for each path that became a deterministic test. It is never a gate and never forces `PARTIAL`; the criterion-to-test table is unchanged. Tested in `tests/test_ticket_finish.py`. |
| `/ticket-merge` | The reviewer may re-run one named scenario as a spot-check, only with the owner's go-ahead and a budget (the same rule as live External suites). Mutation checks stay deterministic. |
| `scripts/test_planner_config.json`, `android/TESTING.md` | A `manual` planner entry "on-phone exploration (needs a device and a paid key)" beside the instrumented suite, an "On-phone exploration" subsection, and a row for each new test file (`tests/test_testing_docs.py` enforces the row). |
| Money and safety | Treated like paid suites: an owner-set run budget in the session, each run asked through `AskUserQuestion`, spend noted in the ticket. Test accounts and test cards only (`docs/CreditCardTest.md`); the beta build only (Test Store key), never a production-key build; Flash has no safety net, so use Pro for anything destructive (deleting a Rig, signing out); keep real personal screens off the phone. |

Tickets to propose, filed only when the owner agrees: (1) install and `docs/agents/artemis.md`; (2) the skill changes and their tests; (3) the first scenario pack.

## Plan C: developing new on-phone test cases

Artemis explores and discovers; **deterministic code is the test.** This matches the owner's rule that tests are judged by the bugs they find, and it is the workflow Artemis's own `mcp_server/rules.md` prescribes.

1. **Scenario card**, in plain words, in the ticket or under `docs/agents/artemis-scenarios/`: the goal, the precondition (account, Free or Pro, granted scans, beta APK `versionCode`), the steps, the observable result that means pass, what fail looks like, and the test data.
2. **Explore** with Flash on the emulator (cheap). Use Pro with `verification_level=checkpoints` when the path is ambiguous. Read the trace (`mobile_inspect_trace`) for exact screen text, transitions, timing and surprises. A surprise is a bug-ticket candidate.
3. **Codify** the verified path as a Compose instrumented test (`android/app/src/androidTest/.../ui/screens/{Screen}Test.kt`, using the existing fakes such as the scan sender and RevenueCat), with explicit waits and semantic locators (text, content description, test tag) before coordinates. Name it in `android/TESTING.md`; the merge review does its usual mutation check.
4. **Keep as an Artemis smoke scenario only what code tests cannot reach:** installing the beta APK over an earlier one, Google sign-in with the upload key on a real device, the soft keyboard and system dialogs, rotation and process death during a scan, camera or photo-picker permissions, and a live round trip to Supabase and the scan service. Cap the pack at about 10 cards and run it before each APK goes to testers, within a budget.
5. **Verdicts:** an Artemis result is never a recorded pass. Run a failing scenario twice; if the runs disagree, fix the card or file a bug, never retry until green. Record the trace id in the ticket.
6. **Judge by bugs found:** per scenario keep runs, cost and bugs found, and retire a scenario that never finds one.
7. **First candidates, from Alpha:** beta APK first launch, email sign-up, a manual check, save a Rig, History appears; Google sign-in on the beta build; a Pro purchase on the Test Store; a scan with a photo pushed to the phone; the Free account at the 5-Rig cap (#169); killing the app mid-scan (#118).

## Risks and open items

- **Maturity:** created 2026-08-13, no releases, last push 2026-10-01, and an open "abandoned?" issue. Pin a commit and expect no support.
- **Cost:** unknown per run until the first ten are measured.
- **Data:** screenshots and video of the phone go to the model provider. The `posthog` dependency is declared and its use is unknown (Plan A step 3). `third_party/mobile_use` is code from another company (Apache-2.0, Minitap, Inc., per the README).
- **Compose visibility:** Artemis reads the screen from the accessibility tree plus screenshots, so Compose test tags are not visible to it unless the root sets `testTagsAsResourceId`. A later small code change; not needed to start.
- **Windows:** the project has a Windows launcher, but an open issue (#172) concerns a console window; expect rough edges.
- **Nothing here was tried:** every command above comes from the README, `.env.example` or `mcp_server/README.md`, except the `claude mcp add` form (marked **UNCONFIRMED**).

## Decisions still open (not asked yet; the owner is not ready to start)

1. **Starting branch** for the work that adds docs, skill and script changes (default `MPSkills`; never `main`). `ticket_start.py` and `ticket_merge.py` assume `MPSkills`, so a different base would need those changed or kept on `MPSkills`.
2. **Install location** (`G:\Tools\artemis` proposed), asked just before anything is cloned.
3. Whether to file the three proposed tickets, and under which parent.
