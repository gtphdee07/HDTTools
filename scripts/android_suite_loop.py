"""Run the full instrumented Android suite N times in a row (#127), restarting
the emulator before every run, and report how many runs reached the end of the
suite (passed, or failed a real test) versus how many were thrown away because
the emulator or adb fell over.

Why this exists: `gradlew connectedDebugAndroidTest` on the dev emulator lost
the device in 8 of 11 runs (device offline, system server crash), none of them
a fault in the app's tests. This is the supported way to get a repeat-run
count (the "full suite N times in a row" criterion on Android tickets); the
cause and the rules are in android/TESTING.md.

Each run: cold-boot the emulator, wait until adb and the system services have
answered several polls in a row, install both APKs, run `am instrument` for the
Major suite (the weekly class excluded exactly as the Gradle task excludes
it), then label the output. `--driver gradle` runs the literal Gradle command
instead, for comparing the two.

Needs the single emulator: no other Android ticket may be running. It builds
the APKs once, up front (`gradlew assembleDebug assembleDebugAndroidTest`).

Usage: uv run scripts/android_suite_loop.py [--runs N] [--driver instrument|gradle]
       [--expected-tests N] [--log-dir DIR] [--emulator-arg ARG ...]
Exit code: 0 every run passed, 1 a real test failed, 2 only infrastructure aborts.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
ANDROID_DIR = REPO_ROOT / "android"

PASSED = "passed"
TEST_FAILED = "test-failed"
INFRA_ABORT = "infra-abort"

# Patterns that mean the emulator, adb or the system server died, whatever
# else the output says. The first one found is the reason quoted in the summary.
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
    r"Execution failed for task ':app:wakeEmulatorForInstrumentedTests'",
)

GRADLEW = str(ANDROID_DIR / ("gradlew.bat" if os.name == "nt" else "gradlew"))
WIN_DETACHED_PROCESS = 0x00000008  # subprocess.DETACHED_PROCESS, which only exists on Windows
WIN_NEW_PROCESS_GROUP = 0x00000200  # subprocess.CREATE_NEW_PROCESS_GROUP, likewise

AVD = "medium_phone"
# Software rendering. On the AVD's default host-GPU backend (gfxstream over the
# host's Vulkan GPU) the system server hung inside a screen capture and was
# killed by its watchdog, and adb dropped; see android/TESTING.md.
GPU = "swangle_indirect"
APP_PACKAGE = "com.rigcheck.app"
RUNNER = f"{APP_PACKAGE}.test/{APP_PACKAGE}.CustomTestRunner"
# The Gradle task excludes this class (app/build.gradle.kts notClass); a raw
# `am instrument` has to say so itself or it runs against the offline app.
WEEKLY_CLASS = "com.rigcheck.app.ui.screens.PaywallScreenWeeklyTest"
WEEKLY_MARKER = "/data/local/tmp/rigcheck_weekly_mode"
APKS = (
    ANDROID_DIR / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk",
    ANDROID_DIR / "app" / "build" / "outputs" / "apk" / "androidTest" / "debug" / "app-debug-androidTest.apk",
)
SERVICES = ("input", "activity", "package", "window")


@dataclass
class Outcome:
    kind: str
    reason: str = ""
    tests: int | None = None


def classify_run(output: str, returncode: int, expected_tests: int | None = None) -> Outcome:
    """Label one finished run. An abort marker anywhere wins: a test that
    fails because the system server was dying says nothing about the app."""
    for marker in ABORT_MARKERS:
        found = re.search(marker, output)
        if found:
            line = next(ln for ln in output.splitlines() if found.group(0) in ln)
            return Outcome(INFRA_ABORT, line.strip()[:200])
    ok = re.search(r"OK \((\d+) tests?\)", output) or re.search(r"Finished (\d+) tests?", output)
    ran = re.search(r"Tests run: (\d+)", output)
    failed = "FAILURES!!!" in output or "There were failing tests" in output
    if failed:
        return Outcome(TEST_FAILED, "tests failed", int(ran.group(1)) if ran else None)
    if not ok:
        # Often our own "install of X failed" line: quote it so a bad APK isn't
        # mistaken for a dead emulator.
        first = next((ln.strip() for ln in output.splitlines() if ln.strip()), "")
        return Outcome(INFRA_ABORT, f"no result line in the output (starts: {first[:120]})" if first else "no output")
    count = int(ok.group(1))
    if returncode != 0:
        return Outcome(INFRA_ABORT, f"result line present but exit code {returncode}", count)
    if expected_tests is not None and count != expected_tests:
        return Outcome(TEST_FAILED, f"ran {count} tests, expected {expected_tests}", count)
    return Outcome(PASSED, tests=count)


@dataclass
class Report:
    outcomes: list[Outcome] = field(default_factory=list)

    @property
    def runs(self) -> int:
        return len(self.outcomes)

    def _count(self, kind: str) -> int:
        return sum(1 for o in self.outcomes if o.kind == kind)

    @property
    def passed(self) -> int:
        return self._count(PASSED)

    @property
    def test_failed(self) -> int:
        return self._count(TEST_FAILED)

    @property
    def infra_aborted(self) -> int:
        return self._count(INFRA_ABORT)

    @property
    def finished(self) -> int:
        return self.passed + self.test_failed

    @property
    def longest_pass_streak(self) -> int:
        """Longest run of passes. An abort neither adds to nor ends a streak
        (it says nothing about the app); a real test failure ends it."""
        best = current = 0
        for outcome in self.outcomes:
            if outcome.kind == PASSED:
                current += 1
                best = max(best, current)
            elif outcome.kind == TEST_FAILED:
                current = 0
        return best

    @property
    def exit_code(self) -> int:
        if self.test_failed:
            return 1
        return 2 if self.infra_aborted else 0

    def summary(self) -> str:
        lines = [
            f"{self.passed} of {self.runs} runs passed; {self.test_failed} failed a test; "
            f"{self.infra_aborted} aborted for infrastructure reasons "
            f"({self.finished} reached the end of the suite).",
            f"Longest streak of passes: {self.longest_pass_streak} (aborted runs neither extend nor end it).",
        ]
        for number, outcome in enumerate(self.outcomes, 1):
            if outcome.kind != PASSED:
                lines.append(f"  run {number}: {outcome.kind}: {outcome.reason}")
        return "\n".join(lines)


def run_loop(
    runs: int,
    *,
    restart: Callable[[], bool],
    run_once: Callable[[int], tuple[str, int]],
    expected_tests: int | None = None,
    restart_every: int = 1,
    out: Callable[[str], None] = print,
) -> Report:
    """`restart_every` is how many runs share one fresh emulator (1: restart
    before every run, the supported mode; 0: restart once, for measuring how
    long a warm emulator lasts). A run that aborts always forces a restart."""
    report = Report()
    needs_restart = True
    runs_on_this_emulator = 0
    for number in range(1, runs + 1):
        if needs_restart:
            out(f"== run {number} of {runs}: restarting the emulator")
            if not restart():
                outcome = Outcome(INFRA_ABORT, "the emulator did not come up ready")
            else:
                needs_restart, runs_on_this_emulator = False, 0
        else:
            out(f"== run {number} of {runs}: reusing the emulator")
        if not needs_restart:
            runs_on_this_emulator += 1
            output, code = run_once(number)
            outcome = classify_run(output, code, expected_tests)
            needs_restart = outcome.kind == INFRA_ABORT or (
                restart_every > 0 and runs_on_this_emulator >= restart_every
            )
        report.outcomes.append(outcome)
        detail = outcome.reason or (f"{outcome.tests} tests" if outcome.tests else "")
        out(f"== run {number}: {outcome.kind}" + (f" ({detail})" if detail else ""))
    out(report.summary())
    return report


# --- the real emulator and adb -------------------------------------------------


Adb = Callable[..., tuple[int, str]]


def not_ready_reason(adb: Adb) -> str | None:
    """None when the device is booted and every system service answers, else
    what is still missing. `sys.boot_completed` alone is not enough: right
    after it, services and the adb transport can still drop out."""
    code, text = adb("get-state")
    if code != 0 or text.strip() != "device":
        return f"adb state: {text.strip() or 'no answer'} (offline)"
    code, text = adb("shell", "getprop", "sys.boot_completed")
    if code != 0 or text.strip() != "1":
        return "boot not completed"
    for service in SERVICES:
        code, text = adb("shell", "service", "check", service)
        if code != 0 or "not found" in text or "found" not in text:
            return f"service {service}: {text.strip() or 'no answer'}"
    return None


def wait_until_ready(
    adb: Adb,
    *,
    consecutive: int = 3,
    timeout_s: float = 300,
    poll_s: float = 5,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
) -> bool:
    """True once `consecutive` polls in a row find the device ready; a bad
    poll restarts the count. False at the timeout."""
    deadline = now() + timeout_s
    streak = 0
    while now() < deadline:
        streak = streak + 1 if not_ready_reason(adb) is None else 0
        if streak >= consecutive:
            return True
        sleep(poll_s)
    return False


def find_sdk_tool(*relative: str) -> str:
    for var in ("ANDROID_SDK_ROOT", "ANDROID_HOME"):
        root = os.environ.get(var)
        if root:
            for suffix in (".exe", ""):
                candidate = Path(root, *relative[:-1], relative[-1] + suffix)
                if candidate.is_file():
                    return str(candidate)
    found = shutil.which(relative[-1])
    if found:
        return found
    raise RuntimeError(f"{relative[-1]} not found: set ANDROID_SDK_ROOT or ANDROID_HOME.")


def make_adb(adb_path: str, timeout_s: float = 60) -> Adb:
    def adb(*args: str, timeout: float | None = None) -> tuple[int, str]:
        try:
            proc = subprocess.run(
                [adb_path, *args], capture_output=True, text=True, errors="replace",
                timeout=timeout or timeout_s, env={**os.environ, "MSYS_NO_PATHCONV": "1"},
            )
        except subprocess.TimeoutExpired as exc:
            partial = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            return 124, f"{partial}\nsuite timed out after {timeout or timeout_s:.0f} s"
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    return adb


def emulator_command(emulator_path: str, *, avd: str, gpu: str = GPU, extra_args: list[str] | None = None) -> list[str]:
    return [emulator_path, "-avd", avd, "-no-snapshot", "-no-boot-anim", "-gpu", gpu, *(extra_args or [])]


def restart_emulator(
    adb: Adb, emulator_path: str, *, avd: str, gpu: str, extra_args: list[str], log_path: Path, settle_s: float
) -> bool:
    """Kill the running emulator (if any), cold-boot a fresh one, wait until it
    is steadily ready and let it settle. False if it never came up."""
    adb("emu", "kill")
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        _, devices = adb("devices")
        if "emulator-" not in devices:
            break
        time.sleep(2)
    else:
        return False
    time.sleep(5)  # let the old qemu process release the AVD's lock files
    # The emulator must outlive this script's console, and is left running when it exits.
    flags = {"creationflags": WIN_DETACHED_PROCESS | WIN_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    with open(log_path, "ab") as log:
        subprocess.Popen(
            emulator_command(emulator_path, avd=avd, gpu=gpu, extra_args=extra_args),
            stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, **flags,
        )
    adb("wait-for-device", timeout=240)
    if not wait_until_ready(adb, timeout_s=360):
        return False
    time.sleep(settle_s)
    if not_ready_reason(adb) is not None:
        return False
    adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
    adb("shell", "wm", "dismiss-keyguard")
    adb("shell", "svc", "power", "stayon", "true")
    return True


def instrument_once(adb: Adb, suite_timeout_s: float) -> tuple[str, int]:
    """Install both APKs on the (fresh) emulator and run the Major suite."""
    for apk in APKS:
        code, text = adb("install", "-r", str(apk), timeout=240)
        if code != 0 or "Success" not in text:
            return f"install of {apk.name} failed:\n{text}", code or 1
    adb("shell", "rm", "-f", WEEKLY_MARKER)
    code, text = adb(
        "shell", "am", "instrument", "-w", "-e", "notClass", WEEKLY_CLASS, RUNNER, timeout=suite_timeout_s
    )
    return text, code


def gradle_once(suite_timeout_s: float) -> tuple[str, int]:
    """The literal documented Gradle command, for comparison runs."""
    try:
        proc = subprocess.run(
            [GRADLEW, "-p", "android", "connectedDebugAndroidTest"], cwd=REPO_ROOT, capture_output=True,
            text=True, errors="replace", timeout=suite_timeout_s,
        )
    except subprocess.TimeoutExpired:
        return f"suite timed out after {suite_timeout_s:.0f} s", 124
    return (proc.stdout or "") + (proc.stderr or ""), proc.returncode


def build_apks() -> None:
    subprocess.run([GRADLEW, "-p", "android", "assembleDebug", "assembleDebugAndroidTest"], cwd=REPO_ROOT, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--driver", choices=("instrument", "gradle"), default="instrument")
    parser.add_argument("--expected-tests", type=int, default=None, help="fail a run that finishes with another count")
    parser.add_argument("--restart-every", type=int, default=1, help="runs per emulator boot (0: boot once); default 1")
    parser.add_argument("--avd", default=AVD)
    parser.add_argument("--gpu", default=GPU, help="emulator -gpu mode; 'host' reproduces the #127 aborts")
    parser.add_argument("--emulator-arg", action="append", default=[], help="extra emulator flag, e.g. -memory")
    parser.add_argument("--settle-s", type=float, default=20, help="pause after the emulator is steadily ready")
    parser.add_argument("--suite-timeout-s", type=float, default=2400)
    parser.add_argument("--log-dir", type=Path, default=ANDROID_DIR / "build" / "suite-loop")
    args = parser.parse_args(argv)
    if args.runs < 1:
        parser.error("--runs must be at least 1")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = args.log_dir / stamp
    log_dir.mkdir(parents=True, exist_ok=True)
    adb = make_adb(find_sdk_tool("platform-tools", "adb"))
    emulator = find_sdk_tool("emulator", "emulator")

    if args.driver == "instrument":
        subprocess.run([GRADLEW, "--stop"], cwd=REPO_ROOT)
        build_apks()

    def restart() -> bool:
        return restart_emulator(
            adb, emulator, avd=args.avd, gpu=args.gpu, extra_args=args.emulator_arg, log_path=log_dir / "emulator.log",
            settle_s=args.settle_s,
        )

    def run_once(number: int) -> tuple[str, int]:
        adb("logcat", "-c")
        output, code = (
            instrument_once(adb, args.suite_timeout_s) if args.driver == "instrument" else gradle_once(args.suite_timeout_s)
        )
        (log_dir / f"run-{number}.log").write_text(output, encoding="utf-8")
        # What the device said while it ran, kept for working out why a run
        # aborted; best effort, since a dead emulator answers nothing.
        _, logcat = adb("logcat", "-d", "-b", "all", "-t", "30000")
        _, meminfo = adb("shell", "cat", "/proc/meminfo")
        (log_dir / f"run-{number}.logcat.txt").write_text(logcat, encoding="utf-8")
        (log_dir / f"run-{number}.meminfo.txt").write_text(meminfo, encoding="utf-8")
        return output, code

    print(f"Logs: {log_dir}")
    report = run_loop(
        args.runs, restart=restart, run_once=run_once, expected_tests=args.expected_tests,
        restart_every=args.restart_every,
    )
    (log_dir / "summary.txt").write_text(report.summary() + "\n", encoding="utf-8")
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
