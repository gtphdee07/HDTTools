"""Generates dashboard.svg, the README-embedded test-status graphic
(roadmap item #7, reworked for the change-driven test approach, #49).

One row per context in CONTEXT-MAP.md (Core, Streamlit, Web, Android,
Scan Proxy). Per row: real Minor/Major pass-rate, real coverage and the
External surfaces' freshness (ADR-0008); below the grid, one line per
External surface with its state (fresh, stale, failed, skipped,
overridden or planned). Python's Minor and Major are real now: pytest
markers (#50) split the shared suite per context, so Core and Streamlit
each get `-m "minor and <ctx>"` and `-m <ctx>` runs.

Two kinds of data, deliberately handled differently:

- **Measured results** (pass-rates, coverage) come from running suites.
  A normal run (or --refresh) measures them and saves them to
  scripts/dashboard_data/test_results.json together with the date and
  commit. The header of the graphic shows when they were measured.
- **External** is never measured here (real money/time) and is always
  read live: the surfaces from the freshness script's manifest + status +
  git (registries are not contacted, so a new upstream release is not
  reflected here). The old platform+suite entries in external_status.json
  are history and are not shown.

--from-snapshot runs nothing: it rebuilds the graphic from the saved
measured results plus the live External cells. The pre-commit hook
(.githooks/pre-commit) uses it, so the surface columns stay current on
every commit without a slow or paid test run.

Usage: uv run scripts/generate_dashboard.py [--refresh | --from-snapshot]
    --refresh        Re-run every platform's suites instead of reading an
                     existing report (also controls coverage freshness,
                     via coverage_gate.py).
    --from-snapshot  Run nothing; render from the saved results.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import coverage_gate  # noqa: E402
import dashboard_lib  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_SVG = REPO_ROOT / "dashboard.svg"
SNAPSHOT_FILE = REPO_ROOT / "scripts" / "dashboard_data" / "test_results.json"

PLATFORMS = ("Core", "Streamlit", "Web", "Android", "Scan Proxy")
PYTHON_CONTEXTS = {"Core": ("core", "src/hdttools/"), "Streamlit": ("streamlit", "streamlit_app/")}
SURFACE_PLATFORM = {
    "Web": "web",
    "Android": "android",
    "Scan Proxy": "scan-proxy",
    "Core": "core",
    "Streamlit": "streamlit",
}

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
        if report is not None:
            # Node's junit reporter will not create a missing directory.
            report.parent.mkdir(parents=True, exist_ok=True)
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


def python_selection(marker: str, tier: str) -> str:
    """The pytest -m expression for one context's Minor or Major tier
    (Major includes Minor; see tests/TESTING.md)."""
    return f"minor and {marker}" if tier == "minor" else marker


def get_python_pass_rate(marker: str, tier: str, refresh: bool) -> tuple[int, int] | None:
    report = REPO_ROOT / f"junit-{marker}-{tier}.xml"
    return _get_pass_rate(
        [sys.executable, "-m", "pytest", "-q", "-m", python_selection(marker, tier),
         f"--junitxml={report}"],
        REPO_ROOT,
        report=report,
        refresh=refresh,
    )


def get_web_pass_rate(refresh: bool) -> tuple[int, int] | None:
    return _get_pass_rate(
        ["npm", "run", "test:report"],
        REPO_ROOT / "web",
        report=WEB_JUNIT_REPORT,
        refresh=refresh,
    )


def get_scan_proxy_pass_rate(tier: str, refresh: bool) -> tuple[int, int] | None:
    minor = tier == "minor"
    return _get_pass_rate(
        ["npm", "run", "test:report:sanity" if minor else "test:report"],
        REPO_ROOT / "workers" / "scan-proxy",
        report=SCAN_PROXY_MINOR_JUNIT_REPORT if minor else SCAN_PROXY_MAJOR_JUNIT_REPORT,
        refresh=refresh,
    )


def get_android_pass_rate(tier: str, refresh: bool) -> tuple[int, int] | None:
    minor = tier == "minor"
    return _get_pass_rate(
        ["gradlew.bat" if _IS_WINDOWS else "./gradlew",
         "test" if minor else "connectedDebugAndroidTest"],
        REPO_ROOT / "android",
        report_dir=ANDROID_MINOR_JUNIT_DIR if minor else ANDROID_MAJOR_JUNIT_DIR,
        refresh=refresh,
    )


def _coverage_cell(percent: float | None) -> tuple[float, str] | None:
    if percent is None:
        return None
    return percent, dashboard_lib.color_for_percent(percent)


def measure(refresh: bool) -> tuple[dict, coverage_gate.PlatformResult]:
    """Runs (or reads reports for) every platform; returns the snapshot
    entries by platform name plus Android's informational merged coverage."""
    entries: dict[str, dict] = {}

    python_result = coverage_gate.get_python_result(refresh)
    python_report = {}
    if coverage_gate.PYTHON_REPORT.exists():
        python_report = json.loads(coverage_gate.PYTHON_REPORT.read_text(encoding="utf-8"))
    for name, (marker, prefix) in PYTHON_CONTEXTS.items():
        # The release gate's floor applies to the combined Python number,
        # so the per-context figures here are report-only.
        entries[name] = dashboard_lib.snapshot_entry(
            _cell_from_counts(get_python_pass_rate(marker, "minor", refresh)),
            _cell_from_counts(get_python_pass_rate(marker, "major", refresh)),
            _coverage_cell(dashboard_lib.python_percent_for(python_report, prefix)),
            False,
        )
    del python_result  # only ran to make sure coverage.json exists

    web_result = coverage_gate.get_web_result(refresh)
    web_counts = get_web_pass_rate(refresh)  # one undifferentiated suite: Minor == Major
    entries["Web"] = dashboard_lib.snapshot_entry(
        _cell_from_counts(web_counts), _cell_from_counts(web_counts),
        _coverage_cell(web_result.percent), web_result.gated,
    )

    android_result = coverage_gate.get_android_result(refresh)
    # Major+External merged - informational only, printed by main().
    android_merged_result = coverage_gate.get_android_merged_result(refresh)
    entries["Android"] = dashboard_lib.snapshot_entry(
        _cell_from_counts(get_android_pass_rate("minor", refresh)),
        _cell_from_counts(get_android_pass_rate("major", refresh)),
        _coverage_cell(android_result.percent), android_result.gated,
    )

    proxy_result = coverage_gate.get_scan_proxy_result(refresh)
    entries["Scan Proxy"] = dashboard_lib.snapshot_entry(
        _cell_from_counts(get_scan_proxy_pass_rate("minor", refresh)),
        _cell_from_counts(get_scan_proxy_pass_rate("major", refresh)),
        _coverage_cell(proxy_result.percent), proxy_result.gated,
    )
    return entries, android_merged_result


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def head_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def surface_verdicts(manifest=None, status=None, git=None) -> list[dashboard_lib.SurfaceRow]:
    """Every surface's state (fresh, stale, failed, skipped, overridden or
    planned), from the manifest, recorded status and git only. Registries
    are not contacted (the dashboard and the commit hook must stay offline
    and fast), so a new upstream release shows up in `external_freshness.py`,
    not here. The platform+suite entries in the status file are history and
    are never read."""
    import external_freshness as ef

    manifest = ef.load_manifest() if manifest is None else manifest
    status = ef.load_status() if status is None else status
    git = ef.GitHistory() if git is None else git
    return [
        dashboard_lib.SurfaceRow(v.surface, v.display_state, tuple(manifest["surfaces"][v.surface].get("platforms", [])))
        for v in ef.evaluate(manifest, status, git, lambda _eco, _pkg: {})
    ]


