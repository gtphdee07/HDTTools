"""Decides and executes one platform's External run (ADR-0008); the
platform wrappers (e.g. web/test-external.ps1) are thin shells around this.

Usage: uv run scripts/external_wrapper.py --platform web --tests-dir web/src/external
           --cwd web [--skip] -- npm run test:external

Only stale surfaces in the platform's dependency chain run. Fresh ones are
left alone, `--skip` records `skipped` (which never advances freshness), a
stale surface with no test tagged `[surface]` is recorded as a fail rather
than a false pass, and each run surface is recorded pass or fail. The test
command receives the surfaces to run in EXTERNAL_SURFACES (comma-separated).

A surface with a declared `max_paid_calls` in the manifest is gated by
scripts/paid_call_budget.py: the owner is asked to confirm before it runs
(naming the surface and its call count), declining records it `skipped`
(same as never advancing freshness), and a confirmation that would push the
run over its declared ceiling aborts instead of prompting (BudgetExceeded).
Free surfaces (max_paid_calls 0, the default) are never gated. The ceiling
defaults to the sum of the in-scope surfaces' own declared max_paid_calls,
but `--max-paid-calls` (mirroring scripts/scan_proxy_release.py's and
scripts/android_release.py's own `-MaxPaidCalls` convention) sets an
independent, operator-chosen cap instead - useful since a surface's
declared cost is a self-reported number nothing here independently verifies
against the calls its suite actually makes.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import external_freshness  # noqa: E402
import record_external_result  # noqa: E402
from paid_call_budget import BudgetExceeded, PaidCallBudget  # noqa: E402

TAG_FORMATS = {
    "bracket": lambda surface: f"[{surface}]",
    "marker": lambda surface: f"mark.{surface}",
}


def execute_plan(verdicts, *, skip, has_tests, run_tests, record, out=print, paid_calls=None, budget=None) -> int:
    for v in verdicts:
        reasons = f": {'; '.join(v.reasons)}" if v.reasons else ""
        out(f"{v.surface} - {v.state}{reasons}")

    stale = [v for v in verdicts if v.blocking]
    if not stale:
        out("No stale surfaces; nothing to run.")
        return 0

    if skip:
        for v in stale:
            record(v.surface, "skipped", v.versions)
        out(f"Recorded skipped for: {', '.join(v.surface for v in stale)}. They remain stale.")
        return 0

    untested = [v for v in stale if not has_tests(v.surface)]
    for v in untested:
        out(f"No external tests tagged [{v.surface}]; recording fail.")
        record(v.surface, "fail", v.versions)
    runnable = [v for v in stale if v not in untested]
    if not runnable:
        return 1

    paid_calls = paid_calls or {}
    to_run = []
    for v in runnable:
        cost = paid_calls.get(v.surface, 0)
        if cost <= 0:
            to_run.append(v)
            continue
        try:
            proceed = budget.confirm_and_spend(f"External suite: {v.surface}", cost)
        except BudgetExceeded as exc:
            out(f"Aborting: {exc}")
            return 1
        if proceed:
            to_run.append(v)
        else:
            out(f"Skipping {v.surface} (declined).")
            record(v.surface, "skipped", v.versions)

    if not to_run:
        return 1

    code = run_tests([v.surface for v in to_run])
    outcome = "pass" if code == 0 else "fail"
    for v in to_run:
        record(v.surface, outcome, v.versions)
    if (untested or len(to_run) < len(runnable)) and code == 0:
        return 1
    return code


def tagged_in(tests_dir: Path, glob: str = "*.external.test.ts", tag=TAG_FORMATS["bracket"]):
    texts = [p.read_text(encoding="utf-8") for p in tests_dir.glob(glob)]
    return lambda surface: any(tag(surface) in t for t in texts)


def paid_calls_for(manifest: dict, only: list[str]) -> dict[str, int]:
    return {n: manifest["surfaces"][n].get("max_paid_calls", 0) for n in only}


def budget_for(paid_calls: dict[str, int], max_calls: int | None = None) -> PaidCallBudget | None:
    """None when nothing in scope is paid - the free-surface case `execute_plan`
    never needs to consult a budget for. `max_calls` set explicitly (the
    wrapper's own `--max-paid-calls`) is an independent, operator-chosen
    ceiling; left unset, it defaults to the sum of the declared costs it is
    about to gate - a number nothing here independently verifies against the
    calls a surface's suite actually makes, so the explicit override exists
    precisely to let a caller set a real, separately-chosen cap instead."""
    if not any(paid_calls.values()):
        return None
    return PaidCallBudget(max_calls=max_calls if max_calls is not None else sum(paid_calls.values()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--tests-dir", required=True, type=Path)
    parser.add_argument("--cwd", required=True, type=Path)
    parser.add_argument("--skip", action="store_true")
    parser.add_argument("--test-glob", default="*.external.test.ts")
    parser.add_argument("--tag-style", choices=sorted(TAG_FORMATS), default="bracket")
    parser.add_argument(
        "--max-paid-calls", type=int, default=None,
        help="Declared ceiling for paid calls this run may confirm (default: the sum of the "
        "in-scope surfaces' own manifest max_paid_calls - pass this to set an independent, "
        "operator-chosen cap instead of trusting that sum as its own ceiling).",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command

    manifest = external_freshness.load_manifest()
    only = external_freshness.surfaces_for_platform(manifest, args.platform)
    verdicts = external_freshness.evaluate(
        manifest,
        external_freshness.load_status(),
        external_freshness.GitHistory(),
        external_freshness.fetch_publish_times,
        only,
    )

    paid_calls = paid_calls_for(manifest, only)
    budget = budget_for(paid_calls, args.max_paid_calls)

    def run_tests(surfaces: list[str]) -> int:
        exe = shutil.which(command[0]) or command[0]
        env = {**os.environ, "EXTERNAL_SURFACES": ",".join(surfaces)}
        return subprocess.run([exe, *command[1:]], cwd=args.cwd, env=env).returncode

    return execute_plan(
        verdicts,
        skip=args.skip,
        has_tests=tagged_in(args.tests_dir, args.test_glob, TAG_FORMATS[args.tag_style]),
        run_tests=run_tests,
        record=lambda surface, outcome, versions: record_external_result.record_surface(
            surface, outcome, versions=versions
        ),
        paid_calls=paid_calls,
        budget=budget,
    )


if __name__ == "__main__":
    raise SystemExit(main())
