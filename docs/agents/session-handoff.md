# Session handoff

How sessions (and the person running them) pass status to each other. Ticket work runs in separate sessions, usually one per git worktree, and `/implement` cannot be called by a sub-agent, so status has to travel in a form any session can read.

## Where status goes

1. **A comment on the ticket** is the default and the record. It outlives the session and the worktree, and it needs no commit. Do not add a committed handoff directory: it conflicts across branches and drifts from the tracker.
2. **A scratch file outside the repo** is for live notes between sessions that are running right now (for example "#28 is editing `Account.tsx`"). Put it at `%TEMP%\hdttools-status\ticket-<N>.md` (the OS temp directory, the same place the `/handoff` skill writes). It is local and temporary. Anything needed after the session ends belongs in a ticket comment instead.

## Claiming a ticket

When a session starts a ticket, assign the ticket to the person driving the work (`gh issue edit <N> --add-assignee @me`). An assigned open ticket is in flight; skip it.

## The ticket comment

Post one when the session finishes, stops, or is blocked. Start with the status line so it can be found by search.

```markdown
STATUS: READY TO MERGE | PARTIAL | BLOCKED

Branch: `<branch>` at `<sha>` (worktree: `<path>`; pushed: yes/no)

| Criterion | Proven by (test file and name) |
|---|---|
| ... | ... |

Commands run and results: <suite, pass/fail counts, typecheck, lint, build>
Code review: <findings and how each was handled>

Not done, and why: <or "nothing">
Owner actions needed: <dashboard steps, env values, decisions; or "none">
Follow-up tickets filed: <#N title; or "none">
```

- `READY TO MERGE` means every acceptance criterion is met by an automated test.
- `PARTIAL` or `BLOCKED` names the exact criterion or assumption and the evidence, and what was completed. Do not weaken a criterion to make a ticket pass; a mistaken criterion is reported here for the owner.
- Never include secret values. Say where a secret lives, not what it is.

## Rules that stay in force

- Sessions do not push and do not close the ticket. Whoever merges verifies (re-runs the suites, traces each criterion to a test, spot-checks by mutation), merges into `MPSkills`, commits, closes the ticket with a comment, and asks before any push.
- Do not commit `.env*`, `scripts/dashboard_data/external_status.json`, or a regenerated `dashboard.svg` from a feature branch.
- Android tickets share one emulator, so run them one at a time.
