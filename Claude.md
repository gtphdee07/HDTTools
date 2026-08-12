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