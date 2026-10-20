"""Android's session-end command (#133, spec #51): the device-free checks that end an Android
ticket, in this order, stopping at the first one that fails:

  1. the JVM unit tests (and the JVM coverage report they leave);
  2. the decision-logic coverage floor over that report (#130, android/coverage-logic.toml);
  3. detekt (the dead-code sweep; offline).

About 45 s warm. No emulator or device is touched. The instrumented tests are not part of it:
the test planner (scripts/test_planner.py) lists the ones a diff needs next to this command.

Usage: uv run scripts/android_session_end.py
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_steps import default_run_command  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
ANDROID_DIR = REPO_ROOT / "android"

# Absolute for the same reason as android_release.GRADLEW: a relative wrapper path only resolves
# from the repo root, and this command may be started from anywhere.
GRADLEW = str(ANDROID_DIR / ("gradlew.bat" if os.name == "nt" else "gradlew"))

STEPS = [
    {
        "name": "JVM unit tests",
        "command": [GRADLEW, "-p", "android", "testDebugUnitTest", "createDebugUnitTestCoverageReport"],
        "cwd": REPO_ROOT,
    },
    {
        "name": "decision-logic coverage floor",
        "command": [sys.executable, str(REPO_ROOT / "scripts" / "coverage_gate.py"), "--android-logic"],
        "cwd": REPO_ROOT,
    },
    {
        "name": "detekt",
        "command": [GRADLEW, "-p", "android", "detekt"],
        "cwd": REPO_ROOT,
    },
]


def run(argv: list[str] | None = None, *, run_command=default_run_command, out: Callable[[str], None] = print) -> int:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args(argv)

    for number, step in enumerate(STEPS, 1):
        out(f"Android session end, step {number} of {len(STEPS)}: {step['name']}")
        code = run_command(step["command"], cwd=step["cwd"]).returncode
        if code != 0:
            out(f"Android session end: {step['name']} failed (exit {code}); stopping.")
            return code
    out("Android session-end run complete.")
    return 0


def main(argv: list[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
