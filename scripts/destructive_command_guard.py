"""PreToolUse hook that holds a delete, move or overwrite whose target is not a plain path inside the project (#207).

  uv run --no-project scripts/destructive_command_guard.py --hook     # reads the hook's JSON on stdin

`.claude/settings.json` registers it for the Bash and PowerShell tools. It makes the written rule in CLAUDE.md
("Verify before touching anything outside this repo, or before a multi-target delete") something the harness
enforces, not something the agent has to remember. For each simple command on the line it looks at what the
command deletes (rm, rmdir, del, rd, Remove-Item, find -delete ...), moves or copies (mv, cp, Move-Item,
Copy-Item ...) or overwrites (a > or >> redirect, tee, dd of=, Set-Content, Out-File, sed -i ...), and answers
`ask` (the permission prompt, with the reason) when a target

  - holds a variable, a command substitution or a %VAR% (what it names is not known until it runs),
  - holds a wildcard (a glob, a {a,b} brace, or any * ? [ in PowerShell, which globs even inside quotes),
  - starts with ~ (the home folder), or
  - is a literal path that resolves outside the project folder (a .. that climbs out, another drive, the
    user profile, / or the project folder itself). The harness scratch folders under the temp folder
    (`claude` and `hdttools-status`) count as inside.

Anything else is left alone (nothing is printed): a single literal path inside the project, git commands, a
quoted word that merely contains `rm -rf` (a commit message), a redirect to /dev/null or $null, and
reading. The line is split at ; | & && || newlines and (in PowerShell) { }, wrapper commands are read through
(sudo, env, xargs, bash -c, cmd /c, powershell -Command), and a `cd` earlier on the line moves the folder
that relative targets are read against. A command that comes from a sub-agent is refused (`deny`) instead of
asked, because a prompt may not reach anyone there.

What it does not see: code run by an interpreter (python -c, node -e, a script), a command built at run time
(`$cmd args`; Invoke-Expression and -EncodedCommand are held), what a variable will expand to, a here-document's
body, and a symbolic link or junction inside the project that points outside it.

It fails closed: when the guard itself breaks (a bug, unreadable input) it logs the error to
`%TEMP%\\hdttools-status\\destructive_command_guard.log` and holds the command for a prompt. A hook that cannot
start at all (uv missing) or times out lets the command run; Claude Code's `onFailure: "block"` would deny it
instead of asking, and so would lock a session out when uv breaks, so it is deliberately not set.
"""

from __future__ import annotations

import json
import ntpath
import os
import re
import sys
import tempfile
import traceback
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Callable

TOOLS = ("Bash", "PowerShell")
MAX_LISTED = 3  # commands named in a reason before "and N more"
MAX_UNWRAP = 3  # nested `bash -c` / `cmd /c` / `powershell -Command` levels that are read


def _temp_dir() -> Path:
    base = Path(tempfile.gettempdir())
    try:
        return base.resolve()  # the long form of a short 8.3 name such as ANGELA~1
    except OSError:
        return base


LOG_PATH = _temp_dir() / "hdttools-status" / "destructive_command_guard.log"
SAFE_DIRS = (str(_temp_dir() / "claude"), str(_temp_dir() / "hdttools-status"))  # the harness scratchpad and the handoff notes

