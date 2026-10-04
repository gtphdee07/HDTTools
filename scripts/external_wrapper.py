"""Decides and executes one platform's External run (ADR-0008); the
platform wrappers (e.g. web/test-external.ps1) are thin shells around this.

Usage: uv run scripts/external_wrapper.py --platform web --tests-dir web/src/external
           --cwd web [--skip] -- npm run test:external

Only stale surfaces in the platform's dependency chain run. Fresh ones are
left alone, `--skip` records `skipped` (which never advances freshness), a
stale surface with no test tagged `[surface]` is recorded as a fail rather
than a false pass, and each run surface is recorded pass or fail. The test
command receives the surfaces to run in EXTERNAL_SURFACES (comma-separated).
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


def execute_plan(verdicts, *, skip, has_tests, run_tests, record, out=print) -> int:
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

    code = run_tests([v.surface for v in runnable])
    outcome = "pass" if code == 0 else "fail"
    for v in runnable:
        record(v.surface, outcome, v.versions)
    if untested and code == 0:
        return 1
    return code


def tagged_in(tests_dir: Path):
    texts = [p.read_text(encoding="utf-8") for p in tests_dir.glob("*.external.test.ts")]
    return lambda surface: any(f"[{surface}]" in t for t in texts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--tests-dir", required=True, type=Path)
    parser.add_argument("--cwd", required=True, type=Path)
    parser.add_argument("--skip", action="store_true")
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

    def run_tests(surfaces: list[str]) -> int:
        exe = shutil.which(command[0]) or command[0]
        env = {**os.environ, "EXTERNAL_SURFACES": ",".join(surfaces)}
        return subprocess.run([exe, *command[1:]], cwd=args.cwd, env=env).returncode

    return execute_plan(
        verdicts,
        skip=args.skip,
        has_tests=tagged_in(args.tests_dir),
        run_tests=run_tests,
        record=lambda surface, outcome, versions: record_external_result.record_surface(
            surface, outcome, versions=versions
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
