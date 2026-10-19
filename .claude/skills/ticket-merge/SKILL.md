---
name: ticket-merge
description: In the main checkout, independently verify ticket <N>, merge it --no-ff into MPSkills, close it, and remove its worktree.
disable-model-invocation: true
---

Merge ticket $ARGUMENTS (a number, with or without `#`). Run this from the **main checkout** on `MPSkills`. You are the second pair of eyes: the session that built the work already said it was ready, so trust none of that without checking. Convention: `docs/agents/session-handoff.md`.

## 1. Preflight

```
uv run scripts/ticket_merge.py preflight <N>
```

It stops unless this is the main checkout on a clean `MPSkills`, `ticket-<N>` has commits, and the ticket's newest `STATUS:` comment is `READY TO MERGE`. Report a stop and end. Merge past a `PARTIAL` or `BLOCKED` only when the owner says so in this session, then run `preflight <N> --allow-status`. Only `preflight` takes that flag; `merge` does not look at the status again.

## 2. Verify independently

Work in `.claude/worktrees/ticket-<N>` (it has the dependencies). Read the STATUS comment, then:

1. **Read the code.** `git diff MPSkills...ticket-<N>`. Judge it against the ticket's acceptance criteria yourself, not against the comment's claims.
2. **Ask the ledger which suites need a re-run**, instead of running them all again: `uv run scripts/ticket_merge.py verdicts <N>`. `/ticket-finish` ran the session-level suites on this exact commit and recorded each pass against its tree hash (`preflight` already refused a tip that differs from the commit the comment vouches for). A `skip` verdict means that suite passed at the branch tip's tree; do not run it again. A `rerun` verdict means the ledger cannot vouch for it (no recorded pass, or the ledger is unreadable): run that suite in the worktree, free suites only (paid ones need the owner's budget). `manual` lines (device, stale External, paid) are the owner's or the end-of-round bundle's. Skipping the blanket re-run does not skip the checks below: still read the diff, trace the criteria and do the mutation spot-check, which runs only the tests it names. Run extra suites only if the comment is vague about what it ran or the diff touches shared test tooling.
3. **Trace every criterion to a test** in the comment's table. Open each named test and confirm it exists and asserts the criterion.
4. **Spot-check by mutation.** Pick two or three of the most important behaviours, break each in the worktree (flip a condition, remove a guard), and confirm a named test fails. Restore every edit (`git checkout -- <file>`) and check `git status` is clean afterwards. A test that stays green under mutation does not prove its criterion.

If anything fails, do not merge. Comment on the ticket with the evidence and tell the owner.

## 3. Merge

```
uv run scripts/ticket_merge.py merge <N>
```

Before it, run `uv run scripts/ticket_merge.py baseline <N>`. On `BASELINE UNCHANGED` the merged tree equals the branch tip you just tested, so do not test it again. On `BASELINE MOVED`, merge first, then run what `uv run scripts/test_planner.py --level issue --base HEAD^1` lists on the merged tree.

A `--no-ff` merge commit on `MPSkills`. A conflict aborts cleanly and changes nothing; report it.

## 4. Close

Write the closing comment to your scratchpad: a `| Criterion | Proven by (test file and name) |` table of what you verified in step 2, plus one line on what you mutated. Then:

```
uv run scripts/ticket_merge.py close <N> --comment-file <file>
```

It comments, closes the issue, removes the worktree and deletes the branch. If the worktree will not go because of modified or untracked files, `close` lists them and removes nothing: ask the owner to commit, discard or keep them, then re-run only `git worktree remove` and `git branch -d`. If the owner's own session is still open in the worktree, Windows keeps the empty folder: `close` still prunes the worktree and deletes the branch, and prints the `rmdir` to run once that session is closed. For any other refusal, follow `docs/agents/worktree-setup.md`.

## 5. Push

Ask the owner (`AskUserQuestion`) before any push, every time. The scripts never push.