DESTRUCTIVE = frozenset({
    "rm", "rmdir", "unlink", "shred", "mv", "cp", "truncate", "tee", "dd", "install", "rsync",
    "del", "erase", "rd", "move", "copy", "ren", "rename", "xcopy", "robocopy",
    "remove-item", "ri", "move-item", "mi", "copy-item", "cpi", "rename-item", "rni",
    "set-content", "sc", "add-content", "ac", "clear-content", "clc", "out-file", "new-item", "ni", "tee-object",
})
ROOT_OK = frozenset({  # the project folder itself is a normal start or destination for these (never for a delete or an overwrite)
    "find", "mv", "cp", "move", "copy", "move-item", "mi", "copy-item", "cpi", "xcopy", "robocopy", "rsync", "install",
})
POWERSHELL_ONLY = frozenset({"ri", "mi", "cpi", "rni", "sc", "ac", "clc", "ni"})  # `sc` is also sc.exe, so only PowerShell reads it as a write
WINDOWS_ONLY = frozenset({"del", "erase", "rd", "move", "ren", "rename", "xcopy", "robocopy", "copy"})  # /s /q are switches, not paths
WRITE_ONE_PATH = frozenset({"set-content", "sc", "add-content", "ac", "clear-content", "clc", "out-file"})  # later words are data
CD_PROGRAMS = frozenset({"cd", "chdir", "pushd", "set-location", "sl", "push-location"})
POP_PROGRAMS = frozenset({"popd", "pop-location"})
OPAQUE_PROGRAMS = frozenset({"invoke-expression", "iex"})
SHELLS = frozenset({"bash", "sh", "zsh", "dash", "ksh"})
PREFIX_WORDS = frozenset({
    "do", "then", "else", "elif", "if", "while", "until", "!", "time", "sudo", "command", "builtin", "exec", "nohup",
    "nice", "env", "timeout", "stdbuf", "{", "}",
})
XARGS_VALUE_OPTIONS = frozenset({"-I", "-n", "-P", "-L", "-s", "-d", "-E", "-a"})
POWERSHELL_SKIP_VALUE = frozenset({
    "-value", "-encoding", "-erroraction", "-ea", "-warningaction", "-wa", "-errorvariable", "-ev", "-outvariable", "-ov",
    "-include", "-exclude", "-filter", "-itemtype", "-type", "-width", "-stream", "-credential", "-depth", "-delimiter",
    "-inputobject", "-pipelinevariable", "-pv",
})
POWERSHELL_PATH_PARAMS = frozenset({"-path", "-literalpath", "-lp", "-filepath", "-destination", "-name", "-pspath"})
SINKS = frozenset({"/dev/null", "$null", "nul", "/dev/stdout", "/dev/stderr", "/dev/tty", "con"})
PROVIDER_DRIVE = re.compile(r"^(env|variable|function|alias):", re.IGNORECASE)  # in-memory PowerShell drives, not files
PERCENT_VAR = re.compile(r"%[A-Za-z_]\w*%")
ENV_ASSIGN = re.compile(r"^[A-Za-z_]\w*=")
MSYS_DRIVE = re.compile(r"^/([A-Za-z])(?=/|$)")
DOTNET_FILE_CALL = re.compile(r"::\s*(Delete|Move|Copy|Replace|WriteAll\w*|AppendAll\w*)\s*\(", re.IGNORECASE)
CMD_SWITCH = re.compile(r"^/[A-Za-z?]+(:\S*)?$")
SED_IN_PLACE = re.compile(r"^(--in-place(=.*)?|-[A-Za-z]*i(\.\S*)?)$")

WHY_VARIABLE = "names a variable or substitution, so what it touches is not known until it runs"
WHY_GLOB = "contains a wildcard, so it can match more than intended"
WHY_TILDE = "starts with ~, your home folder"
WHY_OUTSIDE = "is outside the project folder"
WHY_CWD = "is relative to a folder that an earlier cd moved to, which the guard cannot read"
WHY_STDIN = "takes its targets from another command"
WHY_OPAQUE = "runs text that cannot be read before it runs"
WHY_DOTNET = "calls a .NET file method"


# --- reading a command line -----------------------------------------------------------------------------


@dataclass
class Token:
    kind: str  # word | redir_out | redir_in
    value: str
    dynamic: bool = False  # holds a variable, substitution or %VAR% that the shell expands
    glob: bool = False
    tilde: bool = False
    dup: bool = False  # a redirect to a descriptor (2>&1), not to a file


@dataclass
class Segment:
    tokens: list[Token] = field(default_factory=list)
    piped: bool = False  # follows a `|`


