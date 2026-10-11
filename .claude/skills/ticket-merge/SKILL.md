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
2. **Re-run the targeted tests**, not the whole application run: the tests the comment's table names, plus what the planner lists for the diff (`uv run scripts/test_planner.py --base MPSkills --level issue`, run in the worktree). The session already ran the full suite; this re-run checks its claims on the tests that matter. Run the full suite only if the comment is vague about what it ran, a run it reports looks wrong, or the diff touches shared test tooling. Free suites only; paid ones need the owner's budget.
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

It comments, closes the issue, removes the worktree and deletes the branch. If the worktree will not go because of modified or untracked files, `close` lists them and removes nothing: ask the owner to commit, discard or keep them, then re-run only `git worktree remove` and `git branch -d`. For any other refusal, follow `docs/agents/worktree-setup.md`.

## 5. Push

Ask the owner (`AskUserQuestion`) before any push, every time. The scripts never push.
