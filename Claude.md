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
`NEXT_STEPS.md` is the durable, cross-machine project record — it travels
via git, unlike any machine-local memory/config. Keep it current every
session, specifically:
 - Maintain its "🧪 Tests still outstanding" section as a living checklist:
   for each test that's known to be needed but not yet written, record
   what it would cover and the specific condition that unlocks writing it
   (an install, an account, a scaffolded project, etc.).
 - The moment a listed test actually gets written, remove its entry (or
   fold it into a "✅ Done" note, matching the file's existing convention)
   — don't let entries go stale.
 - When work in a session surfaces a new test gap (a new component, a new
   integration point, a mocked API response that's never been checked
   against the real thing), add it to this section before the session
   ends — don't leave it only in conversation, since that doesn't survive
   a machine switch.