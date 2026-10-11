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

It stops unless this is the main checkout on a clean `MPSkills`, `ticket-<N>` has commits, and the ticket's newest `STATUS:` comment is `READY TO MERGE`. Report a stop and end. Merge past a `PARTIAL` or `BLOCKED` only when the owner says so in this session, then pass `--allow-status`.

## 2. Verify independently

Work in `.claude/worktrees/ticket-<N>` (it has the dependencies). Read the STATUS comment, then:

1. **Read the code.** `git diff MPSkills...ticket-<N>`. Judge it against the ticket's acceptance criteria yourself, not against the comment's claims.
2. **Re-run the suites** the comment lists, plus anything the diff touches that it omits (`uv run scripts/test_planner.py --level session`). Free suites only; paid ones need the owner's budget.
3. **Trace every criterion to a test** in the comment's table. Open each named test and confirm it exists and asserts the criterion.
4. **Spot-check by mutation.** Pick two or three of the most important behaviours, break each in the worktree (flip a condition, remove a guard), and confirm a named test fails. Restore every edit (`git checkout -- <file>`) and check `git status` is clean afterwards. A test that stays green under mutation does not prove its criterion.

If anything fails, do not merge. Comment on the ticket with the evidence and tell the owner.

## 3. Merge

```
uv run scripts/ticket_merge.py merge <N>
```

A `--no-ff` merge commit on `MPSkills`. A conflict aborts cleanly and changes nothing; report it. Re-run the main suite on the merged result if the merge brought in other tickets' changes.

## 4. Close

Write the closing comment to your scratchpad: a `| Criterion | Proven by (test file and name) |` table of what you verified in step 2, plus one line on what you mutated. Then:

```
uv run scripts/ticket_merge.py close <N> --comment-file <file>
```

It comments, closes the issue, removes the worktree and deletes the branch. If the worktree will not go (Windows long paths), follow `docs/agents/worktree-setup.md`.

## 5. Push

Ask the owner (`AskUserQuestion`) before any push, every time. The scripts never push.
