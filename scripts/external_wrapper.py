"""Decides and executes one platform's External run (ADR-0008); the
platform wrappers (e.g. web/test-external.ps1) are thin shells around this.

Usage: uv run scripts/external_wrapper.py --platform web --tests-dir web/src/external
           --cwd web [--skip] -- npm run test:external

A wrapper acts only on the surfaces it owns (the manifest's `owner`, #142). A
stale surface in its chain that another platform owns is reported with the
script that runs it, and is neither run, guarded nor recorded here: its tests
live in the owner's tests directory, so a "no tests tagged" fail from this
wrapper would be false. A manifest with a surface that has no owner, or more
than one, stops the run before anything is run or recorded.

Only stale surfaces in the platform's dependency chain run. Fresh ones are
left alone, `--skip` records `skipped` (which never advances freshness), a
stale surface with no test tagged `[surface]` is recorded as a fail rather
than a false pass, and each run surface is recorded pass or fail. The test
command receives the surfaces to run in EXTERNAL_SURFACES (comma-separated)
and a path in EXTERNAL_RESULTS_FILE to write its JUnit XML to.

Each surface is decided from its own tagged tests in that file, not from the
run's single exit code: it passes only if none of its tests failed and at
least one passed, so one surface's failure never marks another failed and a
surface with nothing run is not a pass. The exit code decides every surface
only when there is no per-test data (the runner wrote nothing usable), or
when it is non-zero yet no tagged test failed (a failure nobody can be blamed
for, e.g. a suite that would not load).

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
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import external_freshness  # noqa: E402
import record_external_result  # noqa: E402
from external_surface_plugin import marker_name  # noqa: E402
from paid_call_budget import BudgetExceeded, PaidCallBudget  # noqa: E402

TAG_FORMATS = {
    "bracket": lambda surface: f"[{surface}]",
    "marker": lambda surface: f"mark.{marker_name(surface)}",
}


# Each platform's wrapper script, relative to the repo root, for the "run <script>" note.
WRAPPER_SCRIPTS = {
    "web": r"web\test-external.ps1",
    "scan-proxy": r"workers\scan-proxy\test-external.ps1",
    "core": "test-external.ps1",
}


def foreign_owners(manifest: dict, platform: str) -> dict[str, str]:
    """The surfaces in `platform`'s dependency chain that another platform's wrapper owns, with
    their owners. This wrapper reports them when stale but neither runs nor records them."""
    surfaces = manifest["surfaces"]
    return {
        n: surfaces[n]["owner"]
        for n in external_freshness.surfaces_for_platform(manifest, platform)
        if surfaces[n].get("owner") != platform
    }


def execute_plan(
    verdicts, *, skip, has_tests, run_tests, record, out=print, paid_calls=None, budget=None, read_results=None,
    owned_elsewhere=None,
) -> int:
    owned_elsewhere = owned_elsewhere or {}
    for v in verdicts:
        reasons = f": {'; '.join(v.reasons)}" if v.reasons else ""
        out(f"{v.surface} - {v.state}{reasons}")
        if v.blocking and v.surface in owned_elsewhere:
            owner = owned_elsewhere[v.surface]
            script = WRAPPER_SCRIPTS.get(owner)
            how = f"run {script}" if script else f"run the {owner} External wrapper"
            out(f"{v.surface} is owned by {owner}: {how}. It is not run or recorded here.")

    stale = [v for v in verdicts if v.blocking and v.surface not in owned_elsewhere]
    if not stale:
        if any(v.blocking for v in verdicts):
            out("No stale surfaces of this wrapper's own; nothing to run here.")
        else:
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
    results = read_results([v.surface for v in to_run]) if read_results else None
    if results is not None and code != 0 and not any(c.failed for c in results.values()):
        out("The run failed but no tagged test did; recording every surface as failed.")
        results = None
    all_passed = True
    for v in to_run:
        if results is None:
            outcome = "pass" if code == 0 else "fail"
        else:
            counts = results.get(v.surface, Counts())
            outcome = "pass" if counts.passed > 0 and counts.failed == 0 else "fail"
            if counts.passed + counts.failed == 0:
                out(f"No tests tagged [{v.surface}] ran; recording fail.")
        record(v.surface, outcome, v.versions)
        all_passed = all_passed and outcome == "pass"
    if code == 0 and (untested or len(to_run) < len(runnable) or not all_passed):
        return 1
    return code


@dataclass(frozen=True)
class Counts:
    passed: int = 0
    failed: int = 0
    skipped: int = 0


def surface_results(xml_text: str, surfaces: list[str], tag=TAG_FORMATS["bracket"]) -> dict[str, Counts] | None:
    """Per-surface test counts from a runner's JUnit XML (vitest, node --test and
    pytest all write it). A testcase belongs to a surface when its name, or any
    enclosing suite's, carries the surface's tag, or when it has a `surface`
    property naming it (how the pytest plugin tags marker-style tests). None when
    the XML is unusable or holds no testcase at all, so the caller falls back to
    the exit code."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None
    totals: dict[str, Counter] = {}
    seen = 0

    def walk(node, names):
        nonlocal seen
        for child in node:
            if child.tag == "testsuite":
                walk(child, [*names, child.get("name", "")])
            elif child.tag == "testcase":
                seen += 1
                text = " ".join([*names, child.get("classname", ""), child.get("name", "")])
                props = {p.get("value") for p in child.iter("property") if p.get("name") == "surface"}
                if child.find("failure") is not None or child.find("error") is not None:
                    kind = "failed"
                elif child.find("skipped") is not None:
                    kind = "skipped"
                else:
                    kind = "passed"
                for s in surfaces:
                    if tag(s) in text or s in props:
                        totals.setdefault(s, Counter())[kind] += 1

    walk(root, [root.get("name", "")] if root.tag == "testsuite" else [])
    if not seen:
        return None
    return {s: Counts(**c) for s, c in totals.items()}


