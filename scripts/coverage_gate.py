"""Cross-platform coverage gate, run at release time (roadmap item #9).

Reports real coverage for all four RigCheck platforms from each one's own
native coverage tooling, and enforces a baseline-floor threshold for the
platforms that have both a real coverage baseline and a real release
event today (Android, Python/Streamlit, scan-proxy). Web has no release
event yet (see NEXT_STEPS.md's "Deliberately not on this list" - local
dev only) so it's report-only: its number is printed but never fails the
gate. See the root TESTING.md's "Coverage gate" section for the policy
this implements.

Each platform's number is its own tool's native metric (Android:
instruction coverage from JaCoCo; Python: statement coverage from
coverage.py; Web: statement coverage from Vitest's v8 provider;
scan-proxy: line coverage from Node's --experimental-test-coverage) -
these are genuinely different metrics, not normalized to one, since each
is what that platform's own TESTING.md already documents and no single
metric is available across all four tools.

Usage: uv run scripts/coverage_gate.py [--refresh]
    --refresh   Re-run every platform's test suite instead of reading an
                existing report file, if one is present. Slow (the
                Android suite alone needs a connected device/emulator
                and several minutes) - the default without --refresh
                reads whatever report already exists on disk and only
                falls back to running the suite if no report is found at
                all.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

ANDROID_REPORT = (
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
PYTHON_REPORT = REPO_ROOT / "coverage.json"
WEB_REPORT = REPO_ROOT / "web" / "coverage" / "coverage-summary.json"

ANDROID_BASELINE = 71.0
PYTHON_BASELINE = 79.0
SCAN_PROXY_BASELINE = 100.0

_IS_WINDOWS = os.name == "nt"


@dataclass
class PlatformResult:
    name: str
    percent: float | None
    baseline: float | None
    gated: bool
    note: str = ""

    @property
    def passed(self) -> bool:
        """A report-only or unmeasured platform never fails the gate."""
        if not self.gated or self.baseline is None or self.percent is None:
            return True
        return self.percent >= self.baseline


# --- Pure parsers (each takes already-read text/data, no I/O of its own) ---


def parse_android_report(html: str) -> float:
    """Instruction coverage from the JaCoCo HTML report's Total row."""
    match = re.search(
        r'<tfoot><tr><td>Total</td><td class="bar">([\d,]+) of ([\d,]+)</td>',
        html,
    )
    if not match:
        raise ValueError("No 'Total' row found in the JaCoCo HTML report")
    missed = int(match.group(1).replace(",", ""))
    total = int(match.group(2).replace(",", ""))
    if total == 0:
        raise ValueError("JaCoCo report's Total row reports zero instructions")
    return (total - missed) / total * 100


def parse_python_report(data: dict) -> float:
    """Statement coverage from pytest-cov's --cov-report=json output."""
    return data["totals"]["percent_covered"]


def parse_web_report(data: dict) -> float:
    """Statement coverage from Vitest's v8-provider coverage-summary.json."""
    return data["total"]["statements"]["pct"]


def parse_scan_proxy_output(text: str) -> float:
    """Line coverage from Node's --experimental-test-coverage summary."""
    match = re.search(r"all files\s*\|\s*([\d.]+)\s*\|", text)
    if not match:
        raise ValueError(
            "No 'all files' coverage summary line found in scan-proxy's test output"
        )
    return float(match.group(1))


# --- Run-or-read per platform ---


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd,
        shell=_IS_WINDOWS,
        capture_output=True,
        text=True,
    )


def get_android_result(refresh: bool) -> PlatformResult:
    if refresh or not ANDROID_REPORT.exists():
        proc = _run(
            [
                "gradlew.bat" if _IS_WINDOWS else "./gradlew",
                "connectedDebugAndroidTest",
                "createDebugAndroidTestCoverageReport",
            ],
            cwd=REPO_ROOT / "android",
        )
        if proc.returncode != 0:
            return PlatformResult(
                "Android",
                None,
                ANDROID_BASELINE,
                True,
                "connectedDebugAndroidTest failed - is a device/emulator "
                "connected? See android/TESTING.md.\n" + proc.stdout[-2000:],
            )
    if not ANDROID_REPORT.exists():
        return PlatformResult(
            "Android", None, ANDROID_BASELINE, True, f"No report at {ANDROID_REPORT}"
        )
    percent = parse_android_report(ANDROID_REPORT.read_text(encoding="utf-8"))
    return PlatformResult("Android", percent, ANDROID_BASELINE, True)


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

    return 1 if any_gated_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
