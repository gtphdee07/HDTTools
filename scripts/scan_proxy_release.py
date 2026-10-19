"""One-command Worker release run (#62, spec #51): the offline (Major)
suite, the stale surface suites, the direct-provider release suite and
the through-the-Worker weekly suite (which also redeploys the Worker) -
in that order, stopping on the first failure.

Each paid old suite is gated by a shared paid-call budget
(scripts/paid_call_budget.py): the owner is asked to confirm before it
runs, and the run aborts instead of prompting once the declared maximum
would be exceeded. The same budget module is reusable by other paid
surfaces (the Anthropic surface, #37).

Entry point: workers/scan-proxy/release.ps1.

After the stale surfaces are re-run, the External release gate
(scripts/external_gate.py, ADR-0008) must find every surface in the Worker's
chain fresh before the release and weekly suites run (the weekly suite deploys
the Worker). `--force --reason TEXT` goes past a blocked gate; the reason is
recorded and shown on the dashboard until each surface's next real pass.

Usage: uv run scripts/scan_proxy_release.py [--max-paid-calls N] [--force --reason TEXT]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import external_gate  # noqa: E402
from paid_call_budget import PaidCallBudget  # noqa: E402
from release_steps import default_run_command, powershell_command, run_paid_step, run_step, stale_surfaces  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
PROXY_DIR = REPO_ROOT / "workers" / "scan-proxy"
PLATFORM = "scan-proxy"

# Declared ceiling for one release run: the release suite's 1 billed Claude
# call plus the weekly suite's 2 (workers/scan-proxy/TESTING.md). No headroom
# on purpose - a surprise third paid step should abort, not spend quietly.
DEFAULT_MAX_PAID_CALLS = 3

OFFLINE_STEP = {
    "name": "offline suite (Major)",
    "command": ["npm", "--prefix", "workers/scan-proxy", "test"],
    "cwd": REPO_ROOT,
}
EXTERNAL_STEP = {
    "name": "External suite (stale surfaces)",
    "command": powershell_command("test-external.ps1"),
    "cwd": PROXY_DIR,
}
RELEASE_STEP = {
    "name": "direct-provider release suite (1 billed Claude call)",
    "command": powershell_command("test-release.ps1"),
    "cwd": PROXY_DIR,
    "paid_calls": 1,
}
WEEKLY_STEP = {
    "name": "through-the-Worker weekly suite (redeploys the Worker; 2 billed Claude calls)",
    "command": powershell_command("test-weekly.ps1"),
    "cwd": PROXY_DIR,
    "paid_calls": 2,
}


def run(
    argv: list[str] | None = None,
    *,
    budget: PaidCallBudget | None = None,
    run_command=default_run_command,
    stale: Callable[[], list[str]] | None = None,
    gate=None,
    out: Callable[[str], None] = print,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-paid-calls", type=int, default=DEFAULT_MAX_PAID_CALLS)
    external_gate.add_force_arguments(parser)
    args = parser.parse_args(argv)
    reason = external_gate.force_reason(args, parser, os.environ)
    budget = budget or PaidCallBudget(max_calls=args.max_paid_calls, out=out)

    out(f"Worker release run (paid-call budget: {args.max_paid_calls})")

    # The weekly suite redeploys the Worker through `npm run deploy`, which runs the gate again;
    # a forced run hands its reason down so that deploy is not asked twice.
    with external_gate.exported_force(reason):
        return _run_steps(budget, run_command, stale, gate or external_gate.gate, reason, out)


def _run_steps(budget, run_command, stale, gate, reason, out) -> int:
    code = run_step(OFFLINE_STEP, run_command=run_command, out=out)
    if code != 0:
        return code

    stale_names = stale() if stale is not None else stale_surfaces([PLATFORM])
    if stale_names:
        out(f"Stale surfaces: {', '.join(stale_names)}; running the External suite.")
        code = run_step(EXTERNAL_STEP, run_command=run_command, out=out)
        if code != 0:
            return code
    else:
        out("No stale surfaces; skipping the External suite.")

    # The External release gate (ADR-0008): every surface in the chain must be fresh before the
    # steps that deploy the Worker. A surface the External step skipped or could not refresh stops it here.
    code = gate([PLATFORM], force_reason=reason, out=out)
    if code != 0:
        out("Worker release stopped by the External release gate.")
        return code

    for step in (RELEASE_STEP, WEEKLY_STEP):
        code = run_paid_step(step, budget=budget, run_command=run_command, out=out)
        if code is not None:
            return code

    out("Worker release run complete.")
    return 0


def main(argv: list[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
