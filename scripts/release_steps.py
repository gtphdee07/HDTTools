"""Small shared pieces for the per-context release commands (#62, #63):
running a step and reporting failure consistently, and checking which
External surfaces are stale across a release's platform chain.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import external_freshness as ef  # noqa: E402
from paid_call_budget import BudgetExceeded, PaidCallBudget  # noqa: E402


def powershell_command(script: str) -> list[str]:
    return ["powershell", "-NoProfile", "-File", script]


def default_run_command(command: list[str], cwd) -> subprocess.CompletedProcess:
    """The real runner a release script uses by default (tests inject their own
    fake instead). Resolves command[0] through PATH/PATHEXT (`shutil.which`)
    before invoking, so a bare name like "npm" finds Windows' npm.CMD shim
    without shell=True - the same technique external_wrapper.py's run_tests
    already uses. Only safe for a command whose first token has no path
    separator; a relative script path (e.g. an OS-specific gradlew wrapper)
    must already be resolved by the caller, since shutil.which's lookup for a
    path containing a separator is relative to this process's own cwd, not
    the `cwd` given here for the child process."""
    exe = shutil.which(command[0]) or command[0]
    return subprocess.run([exe, *command[1:]], cwd=cwd)


def stale_surfaces(platforms: list[str], *, evaluate: Callable[[], list] | None = None) -> list[str]:
    """Surfaces in any of the given platforms' chains that are stale (blocking)."""
    if evaluate is not None:
        verdicts = evaluate()
    else:
        manifest = ef.load_manifest()
        only = sorted({n for p in platforms for n in ef.surfaces_for_platform(manifest, p)})
        verdicts = ef.evaluate(manifest, ef.load_status(), ef.GitHistory(), ef.fetch_publish_times, only)
    return [v.surface for v in verdicts if v.blocking]


def run_step(step: dict, *, run_command=default_run_command, out: Callable[[str], None] = print) -> int:
    code = run_command(step["command"], cwd=step["cwd"]).returncode
    if code != 0:
        out(f"{step['name']} failed (exit {code}); stopping the release run.")
    return code


def run_paid_step(
    step: dict, *, budget: PaidCallBudget, run_command=default_run_command, out: Callable[[str], None] = print
) -> int | None:
    """Confirms a paid step against the shared budget, then runs it. Returns
    an exit code if the release should stop (the budget was exceeded, or the
    step failed), or None if it should continue (declined, or passed)."""
    try:
        proceed = budget.confirm_and_spend(step["name"], step["paid_calls"])
    except BudgetExceeded as exc:
        out(f"Aborting release: {exc}")
        return 1
    if not proceed:
        out(f"Skipping {step['name']} (declined).")
        return None
    code = run_step(step, run_command=run_command, out=out)
    return code if code != 0 else None