class _Scanner:
    def __init__(self, text: str, dialect: str):
        self.text, self.dialect = text, dialect  # dialect: bash | powershell | cmd
        self.segments: list[Segment] = []
        self.tokens: list[Token] = []
        self.piped = False
        self.redirect: tuple[str, bool] | None = None
        self._reset_word()

    def _reset_word(self):
        self.val: list[str] = []
        self.started = False
        self.dynamic = self.glob = self.tilde = self.brace = False

    def add_literal(self, ch: str):
        self.val.append(ch)
        self.started = True

    def add_unquoted(self, ch: str):
        d = self.dialect
        if ch == "$" and d != "cmd":
            self.dynamic = True
        elif ch in "*?" or (ch == "[" and d == "bash"):
            self.glob = True
        elif ch == "{" and d == "bash":
            self.brace = True
        elif ch == "~" and not self.val and d == "bash":
            self.tilde = True
        self.add_literal(ch)

    def end_word(self):
        if not self.started:
            return
        value = "".join(self.val)
        powershell = self.dialect == "powershell"  # PowerShell globs and expands ~ even in quotes
        glob = self.glob or (self.brace and ("," in value or ".." in value)) or (powershell and any(c in value for c in "*?["))
        tilde = self.tilde or (powershell and value.startswith("~"))
        token = Token("word", value, self.dynamic or bool(PERCENT_VAR.search(value)), glob, tilde)
        if self.redirect:
            direction, ampersand = self.redirect
            token.kind = "redir_out" if direction == "out" else "redir_in"
            token.dup = ampersand and bool(re.fullmatch(r"\d+|-", value))
            self.redirect = None
        self.tokens.append(token)
        self._reset_word()

    def end_segment(self, next_piped: bool):
        self.end_word()
        if self.tokens:
            self.segments.append(Segment(self.tokens, self.piped))
        self.tokens = []
        self.redirect = None
        self.piped = next_piped

    def separator_at(self, i: int) -> tuple[int, bool] | None:
        """(width, is a pipe) when an unquoted separator starts at i."""
        t, d, ch = self.text, self.dialect, self.text[i]
        if t[i : i + 2] in ("&&", "||"):
            return 2, False
        if ch == ";" and d != "cmd":
            return 1, False
        if ch == "|":
            return 1, True
        if ch == "&" and d != "powershell":
            if t[i + 1 : i + 2] == ">" or (i > 0 and t[i - 1] in "<>"):
                return None  # &> and >& are redirects
            return 1, False
        if d == "bash" and ch in "()`":
            return 1, False
        if d == "powershell" and ch in "{}":
            return 1, False
        return None

    def run(self) -> list[Segment]:
        t, n, d = self.text, len(self.text), self.dialect
        i, quote = 0, ""
        while i < n:
            ch = t[i]
            if quote == "'":
                if ch == "'":
                    if d == "powershell" and t[i + 1 : i + 2] == "'":
                        self.add_literal("'")
                        i += 2
                        continue
                    quote = ""
                else:
                    self.add_literal(ch)
                i += 1
                continue
            if quote == '"':
                nxt = t[i + 1 : i + 2]
                if ch == '"':
                    if d == "powershell" and nxt == '"':
                        self.add_literal('"')
                        i += 2
                        continue
                    quote = ""
                elif d == "bash" and ch == "\\" and nxt in ('"', "\\", "$", "`"):
                    self.add_literal(nxt)
                    i += 2
                    continue
                elif d == "bash" and ch == "\\" and nxt == "\n":
                    i += 2
                    continue
                elif d == "powershell" and ch == "`" and nxt:
                    self.add_literal(nxt)
                    i += 2
                    continue
                else:
                    if (ch == "$" and d != "cmd") or (d == "bash" and ch == "`"):
                        self.dynamic = True
                    self.add_literal(ch)
                i += 1
                continue
            # outside quotes
            if ch in " \t\r":
                self.end_word()
                i += 1
            elif ch == "\n":
                self.end_segment(False)
                i += 1
            elif ch == "#" and not self.started and d != "cmd":
                while i < n and t[i] != "\n":
                    i += 1
            elif d == "bash" and ch == "\\":
                nxt = t[i + 1 : i + 2]
                if nxt == "\n":
                    i += 2
                elif nxt:
                    self.add_literal(nxt)
                    i += 2
                else:
                    i += 1
            elif d == "powershell" and ch == "`":
                nxt = t[i + 1 : i + 2]
                if nxt == "\n":
                    i += 2
                elif nxt:
                    self.add_literal(nxt)
                    i += 2
                else:
                    i += 1
            elif ch == '"' or (ch == "'" and d != "cmd"):
                quote = ch
                self.started = True
                i += 1
            elif d == "powershell" and ch == "{" and t[i - 1 : i] in ("$", "@") and i > 0:
                depth, j = 0, i
                while j < n:
                    depth += (t[j] == "{") - (t[j] == "}")
                    if depth == 0:
                        break
                    j += 1
                for c in t[i : j + 1]:
                    self.add_literal(c)
                i = j + 1
            elif ch == "&" and d == "bash" and t[i + 1 : i + 2] == ">":
                i += 1  # the & of &>file; the > that follows is read as the redirect
            elif ch in "<>":
                cur = "".join(self.val)
                if self.started and (cur.isdigit() or (d == "powershell" and cur in ("*", "&"))):
                    self._reset_word()  # the file descriptor in 2>file, or the stream selector in *>file
                else:
                    self.end_word()
                j = i
                while j < n and t[j] in "<>":
                    j += 1
                op = t[i:j]
                if ">" in op and t[j : j + 1] == "|":
                    j += 1
                ampersand = False
                if t[j : j + 1] == "&":
                    ampersand = True
                    j += 1
                self.redirect = ("out" if ">" in op else "in", ampersand)
                i = j
            else:
                sep = self.separator_at(i)
                if sep:
                    if d == "bash" and ch == "`":
                        self.dynamic = True  # `cmd` substitution: whatever it prints becomes part of the word
                        self.add_literal("`")
                    width, is_pipe = sep
                    self.end_segment(is_pipe)
                    i += width
                else:
                    self.add_unquoted(ch)
                    i += 1
        self.end_segment(False)
        return self.segments


