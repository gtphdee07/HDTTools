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

Run `uv run scripts/test_planner.py --base MPSkills --level issue`, then `--level session`; they name what the branch's commits require (rules: `docs/test-audit/rules.md`). `--base MPSkills` matters: the default base, HEAD, sees nothing once work is committed. Run every **free** suite they list, plus the typecheck/lint/build the surface's `TESTING.md` names. Record each command, pass or fail, and the counts.

Paid or live suites (`action: confirm` in the plan) run only when the owner has set a budget in this session; otherwise list them under "Not done" with the cost. A failing suite is a result, not something to retry away: find out whether the change broke it.

## 3. Criterion-to-test table

`uv run scripts/ticket_finish.py criteria` lists the acceptance criteria. They are read from the ticket's latest `## Agent Brief` comment (its `**Acceptance criteria:**` list, which `/triage` makes the authoritative spec), and from the issue body (`## Acceptance criteria` or the bold label) only when no brief comment exists. For **each one**, name the test file and test that proves it, after reading that test and confirming it would fail without the change. A criterion with no automated test stays unproven; say so, and do not stretch a test to fit it.

## 4. Review

Run `/mattpocock-skills:code-review` against `MPSkills`. Fix real findings (commit, then re-run the affected suites). Record each finding and how it was handled in `review`, including the ones you declined and why.

## 5. Docs and follow-ups

Update what the change requires (`CONTEXT.md`, the surface's `TESTING.md`, an ADR), and commit. File a ticket (`gh issue create`) for any work found but out of scope, and list it in `followups`.

## 6. Post

Write the report JSON to your scratchpad (shape: `uv run scripts/ticket_finish.py --help`), then:

```
uv run scripts/ticket_finish.py post <report.json> --dry-run
uv run scripts/ticket_finish.py post <report.json>
```

Read the dry run first. If it refuses, fix the cause. When a criterion truly cannot be met, post `PARTIAL` or `BLOCKED` with the exact criterion and evidence in `not_done`; never loosen a criterion to pass. Never put a secret value in the report.

On success the script deletes the scratch file. Leave the worktree in place for `/ticket-merge`. Do not push and do not close the issue.
