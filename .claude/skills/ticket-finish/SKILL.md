---
name: ticket-finish
description: In a ticket worktree after /implement, run the required suites, map each criterion to a test, review, and post the STATUS comment.
disable-model-invocation: true
---

Finish the ticket this worktree (`ticket-<N>`) was cut for. Run it **inside the worktree**, after `/implement`. Convention and comment template: `docs/agents/session-handoff.md`. The script refuses a `READY TO MERGE` it cannot back, so the work below has to be real.

## 1. Preflight

```
uv run scripts/ticket_finish.py preflight
```

Exit 0 means the tree is clean, the branch has commits, and no forbidden file (`dashboard.svg`, `external_status.json`, `.env*` other than the public `web/.env.production`) is committed. Fix what it names (commit, or remove the file from the branch) and re-run until it is green.

## 2. Run the required suites

Run the **session level only**, once: it already contains the issue-level tests, so a separate issue-level run only repeats the same tests. Do not run the planner by hand and copy commands; let the script do it:

```
uv run scripts/ticket_finish.py suites --json <suites.json>
```

It plans the session level for the branch's diff against its merge-base with `MPSkills` (rules: `docs/test-audit/rules.md`), looks each suite up in the verification ledger by the **tree hash** of the committed code, and prints `skip` or `run` for it. A suite that already passed at this tree is skipped (an amend or a no-content merge keeps the tree); every other free suite runs, and each pass is recorded against the tree. Use the `--json` entries as the report's `suites`. Then run the typecheck/lint/build the surface's `TESTING.md` names, which the planner does not list.

After a `/code-review` fix, commit and run `suites` again: it re-runs only the suites whose files changed since their last recorded pass and carries the other passes forward. Never re-run a suite by hand to "be sure". The script does not run device tests, stale External surfaces or paid suites; it prints them as `not run here`. Paid or live suites (`action: confirm`) run only when the owner has set a budget in this session; otherwise list them under "Not done" with the cost. A failing suite is a result, not something to retry away: find out whether the change broke it.

## 3. Criterion-to-test table

`uv run scripts/ticket_finish.py criteria` lists the acceptance criteria. They are read from the ticket's latest `## Agent Brief` comment (its `**Acceptance criteria:**` list, which `/triage` makes the authoritative spec), and from the issue body (`## Acceptance criteria` or the bold label) only when no brief comment exists. For **each one**, name the test file and test that proves it, after reading that test and confirming it would fail without the change. A criterion with no automated test stays unproven; say so, and do not stretch a test to fit it.

## 4. Review

Run `/mattpocock-skills:code-review` against `MPSkills`. Fix real findings (commit, then run `ticket_finish.py suites` again; step 2). Record each finding and how it was handled in `review`, including the ones you declined and why.

## 5. Docs and follow-ups

Update what the change requires (`CONTEXT.md`, the surface's `TESTING.md`, an ADR), and commit. File a ticket (`gh issue create`) for any work found but out of scope, and list it in `followups`.

## 6. Post

If the ticket has a `## Decisions` section, check that a comment starting `DECISIONS` is on it (`gh issue view <N> --comments`). The script refuses `READY TO MERGE` without one. If the decisions were never asked, ask the owner now with `AskUserQuestion` and post the answers (layout in `docs/agents/session-handoff.md`); if you cannot ask, post `PARTIAL` and name the unanswered decisions in `not_done`.

Write the report JSON to your scratchpad (shape: `uv run scripts/ticket_finish.py --help`), then:

```
uv run scripts/ticket_finish.py post <report.json> --dry-run
uv run scripts/ticket_finish.py post <report.json>
```

Read the dry run first. If it refuses, fix the cause. When a criterion truly cannot be met, post `PARTIAL` or `BLOCKED` with the exact criterion and evidence in `not_done`; never loosen a criterion to pass. Never put a secret value in the report.

On success the script deletes the scratch file. Leave the worktree in place for `/ticket-merge`. Do not push and do not close the issue.
