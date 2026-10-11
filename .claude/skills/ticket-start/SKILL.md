---
name: ticket-start
description: Pre-check, claim and build a worktree for ticket <N>, then print the /implement command.
disable-model-invocation: true
---

Start ticket $ARGUMENTS (a number, with or without `#`). Run this from the **main checkout**. The script does every deterministic step; your job is the judgement around it. Convention: `docs/agents/session-handoff.md`; overview: `docs/agents/ticket-skills.md`.

## 1. Run the script

```
uv run scripts/ticket_start.py <N>
```

It reads the ticket and stops, having changed nothing, when the ticket is closed, has an open blocker (native dependency or `## Blocked by`), has an assignee, already has a `ticket-<N>` branch or worktree, or (Android) another assigned open Android ticket holds the single emulator. Otherwise it assigns the ticket to the owner, cuts `.claude/worktrees/ticket-<N>` from `MPSkills`, runs `scripts/worktree_setup.py` inside it, and writes the directions to `%TEMP%\hdttools-status\ticket-<N>.md`.

It guesses Android from the title or an `android/` path in the body. If it guessed wrong, re-run with `--android` or `--not-android`.

## 2. If it stopped

Report each reason to the owner in a sentence and end. Blockers, assignees and a busy emulator are the owner's calls; the owner re-runs the skill once they are cleared.

## 3. If it succeeded

Check the result with `git worktree list` (the new path is on `ticket-<N>`) and `git -C <worktree> merge-base --is-ancestor MPSkills HEAD`. Both must hold; if either fails, say so plainly.

Then get the session into the worktree: call `EnterWorktree` with the worktree path. If that is unavailable, tell the owner to run `cd <path>` and start `claude` there (or `claude --worktree`).

Finish by printing, as the last thing the owner sees, the script's next command on its own line:

```
/mattpocock-skills:implement #<N>
```

`/implement` is user-invocation only, so you do not run it. The owner types it, and the directions file tells that session to follow the handoff convention (no push, ticket stays open, `/ticket-finish` last).
