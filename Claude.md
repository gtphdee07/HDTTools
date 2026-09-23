# Claude Instructions for this Project

This project uses `uv` for Python and dependency management. Do not use standard `pip` or global `python` commands.

## Agent skills

### Issue tracker

Issues are tracked in this repo's GitHub Issues (via the `gh` CLI); the legacy `NEXT_STEPS.md`/`ClaudePlans/`/`ARCHIVE_*.md` system is being retired in favor of it. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five canonical roles (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`), unchanged. See `docs/agents/triage-labels.md`.

### Domain docs

Multi-context: a root `CONTEXT-MAP.md` points at per-surface `CONTEXT.md` files (`android/`, `web/`, `src/hdttools/`, `streamlit_app/`, `workers/scan-proxy/`). See `docs/agents/domain.md`.

## Environment Management Commands
- Add a package: `uv add <package_name>`
- Remove a package: `uv remove <package_name>`
- Run a script safely: `uv run <script_name>.py`

## Code Style & Rules
- Always use the local project virtual environment (`.venv`).
- When writing scripts, execute them using `uv run` so dependencies are auto-resolved.

## Human-Written Content

Some files contain content the user has written by hand, marked with
`<!-- HUMAN-WRITTEN ... -->` / `<!-- END HUMAN-WRITTEN -->` HTML comments.
Never edit, remove, reformat, retranslate, or move text between these
markers, for any reason — including a file regeneration, a formatting
cleanup, or an otherwise-unrelated edit that happens to touch the same
file. Treat it as immutable, human-owned content; if a change genuinely
requires touching content around it, edit only outside the markers and
leave the marked block byte-for-byte untouched. `README.md`'s opening
block (a personal note from the project owner) is the first use of this
convention — apply the same rule to any other file that adopts the same
markers in the future, without needing a new instruction here each time.

## Verify before touching anything outside this repo, or before a multi-target delete

Before running a command that (a) deletes more than one file, or (b) writes or deletes anything at all outside this project directory, do a check-then-execute pass instead of running it straight:

- **Single literal, fully-named target, inside this project directory** — no extra step needed, run it directly.
- **Anything where a variable, glob, wildcard, `~`, or other home/environment-relative path resolves the target** — first run a non-destructive command that shows exactly what will be touched (e.g. `printf '%s\n' "$VAR"` for a variable, `printf '%s\n' pattern*` or `ls -d` for a glob, `echo ~/path` or `Resolve-Path ~/path` for a tilde). Read the output back and confirm it matches expectations — a blank result usually means a variable was unset. Only then run the real command, reusing the exact string/pattern just verified. `~` and `$HOME`/`Path.home()` count as expansion here: they resolve at runtime just like a variable, and this user has been bitten by exactly that ambiguity before (bash `$HOME` vs. Windows' real user profile).
- **Anything outside this project directory** — not exempt from the check just because it's a single named literal target. A path outside the repo has a much higher blast radius (it can hit real, non-recoverable data), so it gets the same check-then-execute treatment regardless of whether the path resolved cleanly. This applies to destructive **writes**, not just deletes.

Git operations (branch delete, worktree remove, etc.) are exempt — recoverable via reflog/remotes.

This rule needs to be restated explicitly by name when briefing a sub-agent for work likely to touch the filesystem outside its assigned worktree — inheriting it silently isn't reliable.

## Asking Questions
Any time a question is being posed to the user — clarifying an ambiguous
request, choosing between implementation approaches, or confirming
whether to take an action (including a simple "should I push this to the
remote?") — ask it through the `AskUserQuestion` tool, not as plain text
embedded in a response. A plain-text question is easy to miss, especially
at the end of a longer response; the tool's pop-up can't be missed the
same way.
 - This applies to simple yes/no confirmations too, not just multi-way
   design decisions — frame them as two options (e.g. "Yes, push" /
   "Not yet"). The tool's built-in free-text "Other" option covers
   anything that doesn't fit a predefined choice.
 - Exception: rhetorical or purely explanatory questions that aren't
   actually requesting a decision before proceeding (e.g. "wondering why
   X happened? Here's what I found...") don't need this — only questions
   where a real response is being waited on.
 - Committing is exempt from this rule: commit freely as work is
   completed, without asking first. Pushing to the remote is not exempt
   — always confirm before every push, even if an earlier push in the
   same session was already approved.

## System Tool Installs

Before installing any system-wide application or tool (e.g. via
`winget`, a standalone installer, Android Studio, a JDK, etc.):
- Ask for explicit permission first, explaining what the tool is for.
- Ask where it should be installed. The primary Windows dev machine's
  C: (boot) drive is space-constrained — prefer another drive/location
  whenever a tool has a reasonable chance of working from there, and
  confirm the exact path before installing. Don't assume a default
  location; ask fresh each time unless told otherwise.

This does **not** apply to routine project-level package-manager installs
(`uv add`, `npm install`, etc.) — those already install inside this
project's own folder, not the C: drive, so they're unaffected by the
space constraint and don't need separate permission beyond the normal
tool-use confirmation.