def tokenize(text: str, dialect: str) -> list[Segment]:
    """The simple commands of a line, each a list of words and redirects, with what the shell would expand marked."""
    return _Scanner(text, dialect).run()


# --- deciding what a command touches -----------------------------------------------------------------------


@dataclass(frozen=True)
class Risk:
    program: str
    target: str
    why: str


@dataclass
class _State:
    root: str | None  # the project folder, normalised
    cwd: str | None  # where relative targets are read from; None when an earlier cd cannot be read
    stack: list[str | None] = field(default_factory=list)

    def copy(self) -> _State:
        return _State(self.root, self.cwd, list(self.stack))


def _to_windows(path: str) -> str:
    match = MSYS_DRIVE.match(path)
    if match:
        return match.group(1).upper() + ":" + (path[2:] or "/")
    return path


def _normalise(path: str | None) -> str | None:
    if not path:
        return None
    return ntpath.normpath(_to_windows(path))


def _under(full: str, base: str) -> bool:
    """True when `full` is strictly inside `base` (the folder itself is not inside itself)."""
    full, base = ntpath.normcase(ntpath.normpath(full)), ntpath.normcase(ntpath.normpath(base)).rstrip("\\")
    return full.startswith(base + "\\")


def _resolve(value: str, state: _State) -> str | None:
    """The full Windows path a literal target names, or None when it cannot be told (relative to an unknown folder)."""
    path = _to_windows(value)
    drive, rest = ntpath.splitdrive(path)
    if drive and not rest.startswith(("\\", "/")):
        return "C:\\<drive-relative>"  # C:foo depends on that drive's own current folder: treat as outside
    if not drive and not path.startswith(("\\", "/")):
        if state.cwd is None:
            return None
        path = ntpath.join(state.cwd, path)
    if not drive and path.startswith("/"):
        return "\\<posix-absolute>" + path  # /tmp, /usr, /: a place no Windows project path can match
    return ntpath.normpath(path)


def _path_problem(value: str, state: _State, allow_root: bool) -> str | None:
    if value.strip() == "" or PROVIDER_DRIVE.match(value):
        return None
    full = _resolve(value, state)
    if full is None:
        return WHY_CWD
    if state.root and (_under(full, state.root) or (allow_root and ntpath.normcase(full) == ntpath.normcase(state.root))):
        return None
    if any(_under(full, safe) for safe in SAFE_DIRS):
        return None
    return WHY_OUTSIDE


