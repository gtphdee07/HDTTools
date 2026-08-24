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
