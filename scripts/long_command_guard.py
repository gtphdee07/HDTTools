"""PreToolUse hook that puts a build session's device commands on the supervised runner (#200).

  uv run --no-project scripts/long_command_guard.py --hook     # reads the hook's JSON on stdin

`.claude/settings.json` registers it for Bash. A direct device or emulator command typed in a
session (a Gradle line with `connectedDebugAndroidTest` or `connectedAndroidTest`, `adb ... shell am
instrument`, `emulator -avd`) runs with no output limit, no log and nobody watching, so a stall goes
unnoticed for an hour. The hook finds such a command, one simple command at a time (quoted text such
as `git commit -m "fix connectedDebugAndroidTest"` is not a command), and:

  - Gradle and `adb shell am instrument`: rewrites that command to the supervised form,
    `uv run --no-project .../run_supervisor.py --device -- <the same command, word for word>`. The command's own
    text is kept as typed, so a variable, glob, substitution or redirect still means what it did (a redirect now
    catches the runner's echo of the output). The rest of a compound line is left as it was. The harness applies
    `updatedInput` (Claude Code 2.1.296 documents it for PreToolUse), and deny/ask permission rules are still
    checked against the rewritten command.
  - `emulator -avd` (an emulator is quiet by design, so the stall watch would kill it) cannot run under the
    runner: the hook refuses, and the reason is the exact supervised command to type instead
    (`android_suite_loop.py --boot-only`, which boots it the supported way and leaves it running).

A command already under `run_supervisor.py` passes unchanged, and so does `android_suite_loop.py`: the loop
is itself a runner client (it writes the status file and stops a stalled run). Everything else passes
untouched, and so does any tool other than Bash. The hook fails open: whatever goes wrong inside it (bad
input, a bug) is appended to `%TEMP%\\hdttools-status\\long_command_guard.log` and the command runs.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
import tempfile
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

SUPERVISOR = Path(__file__).resolve().with_name("run_supervisor.py")
LOOP = "scripts/android_suite_loop.py"
LOG_PATH = Path(tempfile.gettempdir()) / "hdttools-status" / "long_command_guard.log"
GRADLE_OUTPUT_LIMIT_S = 300  # a Gradle device run prints nothing between "Starting N tests" and "Finished"
WHOLE_SUITE_OUTPUT_LIMIT_S = 900  # ... and a whole suite takes minutes in that silence (about 8 min for 342 tests)

CONNECTED_TASK = re.compile(r"^connected\w*AndroidTest$")
AM_INSTRUMENT = re.compile(r"\bshell\b.*\bam\s+instrument\b")
ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_]\w*=")
ENV_PREFIX = re.compile(r"""\A\s*(?:[A-Za-z_]\w*=(?:"[^"]*"|'[^']*'|\S*)\s+)*""")


@dataclass(frozen=True)
class Segment:
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class Finding:
    kind: str  # gradle | adb | emulator
    segment: Segment
    env_text: str  # leading VAR=value words as typed, kept in front of the wrapper
    command_text: str  # the command and its arguments as typed
    tokens: list[str]


def split_segments(command: str) -> list[Segment]:
    """The simple commands of a shell line, split at `&&`, `||`, `;`, `|`, `&` and newlines outside quotes."""
    segments: list[Segment] = []
    quote = ""
    start = 0
    i = 0
    while i < len(command):
        ch = command[i]
        if quote:
            if ch == "\\" and quote == '"':
                i += 1
            elif ch == quote:
                quote = ""
        elif ch == "\\":
            i += 1
        elif ch in "'\"":
            quote = ch
        else:
            width = 0
            if command[i : i + 2] in ("&&", "||"):
                width = 2
            elif ch in ";|\n":
                width = 1
            elif ch == "&" and command[i - 1 : i] not in ("<", ">") and command[i + 1 : i + 2] != ">":
                width = 1
            if width:
                segments.append(Segment(start, i, command[start:i]))
                i += width
                start = i
                continue
        i += 1
    segments.append(Segment(start, len(command), command[start:]))
    return [s for s in segments if s.text.strip()]


def _program(token: str) -> str:
    name = re.split(r"[\\/]", token)[-1].lower()
    return re.sub(r"\.(exe|bat|cmd)$", "", name)


def find_device_commands(command: str) -> list[Finding]:
    """The device or emulator commands in a shell line that are not already under the runner."""
    found = []
    for segment in split_segments(command):
        try:
            words = shlex.split(segment.text, posix=True)
        except ValueError:
            continue
        while words and ENV_ASSIGNMENT.match(words[0]):
            words.pop(0)
        if not words or any(w.replace("\\", "/").endswith("run_supervisor.py") for w in words):
            continue
        if any(w.replace("\\", "/").endswith(LOOP) for w in words):
            continue  # the loop supervises its own runs
        program, joined = _program(words[0]), " ".join(words)
        if program in ("gradlew", "gradle") and any(CONNECTED_TASK.match(w) for w in words[1:]):
            kind = "gradle"
        elif program == "adb" and AM_INSTRUMENT.search(joined):
            kind = "adb"
        elif program == "emulator" and any(w == "-avd" or w.startswith("@") for w in words[1:]):
            kind = "emulator"
        else:
            continue
        prefix = ENV_PREFIX.match(segment.text)
        end = prefix.end() if prefix else 0
        found.append(Finding(kind, segment, segment.text[:end].strip(), segment.text[end:].strip(), words))
    return found