def _why(token: Token, state: _State, allow_root: bool = False) -> str | None:
    """Why a target is held, or None. `allow_root`: the project folder itself is fine (a find start, a cp or mv destination),
    which a delete or an overwrite of it never is."""
    if token.dynamic:
        return WHY_VARIABLE
    if token.glob:
        return WHY_GLOB
    if token.tilde:
        return WHY_TILDE
    return _path_problem(token.value, state, allow_root)


def _program(value: str) -> str:
    name = re.split(r"[\\/]", value.strip("(){}"))[-1].lower()
    return re.sub(r"\.(exe|bat|cmd|com)$", "", name)


def _is_powershell_style(program: str, dialect: str) -> bool:
    return dialect == "powershell" or "-" in program or program in POWERSHELL_ONLY


def _targets(program: str, args: list[Token], dialect: str) -> list[Token]:
    """The words after the program that name what it touches (options and their values removed)."""
    out: list[Token] = []
    if _is_powershell_style(program, dialect):
        i = 0
        while i < len(args):
            token = args[i]
            v = token.value
            if v.startswith("-") and len(v) > 1 and not v[1].isdigit():
                name, colon, attached = v.partition(":")
                lname = name.lower()
                if colon:
                    if lname in POWERSHELL_PATH_PARAMS and attached:
                        out.append(replace(token, value=attached))
                elif lname in POWERSHELL_SKIP_VALUE:
                    i += 1
                i += 1
                continue
            for part in v.split(",") if "," in v else [v]:
                out.append(replace(token, value=part))
            i += 1
        return out[:1] if program in WRITE_ONE_PATH else out
    windows_style = dialect == "cmd" or program in WINDOWS_ONLY
    after_dashes, i = False, 0
    while i < len(args):
        token = args[i]
        v = token.value
        if not after_dashes and v == "--":
            after_dashes = True
        elif not after_dashes and v.startswith("-") and len(v) > 1:
            if v == "-t" and i + 1 < len(args):
                out.append(args[i + 1])
                i += 1
            elif v.startswith("--target-directory="):
                out.append(replace(token, value=v.split("=", 1)[1]))
        elif program == "dd":
            if v.startswith("of="):
                out.append(replace(token, value=v[3:]))
        elif windows_style and CMD_SWITCH.match(v):
            pass
        else:
            out.append(token)
        i += 1
    return out


def _find_targets(args: list[Token]) -> list[Token]:
    """The start folders of a `find` that deletes (-delete, or -exec of a deleting command); [] when it only searches."""
    values = [a.value for a in args]
    deletes = "-delete" in values
    for i, v in enumerate(values):
        if v in ("-exec", "-execdir", "-ok", "-okdir") and i + 1 < len(values) and _program(values[i + 1]) in DESTRUCTIVE:
            deletes = True
    if not deletes:
        return []
    starts = []
    for a in args:
        if a.value.startswith("-") or a.value in ("(", ")", "!"):
            break
        starts.append(a)
    return starts


def _sed_targets(args: list[Token]) -> list[Token]:
    """The files of a `sed -i` (empty for a sed that only prints)."""
    if not any(SED_IN_PLACE.match(a.value) for a in args):
        return []
    positional, script_given, i = [], False, 0
    while i < len(args):
        v = args[i].value
        if v in ("-e", "-f", "--expression", "--file"):
            script_given = True
            i += 1
        elif v.startswith("--expression=") or v.startswith("--file="):
            script_given = True
        elif not v.startswith("-"):
            positional.append(args[i])
        i += 1
    return positional if script_given else positional[1:]


def _strip_prefix(words: list[Token], dialect: str) -> tuple[list[Token], bool]:
    """The command proper: leading assignments, keywords (do, then, if), sudo/env/nohup and xargs removed."""
    xargs = False
    while words:
        v = words[0].value
        low = v.lower()
        if dialect == "powershell" and low in ("&", "."):
            words = words[1:]
        elif dialect != "powershell" and ENV_ASSIGN.match(v):
            words = words[1:]
        elif dialect != "powershell" and low in PREFIX_WORDS:
            words = words[1:]
            while words and (words[0].value.startswith("-") or ENV_ASSIGN.match(words[0].value) or (low in ("timeout", "nice") and words[0].value.isdigit())):
                words = words[1:]
        elif dialect != "powershell" and low == "xargs":
            xargs = True
            words = words[1:]
            while words and words[0].value.startswith("-"):
                consume = 2 if words[0].value in XARGS_VALUE_OPTIONS else 1
                words = words[consume:]
        else:
            break
    return words, xargs


