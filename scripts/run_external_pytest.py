"""Runs the Python External suite via pytest, narrowed to the surfaces the
wrapper passes in EXTERNAL_SURFACES (comma-separated) by matching each
surface's own pytest marker (ADR-0008: "marker for pytest"). Unset runs
every external test.

Invoked by test-external.ps1 the same way src/external/run.ts is invoked
by the TS platforms' npm run test:external.
"""

from __future__ import annotations

import os
import subprocess
import sys

surfaces = [s for s in os.environ.get("EXTERNAL_SURFACES", "").split(",") if s]
expr = "external" if not surfaces else "external and (" + " or ".join(surfaces) + ")"

sys.exit(subprocess.run([sys.executable, "-m", "pytest", "-m", expr, "tests"]).returncode)
