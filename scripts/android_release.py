"""One-command Android release run (#63, spec #51): the JVM (Minor)
suite, the instrumented (device) suite, the stale surfaces in Android's
chain (including the Worker's, since android/test-weekly.ps1 depends on
a freshly deployed Worker) and the old weekly suite - in that order,
stopping on the first failure. A missing device/emulator fails the run
outright; it is never silently skipped.

The old weekly suite both redeploys the Worker and makes real Claude
calls, so it is gated by the shared paid-call budget
(scripts/paid_call_budget.py): the owner is asked to confirm, naming
both the deploy and the spend, before it runs, and the run aborts
instead of prompting once the declared maximum would be exceeded.

Entry point: android/release.ps1.

Usage: uv run scripts/android_release.py [--max-paid-calls N]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paid_call_budget import PaidCallBudget  # noqa: E402
from release_steps import default_run_command, powershell_command, run_paid_step, run_step, stale_surfaces  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
ANDROID_DIR = REPO_ROOT / "android"
PLATFORMS = ["android", "scan-proxy"]  # Android's chain includes the Worker's surfaces

# Declared ceiling for one release run: the old weekly suite's 2 real Claude
# calls (android/TESTING.md). No headroom on purpose.
DEFAULT_MAX_PAID_CALLS = 2

# Windows has no extensionless "gradlew" shim (only gradlew.bat). Built as an
# absolute path, not "android/gradlew.bat": that relative form only resolves
# through release_steps.default_run_command's shutil.which call when this
# process's own cwd happens to be REPO_ROOT, but android/TESTING.md documents
# running release.ps1 from android/ itself - confirmed by hand that a relative
# forward-slash path then fails to launch at all (WinError 2), even though the
# subprocess's cwd= is set correctly. An absolute path resolves regardless of
# this process's cwd.
GRADLEW = str(ANDROID_DIR / ("gradlew.bat" if os.name == "nt" else "gradlew"))

JVM_STEP = {
    "name": "JVM tests (Minor)",
    "command": [GRADLEW, "-p", "android", "testDebugUnitTest"],
    "cwd": REPO_ROOT,
}
INSTRUMENTED_STEP = {
    "name": "instrumented tests (device)",
    "command": [GRADLEW, "-p", "android", "connectedDebugAndroidTest"],
    "cwd": REPO_ROOT,
}
# Runs the Worker's own External suite (--platform scan-proxy, hard-coded
# inside test-external.ps1), the only runner that exists today. This covers
# revenuecat-rest (platforms ["scan-proxy", "android"], currently "active")
# correctly, but android-only surfaces (revenuecat-android-sdk,
# google-play-billing - currently "planned", so stale_surfaces() can't
# report them as blocking yet) have no Android-side runner at all; #39/#40
# need to add one before this step can cover them once they go "active".
EXTERNAL_STEP = {
    "name": "Worker External suite (stale surfaces in Android's chain)",
    "command": powershell_command("test-external.ps1"),
    "cwd": REPO_ROOT / "workers" / "scan-proxy",
}
WEEKLY_STEP = {
    "name": "old weekly suite (redeploys the Worker; 2 real Claude calls, ~$0.02)",
    "command": powershell_command("test-weekly.ps1"),
    "cwd": ANDROID_DIR,
    "paid_calls": 2,
}


def _default_adb() -> str:
    found = shutil.which("adb")
    if found:
        return found
    for var in ("ANDROID_SDK_ROOT", "ANDROID_HOME"):
        root = os.environ.get(var)
        if root:
            candidate = Path(root) / "platform-tools" / ("adb.exe" if os.name == "nt" else "adb")
            if candidate.is_file():
                return str(candidate)
    raise RuntimeError("adb not found on PATH and neither ANDROID_SDK_ROOT nor ANDROID_HOME is set.")


def connected_devices(*, adb: str | None = None, run_command=subprocess.run) -> list[str]:
    """Device/emulator serials reported ready by `adb devices` (excludes
    "unauthorized"/"offline" entries, which can't run tests)."""
    exe = adb or _default_adb()
    proc = run_command([exe, "devices"], capture_output=True, text=True)
    lines = proc.stdout.splitlines()[1:] if proc.stdout else []
    return [line.split("\t")[0] for line in lines if line.strip().endswith("\tdevice")]


def run(
    argv: list[str] | None = None,
    *,
    budget: PaidCallBudget | None = None,
    run_command=default_run_command,
    devices: Callable[[], list[str]] | None = None,
    stale: Callable[[], list[str]] | None = None,
    out: Callable[[str], None] = print,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-paid-calls", type=int, default=DEFAULT_MAX_PAID_CALLS)
    args = parser.parse_args(argv)
    budget = budget or PaidCallBudget(max_calls=args.max_paid_calls, out=out)

    out(f"Android release run (paid-call budget: {args.max_paid_calls})")

    code = run_step(JVM_STEP, run_command=run_command, out=out)
    if code != 0:
        return code

    try:
        connected = devices() if devices is not None else connected_devices()
    except RuntimeError as exc:
        out(f"Could not check for a device ({exc}); failing the release run.")
        return 1
    if not connected:
        out("No device or emulator attached (`adb devices` found none); failing the release run.")
        return 1
    out(f"Device(s) attached: {', '.join(connected)}")

    code = run_step(INSTRUMENTED_STEP, run_command=run_command, out=out)
    if code != 0:
        return code

    stale_names = stale() if stale is not None else stale_surfaces(PLATFORMS)
    if stale_names:
        out(f"Stale surfaces: {', '.join(stale_names)}; running the Worker's External suite.")
        code = run_step(EXTERNAL_STEP, run_command=run_command, out=out)
        if code != 0:
            return code
    else:
        out("No stale surfaces; skipping the Worker External suite.")

    code = run_paid_step(WEEKLY_STEP, budget=budget, run_command=run_command, out=out)
    if code is not None:
        return code

    out("Android release run complete.")
    return 0


def main(argv: list[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
