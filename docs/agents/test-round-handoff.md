# Test-first round: how to run each ticket

Working notes for the test-first round (map #49, decisions on #58 and #59, written 2026-10-19). They are temporary: delete this file when the round ends. The general flow is in [ticket-skills.md](ticket-skills.md); this file holds what is specific to the round.

## The flow for every ticket

| Step | Where | Who | Command |
|---|---|---|---|
| 1. Start | main checkout | you | `/ticket-start N` (prints a paste-ready prompt) |
| 2. Build | a new `claude` session inside `.claude/worktrees/ticket-N` | you | paste the printed prompt, then the additions below |
| 3. Finish | the same worktree session | you | `/ticket-finish` |
| 4. Merge | main checkout (the merge session) | you type it, Claude carries it out | `/ticket-merge N` (add `--allow-status` to go past a `PARTIAL`) |
| 5. Push | main checkout | Claude asks first | never automatic; pushing `MPSkills` deploys Web |

- A new build session for every ticket. The merge session can be cleared when convenient: the state lives in GitHub, git and `docs/agents/`.
- Start the next ticket in a lane only after the previous one is merged, so it is cut from the updated `MPSkills`.
- After a merge Claude runs the planner's list on the merged tree only when the baseline moved (another ticket merged since this one was cut).

## What to paste: the printed prompt plus these additions

Paste exactly what `/ticket-start N` prints (`/mattpocock-skills:implement #N` and the handoff line: don't push, don't close the issue, finish with a STATUS comment, live External suites only when a criterion names one, `## Decisions` asked with AskUserQuestion). Then add:

```
Test-round additions:
- Run single test files and typechecks while you work. Do not run the full suite
  yourself; /ticket-finish runs it, so a second full run here repeats it.
- For a full Python run use `uv run pytest -n auto` (about 45 s). The slow tooling
  tests are left out of planner runs unless the diff touches what they check.
- No live or paid runs. The stale External suites are bundled at the end of the
  round and run from the main checkout.
- Judge each test by whether it would find or prevent a real bug and whether it
  adds run time; do not add tests only to raise a coverage number.
```

Drop the first bullet once #128 (tree-hash skip) has merged and the printed handoff line says it itself.

### Extra lines for specific tickets

- **Planner tickets (#128, #66, #133, #136):** "These change `scripts/test_planner.py` and `scripts/test_planner_config.json`, as do the other planner tickets. If another planner ticket merged since you were cut, rebase before finishing."
- **Lockfile tickets (#135):** "This changes `pyproject.toml` and `uv.lock`. Run `uv lock` after any rebase."
- **Android tickets (#131, #137, #133):** "If you add or move a class in `domain`, `data` or `ui`, classify it in `android/coverage-logic.toml` (allow-list, or waiver with a reason). The JVM coverage floor is 95% over the allow-listed decision logic."
- **Emulator tickets (#127, #84, #124, and #75, #39, #40):** "This needs the single emulator; no other Android ticket may be running. Reboot a long-running emulator before the suite."
- **#41-style External tickets:** the live run is deferred to the bundle; the ticket's session must not run it.

## Order of work (lanes)

Two build lanes run in parallel; tickets inside a lane share files, so they go one at a time.

| Step | Lane A (lockfile and planner) | Lane B (External and coverage) |
|---|---|---|
| done | #134, #129 | #130, #41 |
| now | **#128** tree-hash skip | **#43** pre-push gate |
| next | #66 planner from last-verified | #44 dashboard |
| then | #135 remove the FastAPI app | #115 shared Scan outcomes fixture |
| then | #133 session-end command (needs #130 and #66) | #67 session-start debt report (needs #66) |
| then | #136 move `breakdown.py` (needs #135, after the planner tickets, before #45) | |

Android lane (emulator, free now that #118 is merged): #127, then #84, then #124; #131 and #137 (JVM only) alongside; then #75, #39, #40 together (two paid scans, owner confirms first).

Last: #105 (after the owner's dashboard step), #64 (docs refresh), then one bundled run of the stale External suites (`uv run scripts/external_freshness.py` first; run from the main checkout; ask before each live run and before pushing). Optional: #132. Deferred: #68, #69, #70, #72, #100.

## Things to remember

- Once #43 lands, a stale External surface blocks a push that touches `web/`, `workers/scan-proxy/` or `android/`. `scan-proxy-worker` is stale until its first recorded run, which costs one paid scan. Plan the bundled run before or soon after #43 merges.
- `--maxprocesses=8` caps `-n auto` because 24 workers ran this machine out of memory.
- A leftover empty `.claude/worktrees/ticket-N` folder after a merge means a session is still open in it; close the session, then `rmdir` it (Windows long paths: see the notes in [worktree-setup.md](worktree-setup.md)).
- Open follow-up from the #130 merge: one more test case for the prefix-matching direction in `scripts/coverage_lib.py` (allow `ScanApiClient`, leave `ScanApiClientKt` unlisted); add it when a ticket next touches that file.