def _wrapped(program: str, args: list[Token]) -> tuple[str, str] | None:
    """The text a shell wrapper runs and the dialect to read it in; ("", "opaque") when it cannot be read."""
    if program in SHELLS:
        for i, a in enumerate(args):
            if re.fullmatch(r"-[a-z]*c[a-z]*", a.value) and i + 1 < len(args):
                return args[i + 1].value, "bash"
    elif program == "cmd":
        for i, a in enumerate(args):
            if a.value.lower() in ("/c", "/k", "/r"):
                return " ".join(x.value for x in args[i + 1 :]), "cmd"
    elif program in ("powershell", "pwsh"):
        for i, a in enumerate(args):
            low = a.value.lower()
            if low in ("-e", "-ec") or (len(low) >= 4 and "-encodedcommand".startswith(low)):
                return "", "opaque"
            if len(low) >= 2 and "-command".startswith(low):
                return " ".join(x.value for x in args[i + 1 :]), "powershell"
    return None


def _segment_risks(segment: Segment, dialect: str, state: _State, depth: int) -> list[Risk]:
    risks: list[Risk] = []
    for token in segment.tokens:
        if token.kind == "redir_out" and not token.dup and token.value.lower() not in SINKS:
            why = _why(token, state)
            if why:
                risks.append(Risk("redirect to", token.value, why))
    all_words = [t for t in segment.tokens if t.kind == "word"]
    if dialect == "powershell":
        for token in all_words:
            if DOTNET_FILE_CALL.search(token.value):
                risks.append(Risk(".NET call", token.value, WHY_DOTNET))
                break
    words, via_xargs = _strip_prefix(all_words, dialect)
    if not words or (words[0].dynamic and words[0].value.startswith("$")):
        return risks
    program, args = _program(words[0].value), words[1:]
    if program in CD_PROGRAMS:
        target = next((t for t in _targets(program, args, dialect)), None)
        if program in ("pushd", "push-location"):
            state.stack.append(state.cwd)
        if target is None or target.dynamic or target.glob or target.tilde or target.value == "-":
            state.cwd = None
        else:
            state.cwd = _resolve(target.value, state)
        return risks
    if program in POP_PROGRAMS:
        state.cwd = state.stack.pop() if state.stack else None
        return risks
    if program in OPAQUE_PROGRAMS:
        return [*risks, Risk(program, " ".join(a.value for a in args) or "(no text)", WHY_OPAQUE)]
    wrapped = _wrapped(program, args)
    if wrapped is not None:
        text, inner = wrapped
        if inner == "opaque":
            return [*risks, Risk(program, "-EncodedCommand", WHY_OPAQUE)]
        if depth < MAX_UNWRAP:
            risks += find_risks(text, inner, state.copy(), depth + 1)
        return risks
    if program == "find":
        targets, label = _find_targets(args), "find"
    elif program == "sed":
        targets, label = _sed_targets(args), "sed -i"
    elif program in DESTRUCTIVE and not (program in POWERSHELL_ONLY and dialect != "powershell"):
        if via_xargs:
            return [*risks, Risk(program, "(from standard input)", WHY_STDIN)]
        targets, label = _targets(program, args, dialect), program
        if not targets and segment.piped and _is_powershell_style(program, dialect):
            return [*risks, Risk(program, "(from the pipeline)", WHY_STDIN)]
    else:
        return risks
    for target in targets:
        why = _why(target, state, allow_root=program in ROOT_OK)
        if why:
            risks.append(Risk(label, target.value, why))
    return risks


