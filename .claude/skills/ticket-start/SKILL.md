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

It reads the ticket and stops, having changed nothing, when the ticket is closed, has an open blocker (native dependency or `## Blocked by`), has an assignee, already has a `ticket-<N>` branch or worktree, or (Android) another assigned open Android ticket holds the single emulator. Otherwise it assigns the ticket to the owner, cuts `.claude/worktrees/ticket-<N>` from `MPSkills`, runs `scripts/worktree_setup.py --copy-env` inside it (so the gitignored `web/.env.local` comes along), and writes the directions to `%TEMP%\hdttools-status\ticket-<N>.md`.

It guesses Android from the title or an `android/` path in the body. If it guessed wrong, re-run with `--android` or `--not-android`. If an assigned ticket is wrongly counted as holding the emulator (its title says Android but it never uses the emulator, like #43's release gate), name it with `--emulator-free <M>`.

## 2. If it stopped

Report each reason to the owner in a sentence and end. Blockers, assignees and a busy emulator are the owner's calls; the owner re-runs the skill once they are cleared.

## 3. If it succeeded

Check the result with `git worktree list` (the new path is on `ticket-<N>`) and `git -C <worktree> merge-base --is-ancestor MPSkills HEAD`. Both must hold; if either fails, say so plainly.

Then get the session into the worktree: call `EnterWorktree` with the worktree path. If that is unavailable, tell the owner to run `cd <path>` and start `claude` there (or `claude --worktree`).

Finish by printing, as the last thing the owner sees, the prompt the script printed, exactly as it printed it (the command, a blank line, then the handoff line):

```
/mattpocock-skills:implement #<N>

Follow docs/agents/session-handoff.md: don't push, don't close the issue, and finish with a STATUS comment on the ticket. While you work, run single test files and typechecks only; leave the full run to /ticket-finish, which runs it once and remembers the pass. Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion (up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions.
```

`/implement` is user-invocation only, so you do not run it. The owner pastes the whole prompt as the first message of the new session; the handoff line is what makes that session follow the handoff convention (no push, ticket stays open, `/ticket-finish` last).