LOOP_BOOT_FLAGS = ("-no-snapshot", "-no-snapshot-save", "-no-boot-anim")  # the loop's cold boot already passes these


def emulator_flags(tokens: list[str]) -> str:
    """An emulator command line as the loop's `--boot-only` options: the AVD and GPU become `--avd` and `--gpu`, the
    flags the loop always passes are dropped, and any other word is forwarded as `--emulator-arg=<word>`, in order."""
    words, found, i = tokens[1:], [], 0
    while i < len(words):
        word = words[i]
        if word in ("-avd", "-gpu") and i + 1 < len(words):
            found.append(f"--{word[1:]} {shlex.quote(words[i + 1])}")
            i += 2
            continue
        if word.startswith("@"):
            found.append(f"--avd {shlex.quote(word[1:])}")
        elif word not in LOOP_BOOT_FLAGS:
            found.append(f"--emulator-arg={shlex.quote(word)}")
        i += 1
    return "".join(f" {option}" for option in found)


def silence_limit_s(finding: Finding) -> int | None:
    """How long the run may print nothing before it is called hung; None keeps the runner's default (120 s). A Gradle
    device run prints nothing between "Starting N tests" and "Finished", so a class-level run gets 300 s and a whole-suite
    run 900 s; `adb ... am instrument` without `-r` prints no progress at all, so it gets the whole-suite limit."""
    if finding.kind == "gradle":
        class_level = any(w.startswith("-Pandroid.testInstrumentationRunnerArguments.") for w in finding.tokens)
        return GRADLE_OUTPUT_LIMIT_S if class_level else WHOLE_SUITE_OUTPUT_LIMIT_S
    if finding.kind == "adb" and "-r" not in finding.tokens:
        return WHOLE_SUITE_OUTPUT_LIMIT_S
    return None


def supervised_form(finding: Finding) -> str:
    """The command to type instead (the same words, under the runner)."""
    if finding.kind == "emulator":
        return "uv run scripts/android_suite_loop.py --boot-only" + emulator_flags(finding.tokens)
    seconds = silence_limit_s(finding)
    limit = f" --output-limit-s {seconds}" if seconds else ""
    runner = f"uv run --no-project {shlex.quote(SUPERVISOR.as_posix())} --device{limit} -- {finding.command_text}"
    return f"{finding.env_text} {runner}".strip()


def decide(command: str) -> dict | None:
    """The hook's JSON answer for a Bash command, or None to let it run as typed."""
    findings = find_device_commands(command)
    if not findings:
        return None
    if all(f.kind != "emulator" for f in findings):
        rewritten = command
        for finding in reversed(findings):  # from the back, so earlier offsets stay valid
            seg = finding.segment
            lead = seg.text[: len(seg.text) - len(seg.text.lstrip())]
            trail = seg.text[len(seg.text.rstrip()) :]
            rewritten = rewritten[: seg.start] + lead + supervised_form(finding) + trail + rewritten[seg.end :]
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "long_command_guard: the device command now runs under scripts/run_supervisor.py "
                "(a stalled run is stopped and reported hung; status: uv run scripts/run_status.py)",
                "updatedInput": {"command": rewritten},
            }
        }
    names = "; ".join(supervised_form(f) for f in findings)
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "A device or emulator command must run under the supervised runner so a stall is caught in minutes, and an "
                f"emulator start cannot be wrapped (it is quiet by design). Run it as: {names}  "
                "(docs/agents/session-handoff.md, android/TESTING.md)"
            ),
        }
    }


def log_error(path: Path, exc: BaseException, now: Callable[[], datetime] = datetime.now) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as log:
            log.write(f"{now().isoformat(timespec='seconds')} {type(exc).__name__}: {exc}\n{traceback.format_exc()}\n")
    except OSError:
        pass  # a hook that cannot log still must not block the command


def run_hook(
    stdin_text: str,
    *,
    out: Callable[[str], None] = print,
    log_path: Path = LOG_PATH,
    decide_fn=decide,
    now: Callable[[], datetime] = datetime.now,
) -> int:
    """Always returns 0. Nothing printed means: let the command run as typed."""
    try:
        data = json.loads(stdin_text)
        if not isinstance(data, dict) or data.get("tool_name") != "Bash":
            return 0
        command = (data.get("tool_input") or {}).get("command")
        if not isinstance(command, str):
            return 0
        answer = decide_fn(command)
        if answer is not None:
            out(json.dumps(answer))
    except Exception as exc:  # fail open: a bug here must never lock a session out
        log_error(log_path, exc, now)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--hook" not in args:
        print(__doc__)
        return 0
    try:
        text = sys.stdin.read()
    except Exception as exc:  # stdin unreadable: let the command run
        log_error(LOG_PATH, exc)
        return 0
    return run_hook(text)


if __name__ == "__main__":
    sys.exit(main())
