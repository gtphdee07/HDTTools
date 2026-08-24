"""Pure pass-rate parsing, color thresholds, and SVG rendering for the
README-embedded test-status dashboard (roadmap item #7).

JUnit XML schema note (confirmed against real output from all four
platforms' tools, 2026-08-24): pytest and Vitest both nest one or more
`<testsuite tests=... failures=... errors=... skipped=...>` elements
under a `<testsuites>` root (Vitest's `<testsuites>` root also carries
its own tests/failures/errors attributes, but not skipped - summing the
child `<testsuite>` elements instead of trusting the root avoids
undercounting skipped tests in that case); Android's AGP-generated
reports use a bare `<testsuite ...>` as the root (no wrapper) for the
Unit tier's per-class files, and a `<testsuites><testsuite ...>` wrapper
for the instrumented tier's single aggregate file. Node's built-in
--test-reporter=junit is the outlier: `<testcase>` elements sit directly
under `<testsuites>` with no `<testsuite>` wrapper and no aggregate
counts at all - pass/fail there has to be counted by presence/absence of
a `<failure>`/`<error>` child on each `<testcase>`.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Literal, NamedTuple

Color = Literal["blue", "green", "yellow", "red"]

_COLOR_HEX = {
    "blue": "#2563eb",
    "green": "#16a34a",
    "yellow": "#ca8a04",
    "red": "#dc2626",
}


def color_for_percent(percent: float) -> Color:
    """Blue=100%, Green>90%, Yellow>80%, Red<80% (decided 2026-08-24)."""
    if percent >= 100:
        return "blue"
    if percent > 90:
        return "green"
    if percent > 80:
        return "yellow"
    return "red"


def _counts_from_testsuite(suite: ET.Element) -> tuple[int, int]:
    tests = int(suite.get("tests", 0))
    failures = int(suite.get("failures", 0))
    errors = int(suite.get("errors", 0))
    skipped = int(suite.get("skipped", 0))
    return tests - failures - errors - skipped, tests


def parse_junit_xml(paths: str | Path | list[str | Path]) -> tuple[int, int]:
    """(passed, total) summed across one or more JUnit XML report files.

    Handles both real schemas seen across this repo's tools - see the
    module docstring. A single path or a list of paths (Android's Unit
    tier writes one file per test class) are both accepted.
    """
    if isinstance(paths, (str, Path)):
        paths = [paths]
    total_passed = 0
    total_tests = 0
    for path in paths:
        root = ET.parse(path).getroot()
        suites = [root] if root.tag == "testsuite" else root.findall(".//testsuite")
        if suites:
            for suite in suites:
                passed, tests = _counts_from_testsuite(suite)
                total_passed += passed
                total_tests += tests
            continue
        # Node's --test-reporter=junit: flat <testcase> elements, no
        # <testsuite> wrapper and no aggregate counts to read.
        testcases = root.findall(".//testcase")
        if not testcases:
            raise ValueError(f"No <testsuite> or <testcase> element found in {path}")
        for testcase in testcases:
            total_tests += 1
            if testcase.find("failure") is None and testcase.find("error") is None:
                total_passed += 1
    return total_passed, total_tests


def format_external_cell(
    statuses: list[dict],
) -> tuple[Color, str] | None:
    """Combines one or more recorded External-suite statuses (each
    {"passed": bool, "timestamp": str}) into one dashboard cell.

    A platform with two real External suites (scan-proxy: through-our-
    service + direct-provider-boundary) is scored as passed/total via the
    same color_for_percent banding the rest of the dashboard uses, for
    visual consistency - not a separate ad hoc pass/fail look. The label
    shows the oldest of the given timestamps, since that's the more
    conservative "how stale is this data" signal to surface. None (not an
    empty list) means "never recorded" - a genuinely different state from
    "recorded and failing."
    """
    if not statuses:
        return None
    passed_count = sum(1 for s in statuses if s["passed"])
    percent = passed_count / len(statuses) * 100
    oldest = min(s["timestamp"] for s in statuses)
    date_only = oldest.split("T", 1)[0]
    return color_for_percent(percent), f"{passed_count}/{len(statuses)} ({date_only})"


class PlatformRow(NamedTuple):
    name: str
    minor: tuple[Color, str] | None  # (color, label) - e.g. ("green", "31/32")
    major: tuple[Color, str] | None
    external: tuple[Color, str] | None  # None = never recorded, or N/A
    coverage: tuple[float, Color] | None  # None = no data (e.g. report failed)
    coverage_gated: bool = True  # False = real number shown, but report-only


_CATEGORY_LABELS = ("Minor", "Major", "External", "Coverage")


def render_dashboard_svg(rows: list[PlatformRow]) -> str:
    """Renders a small grid: one row per platform, one column per category
    plus coverage. Pure string templating - no image library dependency.
    """
    row_height = 44
    header_height = 36
    # External's real labels ("1/1 (2026-08-24)") are much longer than
    # Minor/Major's ("31/31") - left-aligned rendering (below) means each
    # column's own width just needs to fit its own longest realistic
    # content; it can never overflow into the next column's text the way
    # centered-with-a-fixed-offset rendering did (real bug, found from a
    # screenshot of scan-proxy's row: "1/1 (2026-08-24)" ran straight into
    # "100.0%").
    col_widths = [130, 80, 80, 170, 160]
    width = sum(col_widths)
    height = header_height + row_height * len(rows)

    def cell_x(col: int) -> int:
        return sum(col_widths[:col])

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="13">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#0d1117"/>',
    ]

    headers = ["Platform", *_CATEGORY_LABELS]
    for col, label in enumerate(headers):
        svg_parts.append(
            f'<text x="{cell_x(col) + 8}" y="{header_height - 12}" '
            f'fill="#c9d1d9" font-weight="bold">{label}</text>'
        )

    for row_index, row in enumerate(rows):
        y = header_height + row_index * row_height
        svg_parts.append(
            f'<text x="{cell_x(0) + 8}" y="{y + row_height // 2 + 5}" '
            f'fill="#c9d1d9">{row.name}</text>'
        )
        cells = [row.minor, row.major, row.external]
        for col, cell in enumerate(cells, start=1):
            left = cell_x(col) + 8
            cy = y + row_height // 2
            if cell is None:
                svg_parts.append(
                    f'<text x="{left}" y="{cy + 5}" fill="#8b949e">n/a</text>'
                )
                continue
            color, label = cell
            svg_parts.append(
                f'<circle cx="{left + 7}" cy="{cy}" r="7" fill="{_COLOR_HEX[color]}"/>'
            )
            svg_parts.append(
                f'<text x="{left + 21}" y="{cy + 5}" fill="#c9d1d9">{label}</text>'
            )
        coverage_col = 4
        cx = cell_x(coverage_col) + 8
        cy = y + row_height // 2
        if row.coverage is None:
            svg_parts.append(
                f'<text x="{cx}" y="{cy + 5}" fill="#8b949e">n/a</text>'
            )
        else:
            percent, color = row.coverage
            suffix = "" if row.coverage_gated else " (report-only)"
            svg_parts.append(
                f'<text x="{cx}" y="{cy + 5}" fill="{_COLOR_HEX[color]}">'
                f"{percent:.1f}%{suffix}</text>"
            )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)
