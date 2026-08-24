"""Generates dashboard.svg, the README-embedded test-status graphic
(roadmap item #7).

Per platform, shows real Minor/Major pass-rate (color-coded, run fresh on
every regen) and real coverage (reusing coverage_gate.py's own run-or-read
logic, so this never duplicates or drifts from what the release gate
reports). External's status is read from a small persisted "last real
run" file instead of being re-run here - see
scripts/record_external_result.py and the root TESTING.md's "Dashboard"
section for why: External suites cost real money/time (a real Claude
call, a booted emulator), and regenerating a README graphic shouldn't
trigger that.

Usage: uv run scripts/generate_dashboard.py [--refresh]
    --refresh   Re-run every platform's Minor+Major suite instead of
                reading an existing report, if one is present (same
                meaning as coverage_gate.py's --refresh, and reuses that
                script's own coverage retrieval, so this flag also
                controls coverage freshness).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import coverage_gate
import dashboard_lib

REPO_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_SVG = REPO_ROOT / "dashboard.svg"
EXTERNAL_STATUS_FILE = REPO_ROOT / "scripts" / "dashboard_data" / "external_status.json"

PYTHON_JUNIT_REPORT = REPO_ROOT / "junit.xml"
WEB_JUNIT_REPORT = REPO_ROOT / "web" / "test-results" / "junit.xml"
SCAN_PROXY_MINOR_JUNIT_REPORT = (
    REPO_ROOT / "workers" / "scan-proxy" / "test-results" / "junit-minor.xml"
)
SCAN_PROXY_MAJOR_JUNIT_REPORT = (
    REPO_ROOT / "workers" / "scan-proxy" / "test-results" / "junit-major.xml"
)
ANDROID_MINOR_JUNIT_DIR = (
    REPO_ROOT / "android" / "app" / "build" / "test-results" / "testDebugUnitTest"
)
ANDROID_MAJOR_JUNIT_DIR = (
    REPO_ROOT
    / "android"
    / "app"
    / "build"
    / "outputs"
    / "androidTest-results"
    / "connected"
    / "debug"
)

_IS_WINDOWS = os.name == "nt"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, shell=_IS_WINDOWS, capture_output=True, text=True)


def _get_pass_rate(
    cmd: list[str],
    cwd: Path,
    *,
    report: Path | None = None,
    report_dir: Path | None = None,
    refresh: bool,
) -> tuple[int, int] | None:
    """Runs cmd (if needed) and parses the JUnit XML it produces.

    Exactly one of report (a single file) or report_dir (a directory
    globbed for *.xml - Android's Unit tier writes one file per test
    class) should be given.
    """

    def existing() -> list[Path]:
        if report is not None:
            return [report] if report.exists() else []
        return list(report_dir.glob("*.xml"))

    paths = existing()
    if refresh or not paths:
        _run(cmd, cwd=cwd)
        paths = existing()
    if not paths:
        return None
    return dashboard_lib.parse_junit_xml(paths)


def _cell_from_counts(counts: tuple[int, int] | None) -> tuple[str, str] | None:
    if counts is None:
        return None
    passed, total = counts
    if total == 0:
        return None
    percent = passed / total * 100
    return dashboard_lib.color_for_percent(percent), f"{passed}/{total}"


def get_python_pass_rate(refresh: bool) -> tuple[int, int] | None:
    return _get_pass_rate(
        [sys.executable, "-m", "pytest", "-q", f"--junitxml={PYTHON_JUNIT_REPORT}"],
        REPO_ROOT,
        report=PYTHON_JUNIT_REPORT,
        refresh=refresh,
    )


def get_web_pass_rate(refresh: bool) -> tuple[int, int] | None:
    return _get_pass_rate(
        ["npm", "run", "test:report"],
        REPO_ROOT / "web",
        report=WEB_JUNIT_REPORT,
        refresh=refresh,
    )


def get_scan_proxy_minor_pass_rate(refresh: bool) -> tuple[int, int] | None:
    return _get_pass_rate(
        ["npm", "run", "test:report:sanity"],
        REPO_ROOT / "workers" / "scan-proxy",
        report=SCAN_PROXY_MINOR_JUNIT_REPORT,
        refresh=refresh,
    )


def get_scan_proxy_major_pass_rate(refresh: bool) -> tuple[int, int] | None:
    return _get_pass_rate(
        ["npm", "run", "test:report"],
        REPO_ROOT / "workers" / "scan-proxy",
        report=SCAN_PROXY_MAJOR_JUNIT_REPORT,
        refresh=refresh,
    )


def get_android_minor_pass_rate(refresh: bool) -> tuple[int, int] | None:
    return _get_pass_rate(
        ["gradlew.bat" if _IS_WINDOWS else "./gradlew", "test"],
        REPO_ROOT / "android",
        report_dir=ANDROID_MINOR_JUNIT_DIR,
        refresh=refresh,
    )


def get_android_major_pass_rate(refresh: bool) -> tuple[int, int] | None:
    return _get_pass_rate(
        ["gradlew.bat" if _IS_WINDOWS else "./gradlew", "connectedDebugAndroidTest"],
        REPO_ROOT / "android",
        report_dir=ANDROID_MAJOR_JUNIT_DIR,
        refresh=refresh,
    )


def load_external_status() -> dict:
    if not EXTERNAL_STATUS_FILE.exists():
        return {}
    return json.loads(EXTERNAL_STATUS_FILE.read_text(encoding="utf-8"))


def build_rows(refresh: bool) -> list[dashboard_lib.PlatformRow]:
    status = load_external_status()

    android_result = coverage_gate.get_android_result(refresh)
    python_result = coverage_gate.get_python_result(refresh)
    web_result = coverage_gate.get_web_result(refresh)
    scan_proxy_result = coverage_gate.get_scan_proxy_result(refresh)

    def coverage_cell(result: coverage_gate.PlatformResult):
        if result.percent is None:
            return None
        return result.percent, dashboard_lib.color_for_percent(result.percent)

    python_counts = get_python_pass_rate(refresh)
    web_counts = get_web_pass_rate(refresh)

    rows = [
        dashboard_lib.PlatformRow(
            name="Android",
            minor=_cell_from_counts(get_android_minor_pass_rate(refresh)),
            major=_cell_from_counts(get_android_major_pass_rate(refresh)),
            external=dashboard_lib.format_external_cell(
                [status["android"]["weekly"]] if "weekly" in status.get("android", {}) else []
            ),
            coverage=coverage_cell(android_result),
            coverage_gated=android_result.gated,
        ),
        # Python's suite is undifferentiated (no [sanity]-equivalent
        # marker exists) - Minor and Major both reflect the same one run,
        # per tests/TESTING.md's own "Event-based tiers" section.
        dashboard_lib.PlatformRow(
            name="Python",
            minor=_cell_from_counts(python_counts),
            major=_cell_from_counts(python_counts),
            external=None,  # no real 3rd-party boundary in this platform
            coverage=coverage_cell(python_result),
            coverage_gated=python_result.gated,
        ),
        # Same undifferentiated-suite fact as Python - see web/TESTING.md.
        dashboard_lib.PlatformRow(
            name="Web",
            minor=_cell_from_counts(web_counts),
            major=_cell_from_counts(web_counts),
            external=None,  # no real 3rd-party boundary in this platform
            coverage=coverage_cell(web_result),
            coverage_gated=web_result.gated,
        ),
        dashboard_lib.PlatformRow(
            name="scan-proxy",
            minor=_cell_from_counts(get_scan_proxy_minor_pass_rate(refresh)),
            major=_cell_from_counts(get_scan_proxy_major_pass_rate(refresh)),
            external=dashboard_lib.format_external_cell(
                [
                    status["scan_proxy"][suite]
                    for suite in ("weekly", "release")
                    if suite in status.get("scan_proxy", {})
                ]
            ),
            coverage=coverage_cell(scan_proxy_result),
            coverage_gated=scan_proxy_result.gated,
        ),
    ]
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-run every platform's Minor+Major suite instead of reading an existing report",
    )
    args = parser.parse_args(argv)

    rows = build_rows(args.refresh)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    svg = dashboard_lib.render_dashboard_svg(rows, generated)
    DASHBOARD_SVG.write_text(svg, encoding="utf-8")
    print(f"Wrote {DASHBOARD_SVG}")
    for row in rows:
        print(f"  {row.name}: minor={row.minor} major={row.major} "
              f"external={row.external} coverage={row.coverage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
