"""The Worker deploy, behind the External release gate (ADR-0008, #43).

`npm run deploy` in workers/scan-proxy runs this: it checks that every surface in
the scan-proxy chain is fresh (scripts/external_gate.py) and only then runs
`wrangler deploy`. A stale chain refuses the deploy. To deploy anyway, for
example to put changed Worker code in place so its External suite can test it,
give a reason:

    npm run deploy -- --force --reason "deploying changed Worker code to test it"

The reason is recorded on each blocking surface and shown on the dashboard as an
overridden gate until its next real pass. Any other argument goes on to
`wrangler deploy` (for example `npm run deploy -- --dry-run`). A release run that was itself forced
exports its reason (EXTERNAL_GATE_FORCE_REASON), so the deploy inside it does not
need asking twice.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent))
import external_gate  # noqa: E402
from release_steps import default_run_command  # noqa: E402

PROXY_DIR = Path(__file__).resolve().parent.parent / "workers" / "scan-proxy"
PLATFORM = "scan-proxy"
# --no-install: use the project's wrangler, never fetch whichever version npx finds.
DEPLOY_COMMAND = ["npx", "--no-install", "wrangler", "deploy"]


def run(
    argv: list[str] | None = None,
    *,
    gate=None,
    run_command=default_run_command,
    environ: Mapping[str, str] | None = None,
    out: Callable[[str], None] = print,
) -> int:
    # allow_abbrev=False: a wrangler flag such as --re must not be read as --reason.
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False
    )
    external_gate.add_force_arguments(parser)
    args, wrangler_args = parser.parse_known_args(argv)  # anything else goes on to `wrangler deploy`
    reason = external_gate.force_reason(args, parser, os.environ if environ is None else environ)

    code = (gate or external_gate.gate)([PLATFORM], force_reason=reason, out=out)
    if code != 0:
        out("Worker deploy refused by the External release gate.")
        return code
    return run_command([*DEPLOY_COMMAND, *wrangler_args], cwd=PROXY_DIR).returncode


def main(argv: list[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
