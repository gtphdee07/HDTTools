# Destructive-command guard

A `PreToolUse` hook (#207) that makes the "verify before touching anything outside this repo, or before a multi-target delete" rule in `CLAUDE.md` something the harness enforces. It reads every Bash and PowerShell command before it runs; when a delete, move or overwrite names a target it cannot vouch for, it forces the permission prompt and says why. Script: `scripts/destructive_command_guard.py`. Tests: `tests/test_destructive_command_guard.py`. Registered for `Bash|PowerShell` in `.claude/settings.json`, next to the device-command guard (`scripts/long_command_guard.py`, #200).

## What it holds

For each simple command on the line (split at `;` `|` `&` `&&` `||`, newlines, and in PowerShell `{` `}`), it looks at what the command deletes (`rm`, `rmdir`, `del`, `rd`, `Remove-Item`, `find -delete`), moves or copies (`mv`, `cp`, `Move-Item`, `Copy-Item`), or overwrites (a `>` or `>>` redirect, `tee`, `dd of=`, `Set-Content`, `Out-File`, `sed -i`), and holds the command when a target:

| Target | Why it is held |
|---|---|
| holds a variable, `$(...)`, backticks, `%VAR%` | what it names is not known until it runs |
| holds a wildcard: `*` `?` `[`, or a `{a,b}` brace (any `*?[` in PowerShell, which globs even inside quotes) | it can match more than intended |
| starts with `~` | your home folder (PowerShell resolves it even inside quotes) |
| is a literal path outside the project folder: a `..` that climbs out, another drive, the user profile, `/`, an MSYS `/c/...` path | outside the project |
| is the project folder itself, for a delete or an overwrite | one stroke from losing everything |
| is relative, after a `cd` the guard cannot read (`cd "$X" && rm foo`) | the folder is unknown |
| comes from another command: `xargs rm`, a bare `Remove-Item` at the end of a pipeline | the targets are not on the line |
| is `Invoke-Expression`, `iex`, `-EncodedCommand`, or a .NET `::Delete(`/`::Move(`/`::WriteAll*(` call | the text cannot be read in advance |

Wrappers are read through: `sudo`, `env`, `nohup`, `xargs`, `bash -c`, `cmd /c`, `powershell -Command`. A `cd`, `pushd` or `Set-Location` earlier on the line moves the folder relative targets are read against.

## What passes untouched (nothing printed)

A single literal path inside the project in any spelling (`rm tmp/x`, `rm -rf build`, `rm /g/Proj/build`, `Remove-Item .\build`), git commands (branch delete, worktree remove, clean: exempt, as in `CLAUDE.md`), quoted text that only contains `rm -rf` (a commit message, `echo`), a single-quoted `'$HOME'` (a file literally named that), redirects to `/dev/null`, `$null`, `nul` and descriptors (`2>&1`), reading, `find` and `sed` that change nothing, PowerShell's `Env:`/`Variable:`/`Function:`/`Alias:` drives (in memory, not files), and the harness scratch folders under the temp folder (`claude` and `hdttools-status`), literal paths only: a glob or a `..` out of them is still held.

## What it answers

- **`ask`** in the main session: the prompt shows the command, the target, the reason and the check to run first (print what the target resolves to, read it back, rerun with that exact string). Approve a legitimate cleanup there. The command is never rewritten.
- **`deny`** when the call comes from a sub-agent (the hook input carries `agent_id`). Claude Code documents that a hook fires for a sub-agent's tool calls too (it checked 2026-11-04 at <https://code.claude.com/docs/en/hooks>), but whether a prompt reaches anyone from a background sub-agent is not documented, and its handback calls never show one, so a held call there is refused with the same reason and the sub-agent has to rewrite it with a literal path or ask the owner. Behaviour in practice: see "Observed" below.
- **Nothing** for everything else, so an ordinary command costs only the hook's start-up (`uv run`, about the same as the device-command guard).

## When the guard itself breaks

It fails **closed** (owner decision, #207): an exception inside the guard, or input it cannot read, is logged to `%TEMP%\hdttools-status\destructive_command_guard.log` and the command is held for a prompt (`deny` from a sub-agent) with a reason that starts `destructive_command_guard: guard error`. Claude Code treats a hook that crashes outright, exits with a code other than 2, cannot start (uv missing) or times out as non-blocking, so those cases let the command run. `"onFailure": "block"` on the handler would close that gap, but it denies instead of asking, so a broken `uv` would lock every Bash and PowerShell call out of a session; it is deliberately not set. A syntax error cannot reach a session: a test compiles the script.

## What it does not see

- Code run by an interpreter: `python -c "shutil.rmtree(x)"`, `node -e`, `uv run some_script.py`. A script that deletes is reviewed as code, not as a command line.
- A command built at run time (`$cmd args`), and what a variable will expand to (that is the point: it holds the command so you look).
- A here-document's body, and a symbolic link or junction inside the project that points outside it.
- The Edit and Write tools, and MCP tools.

## Observed and not observed

- **Tested by the suite:** the answer for each command shape, the sub-agent refusal (driven by `agent_id` in the hook input), a crash held for a prompt, and the script run as a real process with a hook payload on stdin.
- **Documented by Claude Code, not observed live (2026-11-04):** the hook fires for a sub-agent's Bash and PowerShell calls, with `agent_id` and `agent_type` in its input; a hook `ask` in auto mode normally reaches the permission prompt, unless Claude Code's own checks also flag the call. The build session could not watch this: a hook added to `.claude/settings.json` is not active in a session that was already running, and a headless run was not approved. So whether a prompt can be answered from a background sub-agent is unconfirmed, and that is why the guard refuses there instead of asking. If the sub-agent call is found not to reach the hook at all, restate the "verify before touching" rule in sub-agent briefs, as `CLAUDE.md` already requires.
- **To observe it once** (a fresh Claude Code session started in the project, so the hook loads): (1) ask the session to run `rm -f "$UNSET_VAR_207.tmp"` (it only names a file that does not exist) and confirm a permission prompt appears with a reason starting `destructive_command_guard:`; (2) ask it to run a sub-agent that runs the same command and see whether the sub-agent's call is refused with the sub-agent sentence; (3) run `rm -f no-such-file.tmp` and confirm there is no prompt. Record the result on #207 and replace this paragraph with it.

## Changing it

Add a program to `DESTRUCTIVE` (and, if it is a PowerShell alias that clashes with a Windows program, to `POWERSHELL_ONLY`); add a row to the held or the pass table in the test file first. A new wrapper goes in `_wrapped`. Keep the answer an `ask`; never rewrite the command.