def states_by_platform(surface_rows: list[dashboard_lib.SurfaceRow]) -> dict[str, list[str]]:
    by_platform: dict[str, list[str]] = {}
    for row in surface_rows:
        for platform in row.platforms:
            by_platform.setdefault(platform, []).append(row.state)
    return by_platform


def build_rows(entries: dict, surfaces: dict[str, list[str]]) -> list:
    return [
        dashboard_lib.row_from_snapshot(
            name,
            entries.get(name),
            dashboard_lib.format_surface_cell(surfaces.get(SURFACE_PLATFORM.get(name, ""), [])),
        )
        for name in PLATFORMS
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--refresh", action="store_true",
                      help="Re-run every platform's suites instead of reading an existing report")
    mode.add_argument("--from-snapshot", action="store_true",
                      help="Run nothing; render from the saved results and live External cells")
    args = parser.parse_args(argv)

    merged = None
    if args.from_snapshot:
        snapshot = load_json(SNAPSHOT_FILE)
    else:
        entries, merged = measure(args.refresh)
        snapshot = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "commit": head_commit(),
            "platforms": entries,
        }
        SNAPSHOT_FILE.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")

    try:
        surface_rows = surface_verdicts()
    except Exception as exc:  # the graphic must still render without surface data
        print(f"Surface freshness unavailable ({exc}); External column left n/a")
        surface_rows = []

    rows = build_rows(snapshot.get("platforms", {}), states_by_platform(surface_rows))
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    svg = dashboard_lib.render_dashboard_svg(rows, generated, dashboard_lib.results_note(snapshot), surface_rows)
    DASHBOARD_SVG.write_text(svg, encoding="utf-8")
    print(f"Wrote {DASHBOARD_SVG}")
    for row in rows:
        print(f"  {row.name}: minor={row.minor} major={row.major} external={row.external} "
              f"coverage={row.coverage}")
    if merged is not None:
        percent = f"{merged.percent:.2f}%" if merged.percent is not None else "n/a"
        print(f"  Android (Major+External, informational): {percent}")
        if merged.note:
            print(f"    {merged.note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
