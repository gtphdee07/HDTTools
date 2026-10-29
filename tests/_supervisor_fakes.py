"""Fakes for the run-supervisor tests (#200): a clock that only moves when something waits, a process that
speaks and exits on a schedule, and an adb that answers from a script. Nothing here touches a real
process, emulator, adb or clock."""

from __future__ import annotations

import subprocess
from datetime import datetime, timedelta, timezone


class FakeClock:
    def __init__(self, start: float = 1000.0):
        self.t = start

    def now(self) -> float:
        return self.t

    def wall(self) -> datetime:
        return datetime(2026, 10, 28, 12, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=self.t - 1000.0)


class FakeProc:
    """`script` is [(seconds after the start, bytes)]; the process ends `exit_at` seconds after the start with
    `code` (never, when `exit_at` is None). `read(timeout)` moves the fake clock to the next thing that happens
    inside the timeout, or by the whole timeout when nothing does."""

    def __init__(self, clock: FakeClock, script=(), *, exit_at: float | None = None, code: int = 0):
        self.clock = clock
        self.begin = clock.t
        self.script = sorted(script)
        self.exit_at = exit_at
        self.code = code
        self.killed = False
        self.ended = False

    def read(self, timeout: float):
        if self.ended or self.killed:
            return b""
        deadline = self.clock.t + timeout
        if self.script and self.begin + self.script[0][0] <= deadline:
            at, data = self.script.pop(0)
            self.clock.t = max(self.clock.t, self.begin + at)
            return data
        if self.exit_at is not None and self.begin + self.exit_at <= deadline:
            self.clock.t = max(self.clock.t, self.begin + self.exit_at)
            self.ended = True
            return b""
        self.clock.t = deadline
        return None

    def wait(self) -> int:
        return self.code

    def kill(self) -> None:
        self.killed = True


class FakeAdb:
    """Answers `adb <args>` from `answers`: a function (args) -> (code, bytes) or an exception to raise. Records
    every call as (args, timeout)."""

    def __init__(self, answer=None):
        self.calls: list[tuple[list[str], float]] = []
        self.answer = answer or (lambda args: (0, b"1\n"))

    def __call__(self, args, timeout=5.0):
        self.calls.append((list(args), timeout))
        result = self.answer(list(args))
        if isinstance(result, BaseException):
            raise result
        return result

    def called(self, *prefix: str) -> list[list[str]]:
        return [a for a, _ in self.calls if a[: len(prefix)] == list(prefix)]


DEVICE_LISTED = b"List of devices attached\nemulator-5554\tdevice\n"
NO_DEVICE = b"List of devices attached\n"


def healthy_adb(extra=None) -> FakeAdb:
    def answer(args):
        if args == ["devices"]:
            return 0, DEVICE_LISTED
        if extra:
            replaced = extra(args)
            if replaced is not None:
                return replaced
        return 0, b"1\n"

    return FakeAdb(answer)


def timeout_error() -> subprocess.TimeoutExpired:
    return subprocess.TimeoutExpired(["adb"], 5)


def record(code: int, cls: str, test: str, current: int, total: int = 3, stack: str = "") -> bytes:
    """One `am instrument -r` status record."""
    lines = [
        f"INSTRUMENTATION_STATUS: class={cls}",
        f"INSTRUMENTATION_STATUS: current={current}",
        "INSTRUMENTATION_STATUS: id=AndroidJUnitRunner",
        f"INSTRUMENTATION_STATUS: numtests={total}",
        "INSTRUMENTATION_STATUS: stream=",
        f"{cls}:",
    ]
    if stack:
        lines.append(f"INSTRUMENTATION_STATUS: stack={stack}")
    lines += [f"INSTRUMENTATION_STATUS: test={test}", f"INSTRUMENTATION_STATUS_CODE: {code}", ""]
    return "\n".join(lines).encode()
