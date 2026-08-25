# Claude Instructions for this Project

This project uses `uv` for Python and dependency management. Do not use standard `pip` or global `python` commands.

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

## Coding Preferences
 - The preference is for application code to be constructed using Python libraries, versus Claude skills. It is fine to use skills in Chat to create proofs of concepts, or to create test benches against the Python code, but the application should not require an ANTHROPIC_API_KEY to execute.
  - All coding modules should also have an automated test for each function.
    See `TESTING.md` for the full methodology this implies: function/
    interaction/module/interface test categories, and the Minor/Major
    regression-scoping rules for deciding which suites a change needs to
    run.
  - **Test-Driven Development is required for all new code and bug
    fixes**: write a failing test before the implementation (or the fix),
    watch it fail for real, then write the minimum code to pass it. See
    `TDD_METHODOLOGY.md` for the full workflow, with real per-product-line
    commands/conventions (Python, Web, Android, `scan-proxy`) — `TESTING.md`
    still governs how the resulting tests get categorized (Minor/Major/
    External) and run, a related but separate concern.

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

## Planning Procedure
Whenever the user asks for a plan — directly, or via language like
"what's the plan for X, including goals, steps, how results will be
measured, and the definition of done" — every plan (built via Claude
Code's Plan Mode) follows this shape:
- **Context**: why this work is happening, what prompted it.
- **Goal**: what "success" is aiming at, in one or two sentences.
- **Steps**: the concrete sequence of changes/actions.
- **Definition of Done**: the specific, checkable conditions that mean
  this is actually finished — not just "code written," but verified.
- **Verification**: exactly how to confirm each part works for real.

Once the user approves a plan (`ExitPlanMode` returns approved), before
any other implementation action: save the full approved plan content to
`ClaudePlans/YYYY-MM-DD-<short-title>.md` in the project root (create
the directory if it doesn't exist). Derive `<short-title>` from the
plan's own heading — short, hyphen-separated, no spaces or punctuation
that needs escaping on any filesystem. This is a deliberate, standing
step of the planning procedure itself — do it every time a plan is
approved, not only when separately asked to save one.

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
  `ARCHIVE_WEB_STREAMLIT.md`, `ARCHIVE_EARLY_HISTORY.md`,
  `ARCHIVE_DEAD_CODE.md`, `ARCHIVE_BREAKDOWN_SWEEP.md`.
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