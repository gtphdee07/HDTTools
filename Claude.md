# Claude Instructions for this Project

This project uses `uv` for Python and dependency management. Do not use standard `pip` or global `python` commands.

## Environment Management Commands
- Add a package: `uv add <package_name>`
- Remove a package: `uv remove <package_name>`
- Run a script safely: `uv run <script_name>.py`

## Code Style & Rules
- Always use the local project virtual environment (`.venv`).
- When writing scripts, execute them using `uv run` so dependencies are auto-resolved.

## Coding Preferences
 - The preference is for application code to be constructed using Python libraries, versus Claude skills. It is fine to use skills in Chat to create proofs of concepts, or to create test benches against the Python code, but the application should not require an ANTHROPIC_API_KEY to execute.
  - All coding modules should also have an automated test for each function.
    See `TESTING.md` for the full methodology this implies: function/
    interaction/module/interface test categories, and the Minor/Major
    regression-scoping rules for deciding which suites a change needs to
    run.

## Asking Questions
Any time a question is being posed to the user — clarifying an ambiguous
request, choosing between implementation approaches, or confirming
whether to take an action (including a simple "should I commit and push
this?") — ask it through the `AskUserQuestion` tool, not as plain text
embedded in a response. A plain-text question is easy to miss, especially
at the end of a longer response; the tool's pop-up can't be missed the
same way.
 - This applies to simple yes/no confirmations too, not just multi-way
   design decisions — frame them as two options (e.g. "Yes, commit and
   push" / "Not yet"). The tool's built-in free-text "Other" option
   covers anything that doesn't fit a predefined choice.
 - Exception: rhetorical or purely explanatory questions that aren't
   actually requesting a decision before proceeding (e.g. "wondering why
   X happened? Here's what I found...") don't need this — only questions
   where a real response is being waited on.

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

## NEXT_STEPS.md Maintenance
`NEXT_STEPS.md` is the durable, cross-machine project record — it
travels via git, unlike any machine-local memory/config. It is a
**status/roadmap file, not a history log** — it answers "what's next,"
not "how did we get here." Keep it current every session:

### Core file discipline
- The roadmap section holds active/open items (⬜/🔶) at real length,
  but a completed item (✅) collapses to a single terse line (a couple
  of lines only if there's a real ongoing implication, e.g. an accepted
  tradeoff worth restating) pointing at the matching `ARCHIVE_*.md` for
  detail. Move the full narrative to the archive the same session the
  item completes — don't leave a multi-paragraph writeup sitting under
  a ✅ marker "for now."
- Maintain the "🧪 Tests still outstanding" section as a living
  checklist: for each known-but-unwritten test, record what it would
  cover and the specific condition that unlocks writing it (an install,
  an account, a scaffolded project, etc.). Remove an entry the moment
  its test actually gets written — don't let it go stale.
- When a session surfaces a new test gap (a new component, a new
  integration point, a mocked response never checked against the real
  thing), add it here before the session ends — don't leave it only in
  conversation, since that doesn't survive a machine switch.
- If the file is approaching ~300 lines, sweep it: confirm every ✅ item
  is actually collapsed, and consider whether a topic needs its own new
  archive split (as happened 2026-08-23).

### Archive discipline (`ARCHIVE_*.md`)
- Full narrative — bug writeups, gotchas, design decisions, real
  verification detail — lives in the topic archive that matches the
  work, never inline in `NEXT_STEPS.md`. Current archives:
  `ARCHIVE_ANDROID.md`, `ARCHIVE_TESTING.md`, `ARCHIVE_MONETIZATION.md`,
  `ARCHIVE_WEB_STREAMLIT.md`, `ARCHIVE_EARLY_HISTORY.md`.
- Target detail level: a real account of what was tried, what broke,
  and why the fix works — not a full transcript, but enough to
  reconstruct the reasoning later without re-deriving it. This is
  deliberately more detail than a one-line summary; it's affordable
  specifically because it's out of the core file.
- Every entry leads with a bold tag (`✅ **Real bug`, `**Decided`,
  `**Design correction`, `**Important gotcha`, or similar) so `Grep`
  can filter by type without reading the whole file. Keep using this
  convention for every new entry.
- If one archive file crosses roughly 800-1000 lines, that's a signal
  to split it into a new topic file, not to compress its entries.

### Pruning
- When something documented earlier (a gotcha, a workaround, an open
  question) gets fully superseded — automated away, permanently fixed,
  answered for good — don't delete the original writeup. Add a short,
  clearly-tagged note next to it (e.g. "✅ Automated, <date>: ...")
  pointing at what superseded it. History stays traceable; nothing is
  silently lost.
- Only actually delete detail that's now flat-out wrong or actively
  misleading if left standing without context — not detail that's
  merely outdated.

### Session-end habit
- Before ending a session that did real work (not just discussion),
  check: does `NEXT_STEPS.md` reflect what actually happened? Did
  anything surface that isn't captured anywhere durable yet? Update
  `NEXT_STEPS.md` and the relevant archive proactively — don't wait to
  be asked, and don't wait for a context-compaction prompt to be the
  trigger.