# Ticket skills

Three skills wrap a ticket's `/mattpocock-skills:implement` run, so setting up a worktree, finishing and merging are each one command. `/implement` is user-invocation only (the harness blocks a skill or sub-agent from calling it), so the skills go before it, after it, and at the merge. They follow `docs/agents/session-handoff.md` and build on `docs/agents/worktree-setup.md`.

| Skill | Run where | Does | Script |
|---|---|---|---|
| `/ticket-start <N>` | main checkout | Checks the ticket (closed, open blocker, assignee, existing branch or worktree, Android emulator in use), assigns it to the owner, cuts `.claude/worktrees/ticket-<N>` from `MPSkills`, runs `scripts/worktree_setup.py`, writes the directions, prints the `/implement` line | `scripts/ticket_start.py` |
| `/ticket-finish` | the ticket's worktree, after `/implement` | Confirms the tree is clean and committed, runs the required free suites, maps each acceptance criterion to a test, runs `/code-review`, files follow-ups, posts the `STATUS:` comment, deletes the scratch file | `scripts/ticket_finish.py` |
| `/ticket-merge <N>` | main checkout | Re-verifies independently (diff, suites, criterion-to-test, mutation spot-check), merges `--no-ff` into `MPSkills`, closes the issue with a criterion-to-test comment, removes the worktree and branch. Never pushes | `scripts/ticket_merge.py` |

A typical ticket: `/ticket-start 42`, start `claude` in the new worktree and type the printed `/mattpocock-skills:implement #42`, then `/ticket-finish`, then back in the main checkout `/ticket-merge 42`. Each skill is `disable-model-invocation: true`: only you can start one.

## Where the skills live, and how to install them

They are committed at `.claude/skills/ticket-start/`, `ticket-finish/` and `ticket-merge/` (each a `SKILL.md`). Claude Code loads `.claude/skills/` in a project automatically, so a checkout or a new worktree has them with nothing to install. The rest of `.claude/skills/` is gitignored (locally-fetched payloads, pinned by `skills-lock.json`); `.gitignore` un-ignores only `ticket-*`. A new skill that should be committed needs its own exception there.

A worktree carries the skills as of the commit it was cut from, so a skill edited on `MPSkills` reaches a worktree only after that worktree merges it. To use them from another repository, copy the three directories to `~/.claude/skills/` (they assume this repo's scripts, so that is not recommended).

## What the scripts decide

The skills hold the judgement steps; the scripts hold the rules, and their logic is tested (`tests/test_ticket_start.py`, `test_ticket_finish.py`, `test_ticket_merge.py`, `test_ticket_skills.py`).

- **Start** stops, changing nothing, on any reason above. A ticket counts as Android when its title says so or its body names a path under `android/`; override with `--android` or `--not-android`. The emulator is busy when another open, assigned Android ticket exists. Blockers come from GitHub's native dependencies and the body's `## Blocked by` list; an unreadable blocker counts as open.
- **Start's setup check** is `scripts/worktree_setup.py` itself: it installs from the lockfiles, then reports which local-only files are missing (#83 built no separate doctor command).
- **Finish** refuses `STATUS: READY TO MERGE` when the tree is dirty, any suite in the report failed, no suite was recorded, an acceptance criterion has no named test, the branch has no commits ahead of `MPSkills`, or a commit carries `dashboard.svg`, `external_status.json` or an `.env*` file. A suite's `passed` must be a real true/false. `PARTIAL` and `BLOCKED` are always postable but must say what is not done. The git facts (branch, sha, worktree, pushed) are computed by the script, not taken from the report.
- **Merge** needs the main checkout on a clean `MPSkills`, a newest `STATUS:` comment of `READY TO MERGE` (`--allow-status` if the owner decides otherwise), and a `ticket-<N>` tip that still matches the sha that comment vouches for (later commits mean re-running `/ticket-finish`). A conflict aborts and changes nothing. `close` refuses an unmerged branch or a comment with no criterion table, and a worktree that will not remove (Windows long paths) is reported with the issue already closed.

The pre-commit hook (`.githooks/pre-commit`) skips regenerating `dashboard.svg` on `ticket-*` branches, so a ticket's commits do not carry it. The hook path is shared by every worktree, so the skip applies once it is merged into `MPSkills`; until then, commit with `--no-verify` or drop the file from the commit.

Free suites only: `/ticket-finish` and `/ticket-merge` run a paid or live suite only when the owner has set a budget for it in that session.