def read_results_file(path: Path, surfaces: list[str], tag=TAG_FORMATS["bracket"]) -> dict[str, Counts] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return surface_results(text, surfaces, tag)


def tagged_in(tests_dir: Path, glob: str = "*.external.test.ts", tag=TAG_FORMATS["bracket"]):
    texts = [p.read_text(encoding="utf-8") for p in tests_dir.glob(glob)]

    def has_tag(surface: str) -> bool:
        # A tag ending in a name character must not be the start of a longer one:
        # "mark.anthropic" is not found in "mark.anthropic_python".
        wanted = tag(surface)
        pattern = re.escape(wanted) + (r"(?!\w)" if wanted[-1].isalnum() or wanted[-1] == "_" else "")
        return any(re.search(pattern, t) for t in texts)

    return has_tag


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


def main(
    argv: list[str] | None = None, *, manifest=None, status=None, git=None, registry=None,
    has_tests=None, run_tests=None, record=None, out=print,
) -> int:
    """The keyword arguments replace the manifest, status file, git, registries, test lookup, test
    runner and recorder, so the whole wrapper can be run against fakes."""
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

    manifest = external_freshness.load_manifest() if manifest is None else manifest
    problems = external_freshness.owner_problems(manifest)
    if problems:
        out("The surface manifest is not usable; nothing was run or recorded:")
        for problem in problems:
            out(f"  {problem}")
        return 1

    only = external_freshness.surfaces_for_platform(manifest, args.platform)
    owned_elsewhere = foreign_owners(manifest, args.platform)
    verdicts = external_freshness.evaluate(
        manifest,
        status if status is not None else external_freshness.load_status(),
        git or external_freshness.GitHistory(),
        registry or external_freshness.fetch_publish_times,
        only,
    )

    paid_calls = paid_calls_for(manifest, [n for n in only if n not in owned_elsewhere])
    budget = budget_for(paid_calls, args.max_paid_calls)

    tag = TAG_FORMATS[args.tag_style]
    with tempfile.TemporaryDirectory(prefix="hdttools-external-") as tmp:
        results_file = Path(tmp) / "results.xml"

        def run_command(surfaces: list[str]) -> int:
            exe = shutil.which(command[0]) or command[0]
            env = {**os.environ, "EXTERNAL_SURFACES": ",".join(surfaces), "EXTERNAL_RESULTS_FILE": str(results_file)}
            return subprocess.run([exe, *command[1:]], cwd=args.cwd, env=env).returncode

        return execute_plan(
            verdicts,
            skip=args.skip,
            has_tests=has_tests or tagged_in(args.tests_dir, args.test_glob, tag),
            run_tests=run_tests or run_command,
            record=record
            or (
                lambda surface, outcome, versions: record_external_result.record_surface(
                    surface, outcome, versions=versions
                )
            ),
            out=out,
            paid_calls=paid_calls,
            budget=budget,
            read_results=lambda surfaces: read_results_file(results_file, surfaces, tag),
            owned_elsewhere=owned_elsewhere,
        )


if __name__ == "__main__":
    raise SystemExit(main())
