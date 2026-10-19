"""Cross-platform coverage gate, run at release time (roadmap item #9).

Reports real coverage for all four RigCheck platforms from each one's own
native coverage tooling, and enforces a baseline-floor threshold for the
platforms that have both a real coverage baseline and a real release
event today (Android, Python/Streamlit, scan-proxy). Web has no release
event yet (see NEXT_STEPS.md's "Deliberately not on this list" - local
dev only) so it's report-only: its number is printed but never fails the
gate. See the root TESTING.md's "Coverage gate" section for the policy
this implements.

Android's gated number is the exception to "whole-platform": a JVM floor on
decision-logic classes only (android/coverage-logic.toml), measured with no
device. The device-based Android numbers are informational.

Each platform's number is its own tool's native metric (Android:
instruction coverage from JaCoCo; Python: statement coverage from
coverage.py; Web: statement coverage from Vitest's v8 provider;
scan-proxy: line coverage from Node's --experimental-test-coverage) -
these are genuinely different metrics, not normalized to one, since each
is what that platform's own TESTING.md already documents and no single
metric is available across all four tools.

Usage: uv run scripts/coverage_gate.py [--refresh]
    --refresh   Re-run every platform's test suite instead of reading an
                existing report file, if one is present. Slow - the
                default without --refresh
                reads whatever report already exists on disk and only
                falls back to running the suite if no report is found at
                all.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from coverage_lib import (
    AndroidLogicScope,
    load_android_logic_scope,
    measure_android_logic,
    parse_android_report,
    parse_python_report,
    parse_scan_proxy_output,
    parse_web_report,
    read_jvm_report,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

# The device (Major) suite's report. Informational only since #130 - it no
# longer gates the release, see get_android_device_result below.
ANDROID_DEVICE_REPORT = (
    REPO_ROOT
    / "android"
    / "app"
    / "build"
    / "reports"
    / "coverage"
    / "androidTest"
    / "debug"
    / "connected"
    / "index.html"
)
# jacocoMergedCoverageReport's own output (android/app/build.gradle.kts) -
# Major's coverage.ec merged with External's (PaywallScreenWeeklyTest, via
# test-weekly.ps1's pulled coverage-external.ec). Informational only, see
# get_android_merged_result below and
# ClaudePlans/2026-09-09-merge-external-tier-coverage-paywallscreen.md.
ANDROID_MERGED_REPORT = (
    REPO_ROOT
    / "android"
    / "app"
    / "build"
    / "reports"
    / "coverage"
    / "androidTest"
    / "debug"
    / "merged"
    / "index.html"
)
PYTHON_REPORT = REPO_ROOT / "coverage.json"
WEB_REPORT = REPO_ROOT / "web" / "coverage" / "coverage-summary.json"

PYTHON_BASELINE = 79.0
SCAN_PROXY_BASELINE = 100.0

# Android's gate is a floor on decision logic only, measured from the JVM
# unit-test report (no device): the allow-list and waiver list live in
# ANDROID_LOGIC_SCOPE. Everything else - Compose, navigation, view-model
# wiring, provider wrappers - has no coverage number; device and External
# tests verify it. Measured about 97% on 2026-10-18 (#130).
ANDROID_LOGIC_FLOOR = 95.0
ANDROID_LOGIC_SCOPE = REPO_ROOT / "android" / "coverage-logic.toml"
ANDROID_JVM_REPORT = (
    REPO_ROOT / "android" / "app" / "build" / "reports" / "coverage" / "test" / "debug"
)

# Isolated research spikes that live inside app/src/main/ but are never
# reachable from production - excluded from Android's coverage number the
# same way src/experiments/BoundOCR/ is excluded from Python's (kept
# outside coverage.py's `source`). Add a new entry here, not a change to
# the baseline, the moment a new such spike lands - see
# coverage_lib.parse_android_report's own docstring for the full reasoning
# (item #8, found 2026-09-09).
ANDROID_EXCLUDED_PACKAGES = ("com.rigcheck.app.ui.experiments.cameraoverlay",)

_IS_WINDOWS = os.name == "nt"
# Absolute: cmd.exe does not look in the working directory when
# NoDefaultCurrentDirectoryInExePath is set, so a bare "gradlew.bat" is
# "not recognized".
_GRADLEW = str(REPO_ROOT / "android" / ("gradlew.bat" if _IS_WINDOWS else "gradlew"))


@dataclass
class PlatformResult:
    name: str
    percent: float | None
    baseline: float | None
    gated: bool
    note: str = ""
    problems: list[str] = field(default_factory=list)  # each one fails a gated platform
    warnings: list[str] = field(default_factory=list)  # printed, never fail

    @property
    def passed(self) -> bool:
        """A report-only or unmeasured platform never fails the gate."""
        if not self.gated:
            return True
        if self.problems:
            return False
        if self.baseline is None or self.percent is None:
            return True
        return self.percent >= self.baseline


# --- Run-or-read per platform ---


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd,
        shell=_IS_WINDOWS,
        capture_output=True,
        text=True,
    )


def check_android_logic(report_dir: Path, scope: AndroidLogicScope) -> PlatformResult:
    """Android's gated number: JVM instruction coverage over the allow-listed
    decision-logic classes only. Pure over an already-built report dir."""
    measured = measure_android_logic(read_jvm_report(report_dir), scope)
    problems = []
    if measured.percent < ANDROID_LOGIC_FLOOR:
        problems.append(
            f"decision-logic coverage {measured.percent:.1f}% is below the "
            f"{ANDROID_LOGIC_FLOOR:.1f}% floor "
            f"({measured.missed:,} of {measured.total:,} instructions missed)"
        )
    for name in measured.stale:
        problems.append(
            f"{name} is on the allow list but not in the report (stale list: "
            f"renamed, moved or deleted?)"
        )
    warnings = [
        f"unclassified (on neither list, add to {ANDROID_LOGIC_SCOPE.name}): {name}"
        for name in measured.unclassified
    ]
    return PlatformResult(
        "Android",
        measured.percent,
        ANDROID_LOGIC_FLOOR,
        True,
        note=f"decision logic, JVM report ({measured.total:,} instructions)",
        problems=problems,
        warnings=warnings,
    )


def get_android_result(refresh: bool) -> PlatformResult:
    """The gated Android result: a JVM floor on decision logic. Needs no
    device - only the unit-test coverage report."""
    if refresh or not (ANDROID_JVM_REPORT / "index.html").exists():
        proc = _run(
            [
                _GRADLEW,
                "testDebugUnitTest",
                "createDebugUnitTestCoverageReport",
            ],
            cwd=REPO_ROOT / "android",
        )
        if proc.returncode != 0:
            return PlatformResult(
                "Android",
                None,
                ANDROID_LOGIC_FLOOR,
                True,
                "testDebugUnitTest createDebugUnitTestCoverageReport failed - "
                "see android/TESTING.md.\n" + proc.stdout[-2000:],
            )
    if not (ANDROID_JVM_REPORT / "index.html").exists():
        return PlatformResult(
            "Android", None, ANDROID_LOGIC_FLOOR, True, f"No report at {ANDROID_JVM_REPORT}"
        )
    try:
        scope = load_android_logic_scope(ANDROID_LOGIC_SCOPE)
        return check_android_logic(ANDROID_JVM_REPORT, scope)
    except ValueError as error:
        return PlatformResult("Android", None, ANDROID_LOGIC_FLOOR, True, str(error))


def get_android_device_result() -> PlatformResult:
    """The device (Major) suite's app-wide number - informational only. It
    no longer gates the release, and never runs Gradle: the report is read
    if a past connectedDebugAndroidTest run left one, else shown as n/a."""
    if not ANDROID_DEVICE_REPORT.exists():
        return PlatformResult(
            "Android (device)", None, None, False, "no device report - informational only"
        )
    percent = parse_android_report(
        ANDROID_DEVICE_REPORT.read_text(encoding="utf-8"),
        exclude_packages=ANDROID_EXCLUDED_PACKAGES,
    )
    return PlatformResult("Android (device)", percent, None, False)


def get_android_merged_result(refresh: bool) -> PlatformResult:
    """Major+External merged Android coverage - a second, informational
    number alongside get_android_device_result's Major-only one. Never
    fails the release gate (PlatformResult(gated=False), baseline=None) -
    it exists purely to show PaywallScreenKt's real combined coverage,
    since its remaining Major-only gap is exactly the RevenueCat-dependent
    code paths the External tier (test-weekly.ps1) already exercises for
    real. See ClaudePlans/2026-09-09-merge-external-tier-coverage-
    paywallscreen.md for the full mechanism. Requires Major's own
    coverage.ec to already exist (from a prior connectedDebugAndroidTest
    run) - jacocoMergedCoverageReport merges whatever coverage.ec files it
    finds, so a missing External .ec (test-weekly.ps1 never run, or its
    pull failed) silently falls back to a Major-only merge rather than
    erroring, matching that task's own fileTree-based discovery.
    """
    if refresh or not ANDROID_MERGED_REPORT.exists():
        proc = _run(
            [
                _GRADLEW,
                "jacocoMergedCoverageReport",
            ],
            cwd=REPO_ROOT / "android",
        )
        if proc.returncode != 0:
            return PlatformResult(
                "Android (Major+External)",
                None,
                None,
                False,
                "jacocoMergedCoverageReport failed - is Major's own "
                "coverage.ec present (run connectedDebugAndroidTest first)? "
                "See android/TESTING.md.\n" + proc.stdout[-2000:],
            )
    if not ANDROID_MERGED_REPORT.exists():
        return PlatformResult(
            "Android (Major+External)",
            None,
            None,
            False,
            f"No report at {ANDROID_MERGED_REPORT}",
        )
    percent = parse_android_report(
        ANDROID_MERGED_REPORT.read_text(encoding="utf-8"),
        exclude_packages=ANDROID_EXCLUDED_PACKAGES,
    )
    return PlatformResult("Android (Major+External)", percent, None, False)


def get_python_result(refresh: bool) -> PlatformResult:
    if refresh or not PYTHON_REPORT.exists():
        proc = _run(
            [sys.executable, "-m", "pytest", "--cov", "--cov-report=json", "-q"],
            cwd=REPO_ROOT,
        )
        if proc.returncode not in (0, 1):
            # pytest exits 1 on test failures but still writes coverage.json;
            # any other code means it didn't run at all.
            return PlatformResult(
                "Python", None, PYTHON_BASELINE, True,
                "pytest failed to run - see output above.\n" + proc.stdout[-2000:],
            )
    if not PYTHON_REPORT.exists():
        return PlatformResult(
            "Python", None, PYTHON_BASELINE, True, f"No report at {PYTHON_REPORT}"
        )
    data = json.loads(PYTHON_REPORT.read_text(encoding="utf-8"))
    percent = parse_python_report(data)
    return PlatformResult("Python", percent, PYTHON_BASELINE, True)


def get_web_result(refresh: bool) -> PlatformResult:
    if refresh or not WEB_REPORT.exists():
        proc = _run(["npm", "run", "test:coverage"], cwd=REPO_ROOT / "web")
        if proc.returncode != 0:
            return PlatformResult(
                "Web", None, None, False,
                "npm run test:coverage failed - see output above.\n" + proc.stdout[-2000:],
            )
    if not WEB_REPORT.exists():
        return PlatformResult("Web", None, None, False, f"No report at {WEB_REPORT}")
    data = json.loads(WEB_REPORT.read_text(encoding="utf-8"))
    percent = parse_web_report(data)
    return PlatformResult(
        "Web", percent, None, False, "not gated - no release event yet"
    )


def get_scan_proxy_result(refresh: bool) -> PlatformResult:
    # scan-proxy has no report file to cache - its coverage summary only
    # exists in the command's own stdout/stderr, so this always re-runs.
    del refresh
    proc = _run(
        ["npm", "run", "test:coverage"], cwd=REPO_ROOT / "workers" / "scan-proxy"
    )
    output = proc.stdout + proc.stderr
    if proc.returncode != 0:
        return PlatformResult(
            "scan-proxy", None, SCAN_PROXY_BASELINE, True,
            "npm run test:coverage failed - see output above.\n" + output[-2000:],
        )
    percent = parse_scan_proxy_output(output)
    return PlatformResult("scan-proxy", percent, SCAN_PROXY_BASELINE, True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-run every platform's suite instead of reading an existing report",
    )
    args = parser.parse_args(argv)

    results = [
        get_android_result(args.refresh),
        get_android_device_result(),
        get_android_merged_result(args.refresh),
        get_python_result(args.refresh),
        get_web_result(args.refresh),
        get_scan_proxy_result(args.refresh),
    ]

    print(f"{'Platform':<12} {'Coverage':>10} {'Baseline':>10}  Status")
    print("-" * 55)
    any_gated_failure = False
    for result in results:
        percent_str = f"{result.percent:.2f}%" if result.percent is not None else "n/a"
        baseline_str = f"{result.baseline:.2f}%" if result.baseline is not None else "-"
        if not result.gated:
            status = "REPORT-ONLY"
        elif result.percent is None:
            status = "ERROR"
            any_gated_failure = True
        elif result.passed:
            status = "PASS"
        else:
            status = "FAIL"
            any_gated_failure = True
        print(f"{result.name:<12} {percent_str:>10} {baseline_str:>10}  {status}")
        if result.note:
            print(f"             {result.note}")
        for line in result.problems:
            print(f"             FAIL: {line}")
        for line in result.warnings:
            print(f"             warning: {line}")

    return 1 if any_gated_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
