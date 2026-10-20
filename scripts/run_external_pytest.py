"""Runs the Python External suite via pytest, narrowed to the surfaces the
wrapper passes in EXTERNAL_SURFACES (comma-separated) by matching each
surface's own pytest marker (ADR-0008: "marker for pytest"). Unset runs
every external test.

When the wrapper sets EXTERNAL_RESULTS_FILE, pytest also writes JUnit XML
there, with each test's surface as a `surface` property
(external_surface_plugin), so the wrapper can record each surface from its
own tests.

Invoked by test-external.ps1 the same way src/external/run.ts is invoked
by the TS platforms' npm run test:external.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from external_surface_plugin import marker_name  # noqa: E402


def command(surfaces: list[str], results_file: str | None) -> list[str]:
    expr = "external" if not surfaces else "external and (" + " or ".join(marker_name(s) for s in surfaces) + ")"
    cmd = [sys.executable, "-m", "pytest", "-m", expr, "-p", "external_surface_plugin"]
    if results_file:
        cmd.append(f"--junitxml={results_file}")
    return [*cmd, "tests"]


def main() -> int:
    surfaces = [s for s in os.environ.get("EXTERNAL_SURFACES", "").split(",") if s]
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(filter(None, [str(SCRIPTS), os.environ.get("PYTHONPATH")]))}
    return subprocess.run(command(surfaces, os.environ.get("EXTERNAL_RESULTS_FILE")), env=env).returncode


if __name__ == "__main__":
    sys.exit(main())
