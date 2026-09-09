"""Pure coverage-report parsers shared by coverage_gate.py and the
dashboard (generate_dashboard.py, roadmap item #7).

Extracted from coverage_gate.py 2026-08-24 (roadmap item #7's dashboard
plan) so the release gate and the dashboard both parse each platform's
coverage report the same way, from one place, instead of duplicating
(and risking drifting) the same regex/JSON-key logic in two scripts.
Each platform's number is its own tool's native metric (Android:
instruction coverage from JaCoCo; Python: statement coverage from
coverage.py; Web: statement coverage from Vitest's v8 provider;
scan-proxy: line coverage from Node's --experimental-test-coverage) -
these are genuinely different metrics, not normalized to one, since each
is what that platform's own TESTING.md already documents and no single
metric is available across all four tools.
"""

from __future__ import annotations

import re


def parse_android_report(html: str, exclude_packages: tuple[str, ...] = ()) -> float:
    """Instruction coverage from the JaCoCo HTML report's Total row, minus
    any package named in exclude_packages.

    Exclusion exists for isolated research spikes that live inside the
    app module's main/ source set but are never reachable from production
    (e.g. ui.experiments.cameraoverlay, item #18) - same spirit as
    src/experiments/BoundOCR/ being kept outside Python's coverage.py
    `source` config so an intentionally-unwired experiment doesn't drag
    down the real, shippable-code number (item #8, found 2026-09-09: the
    camera-overlay spike alone dropped Android's measured coverage from
    71% to 64.28%).
    """
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

    for package in exclude_packages:
        pkg_missed, pkg_total = _android_package_instruction_counts(html, package)
        missed -= pkg_missed
        total -= pkg_total

    if total == 0:
        raise ValueError("Excluding all requested packages leaves zero instructions")
    return (total - missed) / total * 100


def _android_package_instruction_counts(html: str, package: str) -> tuple[int, int]:
    """Missed and total instructions for one package row in the top-level
    JaCoCo index.html. Matched by CSS class (redbar.gif = missed,
    greenbar.gif = covered) rather than image position, since a
    0%- or 100%-covered package's row only has one of the two <img> tags."""
    row_match = re.search(
        r'<a href="[^"]*index\.html" class="el_package">'
        + re.escape(package)
        + r'</a></td><td class="bar"[^>]*>(.*?)</td>',
        html,
        re.DOTALL,
    )
    if not row_match:
        raise ValueError(f"Package {package!r} not found in the JaCoCo HTML report")
    segment = row_match.group(1)

    missed_match = re.search(r'redbar\.gif"[^>]*title="([\d,]+)"', segment)
    covered_match = re.search(r'greenbar\.gif"[^>]*title="([\d,]+)"', segment)
    missed = int(missed_match.group(1).replace(",", "")) if missed_match else 0
    covered = int(covered_match.group(1).replace(",", "")) if covered_match else 0
    return missed, missed + covered


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
