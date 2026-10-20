# Test-first round: how to run each ticket

Working notes for the test-first round (map #49, decisions on #58 and #59, written 2026-10-19, updated after the lane A, lane B and first Android merges). They are temporary: delete this file when the round ends. The general flow is in [ticket-skills.md](ticket-skills.md); this file holds what is specific to the round.

## Where the round stands

Merged: #134, #129, #130, #41, #128, #43, #127, #66, #44, #84, #115, #135, #124, #136, #142, #131, #133, #143 (#141 closed as its duplicate). Nothing in build when this was written. #143 split the Claude surface in two: `anthropic` (the Worker, run by `workers\scan-proxy\test-external.ps1`) and `anthropic-python` (run by the root `test-external.ps1`), both checked against `test-vectors/vision_external_cases.json` and `ExampleDocs/golden_fields.json`. After it merged both were stale; the owner approved 6 paid calls on 2026-10-20 and both passed against the shared golden data (pass records 615e552), and everything up to that commit is pushed. Follow-ups filed along the way: #138 (Worker preview deploy), #139 (cache the gate's registry lookups), #140 (Streamlit `FIELDS` vs the Claude extractor keys), #141 (rename the `api` package; the same work as #136).

**Pushed on 2026-10-20** (owner approved the #115 Web wording and the push): everything up to the External re-run commit 0f88264 is on `origin/MPSkills`, and Pages rebuilt Web. Wrangler 4.151.3 had made `pages-site` and `scan-proxy-worker` stale, so both were re-run first (1 paid call) and the gate passed without an override. The pre-push gate from #43 is live in the main checkout: a push of `MPSkills` that touches `web/`, `workers/scan-proxy/` or `android/` is refused while an External surface is stale. A new wrangler release makes the two Cloudflare surfaces stale again; `uv run scripts/external_freshness.py` says which. The honest ways through a stale gate are a real run, or `EXTERNAL_GATE_FORCE_REASON="why" git push` (records an override on the dashboard; commit the changed `scripts/dashboard_data/external_status.json`).

**External sanity run, done 2026-10-19, owner-approved (4 paid calls ceiling):** all seven stale surfaces passed and are recorded in `external_status.json` (commit 95ae133).

- `powershell web\test-external.ps1`: `supabase-auth`, `supabase-tables`, `pages-site`, `revenuecat-web-billing` (32 tests, free).
- `powershell workers\scan-proxy\test-external.ps1 -MaxPaidCalls 4`: `scan-proxy-worker` (1 paid call), `worker-token-verification`, and `anthropic` (3 paid calls). It tested the Worker as deployed; no deploy was made (no Worker source file changed in any merge of the round, the last change was 2026-10-15).
- To answer the paid prompts from a non-interactive shell use `cmd /c "echo y| powershell -NoProfile -File workers\scan-proxy\test-external.ps1 -MaxPaidCalls N"`. Piping several `'y'` lines from PowerShell answered the second prompt but declined the first (recorded `skipped`, which leaves the surface stale and spends nothing).

## The flow for every ticket

| Step | Where | Who | Command |
|---|---|---|---|
| 1. Start | main checkout | you | `/ticket-start N` (prints a paste-ready prompt) |
| 2. Build | a new `claude` session inside `.claude/worktrees/ticket-N` | you | paste the printed prompt, then the additions below |
| 3. Finish | the same worktree session | you | `/ticket-finish` |
| 4. Merge | main checkout (the merge session) | you type it, Claude carries it out | `/ticket-merge N` (add `--allow-status` to go past a `PARTIAL`) |
| 5. Push | main checkout | Claude asks first | never automatic; pushing `MPSkills` deploys Web, and the gate above applies |

- A new build session for every ticket. The merge session can be cleared when convenient: the state lives in GitHub, git and `docs/agents/`.
- Start the next ticket in a lane only after the previous one is merged, so it is cut from the updated `MPSkills`.
- After a merge Claude runs the planner's list on the merged tree when the baseline moved (another ticket merged since this one was cut). Since #128 the merge step also asks the ledger which suites already passed at the branch tip's tree and skips those.
- A merge review that finds a gap in the tests asks for one added test, commits it on the branch and posts its own `STATUS: READY TO MERGE` naming the new commit.

## What to paste: the printed prompt plus these additions

Paste exactly what `/ticket-start N` prints (`/mattpocock-skills:implement #N` and the handoff line: don't push, don't close the issue, finish with a STATUS comment, run single test files only and leave the full run to `/ticket-finish`, live External suites only when a criterion names one, `## Decisions` asked with AskUserQuestion). Then add:

```
Test-round additions:
- For a full Python run use `uv run pytest -n auto --maxprocesses=8` (about 45 s).
  The slow tooling tests are left out of planner runs unless the diff touches
  what they check.
- No live or paid runs. External suites are run from the main checkout with the owner's go-ahead.
- Judge each test by whether it would find or prevent a real bug and whether it
  adds run time; do not add tests only to raise a coverage number.
```

### Extra lines for specific tickets

- **Planner tickets (#133, #136):** "These change `scripts/test_planner.py` and `scripts/test_planner_config.json`, as did #128, #66 and #135. If another planner ticket merged since you were cut, rebase before finishing."
- **Android tickets (#131, #137, #133):** "If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The JVM coverage floor is 95% over the allow-listed decision logic."
- **Emulator tickets (#75, #39, #40):** "This needs the single emulator; no other Android ticket may be running. Start it with `-gpu swangle_indirect` (the AVD default host graphics caused the aborts #127 traced), or use `uv run scripts/android_suite_loop.py --runs N --expected-tests <count>` for a repeat-run count; it cold-boots per run. The instrumented suite is 142 tests at the last merge."
- **Starting an Android ticket:** `/ticket-start` guesses Android only from an Android title or an `android/` file path in the body, so start #40 with `--android` (its text names neither). If an assigned ticket is wrongly counted as holding the emulator (its title says Android but it never uses it), name it with `--emulator-free <M>`.
- **#41-style External tickets:** the live run is the owner's; the ticket's session must not run it.

## Order of work (lanes)

Two build lanes can run in parallel; tickets inside a lane share files, so they go one at a time.

| Step | Lane A (planner and Python) | Lane B (tooling) |
|---|---|---|
| done | #134, #129, #128, #66, #135, #136, #133 | #130, #41, #43, #44, #115, #142, #143 |
| next | (none planned beyond the Android lane) | #67 session-start debt report (needs #66, merged) |

Android lane (one at a time; the single emulator): done #127, #84, #124, #131. Next #137 (JVM only, can run beside any other lane), then #75, #39, #40 together (two paid scans, owner confirms first).

Last: #105 (after the owner's dashboard step), #64 (docs refresh), then a final run of whichever External surfaces went stale again (`uv run scripts/external_freshness.py` first; from the main checkout; ask before each live run and before pushing). Optional: #132. Deferred: #68, #69, #70, #72, #100.

## Things to remember

- `--maxprocesses=8` caps `-n auto` because 24 workers ran this machine out of memory. Even at 8, the Python suite occasionally errors in tests that create a real git repo (`git init` or `git worktree add` exits 3221225773 or "WinError 1455: paging file too small") when the emulator, Gradle and other sessions are up. About 3 in 16 runs. It is memory, not a regression; re-run, and consider a lower worker count with the emulator running.
- Set the `medium_phone` AVD's Graphics to Software in Device Manager (the file is `G:\Android\EmulatorHome\avd\medium_phone.avd\config.ini`, `hw.gpu.mode`). Not yet confirmed done. The loop script does not depend on it; a plain `gradlew connectedDebugAndroidTest` or `android/release.ps1` against a default-graphics emulator can still abort.
- The emulator that `android_suite_loop.py` starts holds its `emulator.log` open, which blocks deleting the ticket worktree folder after `/ticket-merge`. Restart or close the emulator, then `rmdir` the leftover folder (see [worktree-setup.md](worktree-setup.md) for the Windows long-path steps). After the 2026-10-20 reboot all the leftover folders under `.claude/worktrees/` were removed (they held only empty directories and two `emulator.log` files).
- The planner now treats `*.md`, `docs/*` and `ClaudePlans/*` as docs-only (plans nothing), follows `shares_with` and `depends_on` links to downstream contexts (a Core source change also queues Streamlit's tests), and does not list a deleted test file. `--since-verified` plans from each context's last verified commit in the ledger. Config choices on #66 are recorded in its DECISIONS comment.
- Open follow-up from the #130 merge: one more test case for the prefix-matching direction in `scripts/coverage_lib.py` (allow `ScanApiClient`, leave `ScanApiClientKt` unlisted); add it when a ticket next touches that file.