def find_risks(command: str, dialect: str, state: _State, depth: int = 0) -> list[Risk]:
    risks: list[Risk] = []
    for segment in tokenize(command, dialect):
        risks += _segment_risks(segment, dialect, state, depth)
    return risks


# --- the hook's answer -------------------------------------------------------------------------------------

CHECK_FIRST = (
    "A delete, move or overwrite like this waits until you have seen what it will touch: first run a command that only "
    "shows it (printf '%s\\n' \"$VAR\" for a variable, ls -d for a glob, echo ~/path or Resolve-Path for a ~ or a "
    "PowerShell path), read the result back, then run the real command with that exact string "
    '(CLAUDE.md, "Verify before touching anything outside this repo").'
)


def _answer(decision: str, reason: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision, "permissionDecisionReason": reason}}


def decide(
    command: str,
    *,
    tool: str = "Bash",
    project_root: str | None = None,
    cwd: str | None = None,
    subagent: bool = False,
) -> dict | None:
    """The hook's JSON answer for one command, or None to let it run as typed."""
    dialect = "powershell" if tool == "PowerShell" else "bash"
    root = _normalise(project_root)
    state = _State(root, _normalise(cwd) or root)
    risks = list(dict.fromkeys(find_risks(command, dialect, state)))
    if not risks:
        return None
    listed = "; ".join(f"{r.program} {r.target} {r.why}" for r in risks[:MAX_LISTED])
    more = f" (and {len(risks) - MAX_LISTED} more)" if len(risks) > MAX_LISTED else ""
    reason = f"destructive_command_guard: {listed}{more}. {CHECK_FIRST}"
    if subagent:
        return _answer(
            "deny",
            reason + " This call comes from a sub-agent, which may not be able to show you a prompt, so it is refused: "
            "rewrite it with a literal path inside the project, or ask the owner to run it.",
        )
    return _answer("ask", reason)


def log_error(path: Path, exc: BaseException, now: Callable[[], datetime] = datetime.now) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as log:
            log.write(f"{now().isoformat(timespec='seconds')} {type(exc).__name__}: {exc}\n{traceback.format_exc()}\n")
    except OSError:
        pass  # a guard that cannot log still must answer


def guard_error_answer(exc: BaseException, subagent: bool) -> dict:
    """The answer when the guard itself failed: the command was not checked, so it is held, not run."""
    reason = (
        f"destructive_command_guard: guard error ({type(exc).__name__}); this command was not checked, so it is held "
        f"for a prompt instead of running (log: {LOG_PATH})"
    )
    return _answer("deny" if subagent else "ask", reason)


def run_hook(
    stdin_text: str,
    *,
    out: Callable[[str], None] = print,
    log_path: Path = LOG_PATH,
    project_root: str | None = None,
    decide_fn: Callable[..., dict | None] = decide,
    now: Callable[[], datetime] = datetime.now,
) -> int:
    """Always returns 0 (a non-zero code other than 2 would let the command run). Nothing printed means: let it run."""
    subagent = False
    try:
        data = json.loads(stdin_text.lstrip("﻿"))  # a byte-order mark (PowerShell 5.1 adds one to a pipe) is not an error
        if not isinstance(data, dict):
            raise ValueError("hook input is not a JSON object")
        subagent = bool(data.get("agent_id"))
        tool = data.get("tool_name")
        if tool not in TOOLS:
            return 0
        command = (data.get("tool_input") or {}).get("command")
        if not isinstance(command, str):
            return 0
        root = project_root or os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd")
        answer = decide_fn(command, tool=tool, project_root=root, cwd=data.get("cwd") or root, subagent=subagent)
        if answer is not None:
            out(json.dumps(answer))
    except Exception as exc:  # fail closed: a bug here holds the command for a prompt, it never waves it through
        log_error(log_path, exc, now)
        out(json.dumps(guard_error_answer(exc, subagent)))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--hook" not in args:
        print(__doc__)
        return 0
    try:
        text = sys.stdin.read()
    except Exception as exc:  # stdin unreadable: hold the command
        log_error(LOG_PATH, exc)
        print(json.dumps(guard_error_answer(exc, False)))
        return 0
    return run_hook(text)


if __name__ == "__main__":
    sys.exit(main())
