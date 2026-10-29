"""Runs any long command under a watchdog so a stalled run is caught in minutes (#200).

Long commands (an emulator run, a Gradle device task, the suites /ticket-finish starts)
sometimes stall without failing: the output stops and nothing times out for a long while. This
wrapper runs the command, writes what it is doing to `android/build/run-status/` (the layout
is in scripts/run_status.py; read it with `uv run scripts/run_status.py`), and when the run
stalls it saves evidence, marks the run `hung`, stops it and exits with a distinct code.

  uv run scripts/run_supervisor.py [--device] [options] -- <command> [args ...]

  the class-level run:  uv run scripts/run_supervisor.py --device -- android/gradlew -p android connectedDebugAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=<fqcn>
  the full suite:       uv run scripts/android_suite_loop.py --runs 1 --retry-infra-abort
                        (a runner client: it boots the emulator, runs `am instrument -w -r` through this module and writes the same files)

A stall is any of: no output for longer than --output-limit-s (default 120), one test running
longer than --test-limit-s (default 90), the run longer than --wall-limit-s (off by default),
or, with --device, `adb shell getprop sys.boot_completed` unanswered within 5 s, or the device
missing from `adb devices`, on three checks in a row (every 10 s). A command that is quiet by
design (a long build step) takes a higher --output-limit-s. For `am instrument -w -r` output
the running test, the number finished and the number expected are exact; for any other
output only the output age (and the device check) is known, plus the test count of a Gradle
`Starting N tests on <device>` line.

On a stall: a `hung` line is written first, then the evidence goes to
`android/build/run-status/<run-id>/` (logcat -d, the last 2000 lines; a screencap PNG; the
head of `dumpsys window windows`; `adb devices -l`; the last 200 output lines; the process
list), each with its own 10 s limit so a dead device cannot stall the wrapper too, then
--on-stall decides: `stop` (default) kills the command's process tree and the emulator,
`flag` leaves the run going (the wrapper keeps draining its output and still exits hung).
Exit code: the command's own, or 124 (HUNG_EXIT_CODE) for a hung run. A hung run, and any run
that ended because the device or the system fell over, is an `infra-abort`; a failing test is
`test-failed` and is never retried. --retry-infra-abort re-runs an infra-abort once on a
freshly booted emulator (--device only).
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_status  # noqa: E402

HUNG_EXIT_CODE = 124  # what GNU timeout(1) exits with; the wrapper's exit for a hung run

PASSED = "passed"
TEST_FAILED = "test-failed"
INFRA_ABORT = "infra-abort"

# Patterns that mean the emulator, adb or the system server died, whatever else the output says.
# The first one found is the reason quoted in a summary. (android_suite_loop.py labels runs with these too.)
ABORT_MARKERS = (
    "INSTRUMENTATION_ABORTED",
    "System has crashed",
    "Test run failed to complete",
    "Can't find service",
    "device offline",
    r"device '[^']*' not found",
    "no devices/emulators found",
    "No connected devices",
    "ShellCommandUnresponsiveException",
    "ReferenceQueueDaemon timed out",
    "INSTRUMENTATION_FAILED",
    "suite timed out",
    "run hung",
    r"Execution failed for task ':app:wakeEmulatorForInstrumentedTests'",
)

OUTPUT_LIMIT_S = 120.0
TEST_LIMIT_S = 90.0
CHECK_INTERVAL_S = 10.0
DEVICE_CALL_TIMEOUT_S = 5.0
DEVICE_MISSES = 3
EVIDENCE_CALL_TIMEOUT_S = 10.0
LOGCAT_LINES = 2000
WINDOW_HEAD_LINES = 200
OUTPUT_TAIL_LINES = 200
KEPT_OUTPUT_CHARS = 8_000_000

# The measured run time (seconds, idle machine) of each session-level suite; a wall cap is about ten
# times it (#200), never under MIN_CAP_S, so a cold start cannot trip it.
CAP_FACTOR = 10
MIN_CAP_S = 60.0
DEFAULT_CAP_S = 1200.0
SUITE_OUTPUT_LIMIT_S = 300.0  # static checks and the slow Python suites print little for a while
SLOW_MARKER_EXPRESSION = "slow and not external"  # the planner's marker expression for the slow Python run
SLOW_PYTHON_MEASURED_S = 133.0
SUITE_MEASURED_S = (
    ("static_checks.py", 196.0),
    ("android_session_end.py", 106.0),
    ("workers/scan-proxy", 2.0),
    ("--prefix web", 30.0),
    ("pytest", 61.0),
)

Adb = Callable[..., "tuple[int, bytes]"]
RunTool = Callable[..., "tuple[int, bytes]"]


# --- reading `am instrument -w -r` output --------------------------------------------------------

STATUS_LINE = re.compile(r"^INSTRUMENTATION_STATUS: (\w+)=(.*)$")
STATUS_CODE = re.compile(r"^INSTRUMENTATION_STATUS_CODE: (-?\d+)")
GRADLE_COUNT = re.compile(r"Starting (\d+) tests? on ")
INSTALL_LINE = re.compile(r"installing apk|performing (?:streamed )?install|\binstall(?:ing)?\b.*\.apk", re.I)


@dataclass(frozen=True)
class Event:
    kind: str  # install | of | test_started | test_finished
    test: str | None = None
    code: int | None = None  # for test_finished: the instrumentation status code (0 ok, -2 failed, ...)
    of: int | None = None


class Progress:
    """Turns output lines into events. `am instrument -r` prints one record per test start and finish:
    `INSTRUMENTATION_STATUS: key=value` lines (a value can continue over following lines) closed by an
    `INSTRUMENTATION_STATUS_CODE`: 1 started, 0 finished OK, -2 failed, -3 ignored, -4 assumption failed."""

    def __init__(self) -> None:
        self.n = 0  # tests finished
        self.of: int | None = None
        self.failures = 0
        self._fields: dict[str, str] = {}
        self._key: str | None = None

    def feed(self, line: str) -> list[Event]:
        line = line.rstrip("\r")
        events: list[Event] = []
        match = STATUS_LINE.match(line)
        if match:
            self._key = match.group(1)
            self._fields[self._key] = match.group(2)
            return events
        match = STATUS_CODE.match(line)
        if match:
            fields, self._fields, self._key = self._fields, {}, None
            return self._record(int(match.group(1)), fields)
        if line.startswith("INSTRUMENTATION_"):
            self._key = None
        elif self._key is not None:
            self._fields[self._key] += "\n" + line  # the rest of a multi-line value (a stack trace)
        count = GRADLE_COUNT.search(line)
        if count and self.of is None:
            self.of = int(count.group(1))
            events.append(Event("of", of=self.of))
        if INSTALL_LINE.search(line):
            events.append(Event("install"))
        return events

    def _record(self, code: int, fields: dict[str, str]) -> list[Event]:
        events: list[Event] = []
        total = fields.get("numtests", "").strip()
        if total.isdigit() and int(total) != self.of:
            self.of = int(total)
            events.append(Event("of", of=self.of))
        if not fields.get("test"):
            return events  # the runner's own status block, not a test
        name = f"{fields.get('class', '?').strip()}.{fields['test'].strip()}"
        if code == 1:
            events.append(Event("test_started", test=name))
        else:
            self.n += 1
            self.failures += code == -2
            events.append(Event("test_finished", test=name, code=code))
        return events


# --- the watchdog ------------------------------------------------------------------------------


@dataclass(frozen=True)
class Limits:
    output_s: float = OUTPUT_LIMIT_S
    test_s: float = TEST_LIMIT_S
    device_misses: int = DEVICE_MISSES
    wall_s: float | None = None


@dataclass(frozen=True)
class Stall:
    reason: str  # no output | test too long | device not responding | device offline | wall cap
    detail: str
    test: str | None = None


class Watchdog:
    """Decides, from times it is told about, whether the run has stalled. It reads no clock itself."""

    def __init__(self, limits: Limits, start: float):
        self.limits = limits
        self.start = start
        self.last_output = start
        self.test: str | None = None
        self.test_started = start
        self._misses = 0
        self._offline = 0
        self.device = "none"

    def output(self, t: float) -> None:
        self.last_output = t

    def test_start(self, name: str, t: float) -> None:
        self.test, self.test_started = name, t

    def test_end(self) -> None:
        self.test = None

    def device_check(self, state: str, *, counted: bool = True) -> None:
        """`state` is ok, miss (no answer) or offline (not in `adb devices`). A check made while the device is
        still booting is `counted=False`: it shows in `device` but cannot make a stall. One good check clears
        the streak, so a single miss is never a stall."""
        if state == "ok":
            self._misses = self._offline = 0
            self.device = "ok"
            return
        self.device = "offline" if state == "offline" else "slow"
        if not counted:
            self._misses = self._offline = 0
            return
        if state == "offline":
            self._offline += 1
            self._misses = 0
        else:
            self._misses += 1
            self._offline = 0

    def output_age(self, t: float) -> float:
        return max(t - self.last_output, 0.0)

    def check(self, t: float) -> Stall | None:
        limits = self.limits
        if self._offline >= limits.device_misses:
            return Stall("device offline", f"the device was missing from `adb devices` on {self._offline} checks in a row")
        if self._misses >= limits.device_misses:
            return Stall("device not responding", f"`getprop sys.boot_completed` unanswered on {self._misses} checks in a row")
        if self.test is not None and t - self.test_started > limits.test_s:
            return Stall(
                "test too long", f"{self.test} has been running {t - self.test_started:.0f} s (limit {limits.test_s:.0f} s)", self.test,
            )
        if self.output_age(t) > limits.output_s:
            return Stall("no output", f"no output for {self.output_age(t):.0f} s (limit {limits.output_s:.0f} s)")
        if limits.wall_s is not None and t - self.start > limits.wall_s:
            return Stall("wall cap", f"the run is over its {limits.wall_s:.0f} s cap")
        return None


# --- calling adb and other tools (every call has its own limit) ---------------------------------


def run_tool(argv: list[str], timeout: float) -> tuple[int, bytes]:
    """Runs a tool and returns (exit code, stdout + stderr). Raises subprocess.TimeoutExpired or OSError."""
    exe = shutil.which(argv[0]) or argv[0]
    proc = subprocess.run(
        [exe, *argv[1:]], capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL,
        env={**os.environ, "MSYS_NO_PATHCONV": "1"},
    )
    return proc.returncode, (proc.stdout or b"") + (proc.stderr or b"")


def real_adb() -> Adb | None:
    """adb as a function (args, timeout), or None when the SDK cannot be found."""
    try:
        import android_suite_loop

        adb_path = android_suite_loop.find_sdk_tool("platform-tools", "adb")
    except (RuntimeError, ImportError):
        return None

    def adb(args: list[str], timeout: float = DEVICE_CALL_TIMEOUT_S) -> tuple[int, bytes]:
        return run_tool([adb_path, *args], timeout)

    return adb


def device_state(adb: Adb, timeout: float = DEVICE_CALL_TIMEOUT_S) -> str:
    """ok, offline (not listed by `adb devices`) or miss (a call timed out or failed)."""
    try:
        code, text = adb(["devices"], timeout)
        listed = code == 0 and any(ln.split()[1:2] == [b"device"] for ln in text.splitlines()[1:])
        if code == 0 and not listed:
            return "offline"
        if code != 0:
            return "miss"
        code, _ = adb(["shell", "getprop", "sys.boot_completed"], timeout)
    except (subprocess.TimeoutExpired, OSError):
        return "miss"
    return "ok" if code == 0 else "miss"


def process_list_command() -> list[str]:
    return ["tasklist", "/FO", "CSV"] if os.name == "nt" else ["ps", "-eo", "pid,etime,args"]


def collect_evidence(
    directory: Path,
    *,
    output_tail: list[str],
    device: bool,
    adb: Adb | None,
    tool: RunTool = run_tool,
    call_timeout_s: float = EVIDENCE_CALL_TIMEOUT_S,
) -> dict[str, str]:
    """Saves what a person needs to see why the run stalled. Each item is tried on its own with its own
    limit, so a dead device costs a few call timeouts, never the whole wrapper. Returns item -> outcome,
    and saves the same as `evidence.json`."""
    directory.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, str] = {}

    def attempt(name: str, filename: str, produce: Callable[[], bytes]) -> None:
        try:
            data = produce()
            (directory / filename).write_bytes(data)
            manifest[name] = "saved"
        except subprocess.TimeoutExpired:
            manifest[name] = f"failed: no answer within {call_timeout_s:.0f} s"
        except (OSError, ValueError, RuntimeError) as exc:
            manifest[name] = f"failed: {exc}"

    def adb_bytes(args: list[str], keep: Callable[[bytes], bytes] = lambda b: b) -> Callable[[], bytes]:
        def produce() -> bytes:
            assert adb is not None
            code, data = adb(args, call_timeout_s)
            if code != 0:
                raise RuntimeError(f"adb exited {code}")
            return keep(data)

        return produce

    attempt("output-tail", "output-tail.txt", lambda: "\n".join(output_tail[-OUTPUT_TAIL_LINES:]).encode("utf-8", "replace"))
    attempt("process-list", "processes.txt", lambda: tool(process_list_command(), call_timeout_s)[1])
    if device and adb is not None:
        attempt("logcat", "logcat.txt", adb_bytes(["logcat", "-d", "-t", str(LOGCAT_LINES)]))
        attempt("screencap", "screencap.png", adb_bytes(["exec-out", "screencap", "-p"]))
        attempt(
            "window", "window.txt",
            adb_bytes(["shell", "dumpsys", "window", "windows"], lambda b: b"\n".join(b.splitlines()[:WINDOW_HEAD_LINES])),
        )
        attempt("devices", "devices.txt", adb_bytes(["devices", "-l"]))
    (directory / "evidence.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


# --- the process --------------------------------------------------------------------------------


def kill_tree(pid: int) -> None:
    """Ends a process and its children."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=20)
        return
    import signal

    try:
        os.killpg(os.getpgid(pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


class RealProc:
    """A child process whose output a thread feeds into a queue, so the watchdog can wait with a timeout."""

    def __init__(self, command: list[str], cwd: Path | None = None):
        exe = shutil.which(command[0]) or command[0]
        flags = {"creationflags": 0x00000200} if os.name == "nt" else {"start_new_session": True}  # CREATE_NEW_PROCESS_GROUP
        self._proc = subprocess.Popen(
            [exe, *command[1:]], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            bufsize=0, env={**os.environ, "PYTHONUNBUFFERED": "1", "MSYS_NO_PATHCONV": "1"}, **flags,
        )
        self._chunks: queue.Queue[bytes] = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self) -> None:
        assert self._proc.stdout is not None
        while True:
            chunk = self._proc.stdout.read(8192)  # unbuffered: returns what is there, b"" at the end
            self._chunks.put(chunk)
            if not chunk:
                return

    def read(self, timeout: float) -> bytes | None:
        """A chunk of output, None if none came within `timeout`, b"" once the output has ended."""
        try:
            return self._chunks.get(timeout=timeout)
        except queue.Empty:
            return None

    def wait(self) -> int:
        return self._proc.wait()

    def kill(self) -> None:
        kill_tree(self._proc.pid)
        try:
            self._proc.kill()
        except OSError:
            pass


class RealClock:
    @staticmethod
    def now() -> float:
        return time.monotonic()


# --- supervising a run ------------------------------------------------------------------------


@dataclass
class RunResult:
    exit_code: int
    phase: str  # done | failed | hung
    outcome: str  # passed | test-failed | infra-abort
    reason: str = ""
    detail: str = ""
    evidence_dir: Path | None = None
    output: str = ""
    n: int = 0
    of: int | None = None


def _abort_line(output: str) -> str | None:
    for marker in ABORT_MARKERS:
        found = re.search(marker, output)
        if found:
            return next(ln for ln in output.splitlines() if found.group(0) in ln).strip()[:200]
    return None


def supervise(
    command: list[str],
    *,
    writer: run_status.StatusWriter,
    spawn: Callable[[list[str]], object],
    clock=RealClock,
    limits: Limits = Limits(),
    device: bool = False,
    adb: Adb | None = None,
    tool: RunTool = run_tool,
    on_stall: str = "stop",
    phase: str | None = None,
    check_interval_s: float = CHECK_INTERVAL_S,
    poll_s: float = 1.0,
    echo: Callable[[bytes], None] | None = None,
    evidence_dir: Path | None = None,
) -> RunResult:
    """Runs `command` (through `spawn`) and watches it. The process object offers read(timeout) -> bytes | None
    | b"" at the end, wait() -> exit code and kill()."""
    if on_stall not in ("stop", "flag"):
        raise ValueError(f"on_stall must be stop or flag, not {on_stall!r}")
    start = clock.now()
    watchdog = Watchdog(limits, start)
    progress = Progress()
    phase = phase or ("boot" if device else "test")
    use_device = device and adb is not None
    watchdog.device = "ok" if use_device else "none"
    writer.emit(phase, device=watchdog.device, last_output_age_s=0.0, exit_code=None, outcome=None, reason=None, detail=None, evidence=None)

    proc = spawn(command)
    tail: deque[str] = deque(maxlen=OUTPUT_TAIL_LINES)
    kept: deque[str] = deque()
    kept_chars = 0
    pending = ""
    stall: Stall | None = None
    next_beat = start

    def beat(now: float, new_phase: str | None = None, **fields) -> None:
        nonlocal phase
        phase = new_phase or phase
        writer.emit(
            phase, n=progress.n if (progress.n or progress.of) else None, of=progress.of,
            last_output_age_s=round(watchdog.output_age(now), 1), device=watchdog.device, **fields,
        )

    def handle_line(line: str, now: float) -> None:
        for event in progress.feed(line):
            if event.kind == "install" and phase == "boot":
                beat(now, "install")
            elif event.kind == "of":
                beat(now)
            elif event.kind == "test_started":
                watchdog.test_start(event.test or "?", now)
                beat(now, "test", test=event.test)
            elif event.kind == "test_finished":
                watchdog.test_end()
                beat(now, "test", test=None)

    while True:
        now = clock.now()
        chunk = proc.read(max(min(poll_s, next_beat - now), 0.0))
        now = clock.now()
        if chunk == b"":
            break
        if chunk:
            if echo is not None:
                echo(chunk)
            watchdog.output(now)
            text = chunk.decode("utf-8", errors="replace")
            kept.append(text)
            kept_chars += len(text)
            while kept_chars > KEPT_OUTPUT_CHARS and len(kept) > 1:
                kept_chars -= len(kept.popleft())
            *lines, pending = (pending + text).split("\n")
            for line in lines:
                tail.append(line.rstrip("\r"))
                handle_line(line, now)
        if now >= next_beat:
            if use_device:
                watchdog.device_check(device_state(adb), counted=phase in ("install", "test"))  # type: ignore[arg-type]
            beat(now)
            next_beat = now + check_interval_s
        if stall is None:
            stall = watchdog.check(now)
            if stall is not None:
                evidence = evidence_dir or writer.directory / writer.run_id
                beat(now, "hung", reason=stall.reason, detail=stall.detail, test=stall.test or watchdog.test)
                manifest = collect_evidence(
                    evidence, output_tail=list(tail) + ([pending] if pending else []), device=use_device, adb=adb, tool=tool,
                )
                beat(clock.now(), "hung", reason=stall.reason, detail=stall.detail, test=stall.test or watchdog.test,
                     evidence=str(evidence), evidence_items=manifest, outcome=INFRA_ABORT, exit_code=HUNG_EXIT_CODE)
                if on_stall == "stop":
                    proc.kill()
                    if use_device:
                        try:
                            adb(["emu", "kill"], EVIDENCE_CALL_TIMEOUT_S)  # type: ignore[misc]
                        except (subprocess.TimeoutExpired, OSError):
                            pass
                    return RunResult(
                        HUNG_EXIT_CODE, "hung", INFRA_ABORT, stall.reason, stall.detail, evidence,
                        "".join(kept) + "\nrun hung: " + stall.detail, progress.n, progress.of,
                    )

    code = proc.wait()
    now = clock.now()
    output = "".join(kept)
    if stall is not None:  # on_stall == "flag": the run went on, but it stays hung
        return RunResult(HUNG_EXIT_CODE, "hung", INFRA_ABORT, stall.reason, stall.detail, evidence_dir or writer.directory / writer.run_id,
                         output, progress.n, progress.of)
    if device and (marker := _abort_line(output)):
        outcome, reason = INFRA_ABORT, marker
    elif code != 0 or progress.failures or "FAILURES!!!" in output:
        outcome, reason = TEST_FAILED, f"exit code {code}" if code else "tests failed"
    else:
        outcome, reason = PASSED, ""
    if outcome != PASSED and code == 0:
        code = 1
    final = "done" if outcome == PASSED else "failed"
    beat(now, final, test=None, exit_code=code, outcome=outcome, reason=reason or None)
    return RunResult(code, final, outcome, reason, "", None, output, progress.n, progress.of)


# --- suites started by /ticket-finish ----------------------------------------------------------


def suite_cap_s(argv: list[str], *, factor: float = CAP_FACTOR) -> float:
    """The wall cap for a session-level suite: about ten times its measured run (SUITE_MEASURED_S)."""
    line = " ".join(argv)
    if any(arg == SLOW_MARKER_EXPRESSION for arg in argv):  # a whole argument: "not slow and not external" is the fast run
        return max(SLOW_PYTHON_MEASURED_S * factor, MIN_CAP_S)
    for needle, measured in SUITE_MEASURED_S:
        if needle in line:
            return max(measured * factor, MIN_CAP_S)
    return DEFAULT_CAP_S


@dataclass
class SupervisedProcess:
    """What a suite run leaves for the caller: the exit code (HUNG_EXIT_CODE if it stalled or hit its cap)."""

    returncode: int
    hung_reason: str = ""
    evidence: str = ""
    output: str = ""


def supervised_run_command(
    command: list[str],
    cwd: Path | None = None,
    *,
    status_dir: Path = run_status.DEFAULT_DIR,
    spawn: Callable[[list[str]], object] | None = None,
    clock=RealClock,
    factor: float = CAP_FACTOR,
    output_limit_s: float = SUITE_OUTPUT_LIMIT_S,
    echo: Callable[[bytes], None] | None = None,
    now: Callable[[], datetime] = run_status.utc_now,
) -> SupervisedProcess:
    """A drop-in `run_command(command, cwd)` for a suite: the command runs under the watchdog with its wall cap,
    its output still reaches the terminal. A stalled or capped suite returns HUNG_EXIT_CODE, which the ledger
    never records as a pass."""
    run_id = new_run_id("suite", now())
    writer = run_status.StatusWriter(run_id, " ".join(command), status_dir, now=now)
    result = supervise(
        command, writer=writer, spawn=spawn or (lambda argv: RealProc(argv, cwd)), clock=clock,
        limits=Limits(output_s=output_limit_s, wall_s=suite_cap_s(command, factor=factor)),
        echo=echo if echo is not None else _echo_stdout,
    )
    hung = result.phase == "hung"
    return SupervisedProcess(result.exit_code, f"{result.reason}: {result.detail}" if hung else "", str(result.evidence_dir or ""), result.output)


def _echo_stdout(chunk: bytes) -> None:
    sys.stdout.buffer.write(chunk)
    sys.stdout.buffer.flush()


def new_run_id(prefix: str, moment: datetime) -> str:
    return f"{prefix}-{moment.strftime('%Y%m%d-%H%M%S')}"


# --- a device run that is retried once ---------------------------------------------------------


def run_with_one_retry(attempt: Callable[[], object], *, is_infra_abort: Callable[[object], bool],
                       fresh_emulator: Callable[[], bool], out: Callable[[str], None] = print) -> tuple[object, int]:
    """Runs `attempt`; if it ended because of the device or the system (an infra-abort), boots a fresh emulator
    and runs it once more. A second abort is the answer. A failing test is never retried. Returns (result, attempts)."""
    result = attempt()
    if not is_infra_abort(result):
        return result, 1
    out("infra-abort: retrying once on a freshly booted emulator")
    if not fresh_emulator():
        out("the fresh emulator did not come up; keeping the infra-abort")
        return result, 1
    return attempt(), 2


# --- the command line ---------------------------------------------------------------------------


def _split_command(argv: list[str]) -> tuple[list[str], list[str]]:
    if "--" not in argv:
        return argv, []
    index = argv.index("--")
    return argv[:index], argv[index + 1:]


def main(argv: list[str] | None = None) -> int:
    own, command = _split_command(list(sys.argv[1:] if argv is None else argv))
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--device", action="store_true", help="the command uses the emulator: also check adb every 10 s")
    parser.add_argument("--output-limit-s", type=float, default=OUTPUT_LIMIT_S)
    parser.add_argument("--test-limit-s", type=float, default=TEST_LIMIT_S)
    parser.add_argument("--wall-limit-s", type=float, default=None, help="end the run if it takes longer than this")
    parser.add_argument("--on-stall", choices=("stop", "flag"), default="stop")
    parser.add_argument("--retry-infra-abort", action="store_true", help="re-run once on a fresh emulator after an infra-abort (--device)")
    parser.add_argument("--status-dir", type=Path, default=run_status.DEFAULT_DIR)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(own)
    if not command:
        parser.error("give the command after `--`")
    if args.retry_infra_abort and not args.device:
        parser.error("--retry-infra-abort needs --device")

    adb = real_adb() if args.device else None
    if args.device and adb is None:
        print("run_supervisor: no Android SDK found (ANDROID_SDK_ROOT / ANDROID_HOME); the device is not checked.", file=sys.stderr)
    limits = Limits(args.output_limit_s, args.test_limit_s, DEVICE_MISSES, args.wall_limit_s)

    def attempt() -> RunResult:
        moment = run_status.utc_now()
        run_id = args.run_id or new_run_id("run", moment)
        writer = run_status.StatusWriter(run_id, " ".join(command), args.status_dir)
        result = supervise(
            command, writer=writer, spawn=lambda argv: RealProc(argv), limits=limits, device=args.device, adb=adb,
            on_stall=args.on_stall, echo=_echo_stdout,
        )
        print(f"run_supervisor: {run_id} {result.phase}" + (f" ({result.reason}: {result.detail})" if result.reason else "")
              + f"; status in {args.status_dir}", flush=True)
        return result

    if not args.retry_infra_abort:
        return attempt().exit_code

    def fresh_emulator() -> bool:
        import android_suite_loop as loop

        return loop.restart_emulator(
            loop.make_adb(loop.find_sdk_tool("platform-tools", "adb")), loop.find_sdk_tool("emulator", "emulator"),
            avd=loop.AVD, gpu=loop.GPU, extra_args=[], log_path=args.status_dir / "emulator.log", settle_s=20,
        )

    result, _ = run_with_one_retry(attempt, is_infra_abort=lambda r: r.outcome == INFRA_ABORT, fresh_emulator=fresh_emulator)
    return result.exit_code  # type: ignore[attr-defined]


if __name__ == "__main__":
    sys.exit(main())
