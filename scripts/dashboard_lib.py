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

Color = Literal["blue", "green", "yellow", "red", "grey"]

_COLOR_HEX = {
    "blue": "#2563eb",
    "green": "#16a34a",
    "yellow": "#ca8a04",
    "red": "#dc2626",
    "grey": "#8b949e",
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


class PlatformRow(NamedTuple):
    name: str
    minor: tuple[Color, str] | None  # (color, label) - e.g. ("green", "31/32")
    major: tuple[Color, str] | None
    external: tuple[Color, str] | None  # this platform's External surfaces (format_surface_cell); None = it has none
    coverage: tuple[float, Color] | None  # None = no data (e.g. report failed)
    coverage_gated: bool = True  # False = real number shown, but report-only


class SurfaceRow(NamedTuple):
    name: str
    state: str  # an external_freshness display_state, see SURFACE_STATE_COLOR
    platforms: tuple[str, ...]  # the platforms whose release depends on this surface


_CATEGORY_LABELS = ("Minor", "Major", "External", "Coverage")

# One colour per state a surface can show (ADR-0008). Planned is grey: it is not covered, so it
# must never look like a pass or a fail.
SURFACE_STATE_COLOR: dict[str, Color] = {
    "fresh": "blue",
    "stale": "yellow",
    "skipped": "yellow",
    "failed": "red",
    "overridden": "red",
    "planned": "grey",
}


def render_dashboard_svg(
    rows: list[PlatformRow],
    generated: str,
    results_note: str = "",
    surface_rows: list[SurfaceRow] | tuple[SurfaceRow, ...] = (),
) -> str:
    """Renders a small grid: a "Graphic generated" meta line, one row per
    platform, one column per category plus coverage, then (when given) a
    list of every External surface with its state. Pure string
    templating - no image library dependency. `generated` is a caller-
    supplied date string (e.g. "2026-08-24") - not computed internally,
    so this stays a pure, deterministic function to test.
    """
    meta_height = 22
    row_height = 44
    header_height = 36
    surface_header_height = 30
    surface_row_height = 22
    # External's real labels ("2/5 (2 planned, 1 overridden)") are longer
    # than Minor/Major's ("31/31") - left-aligned rendering (below) means
    # each column's own width just needs to fit its own longest realistic
    # content; it can never overflow into the next column's text the way
    # centered-with-a-fixed-offset rendering did (real bug, found from a
    # screenshot of scan-proxy's row: an earlier, unbounded-length raw-date
    # version of this label ran straight into "100.0%").
    col_widths = [130, 80, 80, 240, 160]
    width = sum(col_widths)
    grid_height = meta_height + header_height + row_height * len(rows)
    surface_height = surface_header_height + surface_row_height * len(surface_rows) if surface_rows else 0
    height = grid_height + surface_height

    def cell_x(col: int) -> int:
        return sum(col_widths[:col])

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="13">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#0d1117"/>',
        f'<text x="8" y="{meta_height - 7}" fill="#8b949e" font-size="11">'
        f"Graphic generated: {generated}{results_note}</text>",
    ]

    headers = ["Platform", *_CATEGORY_LABELS]
    for col, label in enumerate(headers):
        svg_parts.append(
            f'<text x="{cell_x(col) + 8}" y="{meta_height + header_height - 12}" '
            f'fill="#c9d1d9" font-weight="bold">{label}</text>'
        )

    for row_index, row in enumerate(rows):
        y = meta_height + header_height + row_index * row_height
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

    if surface_rows:
        svg_parts.extend(_surface_list_parts(surface_rows, grid_height, surface_header_height,
                                             surface_row_height, col_widths))

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def _surface_list_parts(surface_rows, top, header_height, row_height, col_widths) -> list[str]:
    """SVG for the per-surface block: name, state (a planned surface says it is
    not covered) and the platforms that depend on it, one line each."""
    name_x, state_x, platforms_x = 28, 28 + col_widths[0] + 100, 28 + col_widths[0] + 100 + 180
    parts = [
        f'<text x="8" y="{top + header_height - 10}" fill="#c9d1d9" font-weight="bold">'
        "External surfaces</text>"
    ]
    for index, row in enumerate(surface_rows):
        cy = top + header_height + index * row_height + row_height // 2
        label = "planned - not covered" if row.state == "planned" else row.state
        parts.append(f'<circle cx="14" cy="{cy}" r="5" fill="{_COLOR_HEX[SURFACE_STATE_COLOR[row.state]]}"/>')
        parts.append(f'<text x="{name_x}" y="{cy + 4}" fill="#c9d1d9">{row.name}</text>')
        parts.append(f'<text x="{state_x}" y="{cy + 4}" fill="#c9d1d9">{label}</text>')
        parts.append(f'<text x="{platforms_x}" y="{cy + 4}" fill="#8b949e">{", ".join(row.platforms)}</text>')
    return parts


def format_surface_cell(states: list[str]) -> tuple[Color, str] | None:
    """One platform's External cell from its surfaces' states ("fresh" |
    "stale" | "failed" | "skipped" | "overridden" | "planned", as
    external_freshness's display_state reports them). Only active surfaces
    (everything but planned) count toward the score, and only fresh ones
    pass; planned, overridden, failed and skipped surfaces are also shown as
    counts so what is not covered stays visible (ADR-0008). None means the
    platform has no surfaces at all.
    """
    active = [s for s in states if s != "planned"]
    planned = len(states) - len(active)
    if not states:
        return None
    if not active:
        return "red", f"0/0 ({planned} planned)"
    fresh = sum(1 for s in active if s == "fresh")
    color = color_for_percent(fresh / len(active) * 100)
    counts = ((planned, "planned"), *((sum(1 for s in active if s == word), word)
                                      for word in ("overridden", "failed", "skipped")))
    notes = [f"{n} {word}" for n, word in counts if n]
    suffix = f" ({', '.join(notes)})" if notes else ""
    return color, f"{fresh}/{len(active)}{suffix}"


def python_percent_for(report: dict, prefix: str) -> float | None:
    """Statement coverage of the files under `prefix` from pytest-cov's
    --cov-report=json output (its `files` map holds per-file summaries).
    None when no measured file sits under the prefix."""
    covered = statements = 0
    for path, entry in report.get("files", {}).items():
        if path.replace("\\", "/").startswith(prefix):
            covered += entry["summary"]["covered_lines"]
            statements += entry["summary"]["num_statements"]
    return None if statements == 0 else covered / statements * 100


def snapshot_entry(
    minor: tuple[Color, str] | None,
    major: tuple[Color, str] | None,
    coverage: tuple[float, Color] | None,
    coverage_gated: bool,
) -> dict:
    """JSON-able measured results for one platform (the part of a row that
    comes from running suites, as opposed to the External column, which
    is always read live)."""
    return {
        "minor": list(minor) if minor else None,
        "major": list(major) if major else None,
        "coverage": list(coverage) if coverage else None,
        "coverage_gated": coverage_gated,
    }


def row_from_snapshot(
    name: str,
    entry: dict | None,
    external: tuple[Color, str] | None,
) -> PlatformRow:
    """A dashboard row from a stored snapshot entry plus the live External
    cell. A platform missing from the snapshot renders n/a."""
    entry = entry or {}
    pair = lambda v: tuple(v) if v else None  # noqa: E731
    return PlatformRow(
        name=name,
        minor=pair(entry.get("minor")),
        major=pair(entry.get("major")),
        external=external,
        coverage=pair(entry.get("coverage")),
        coverage_gated=entry.get("coverage_gated", True),
    )


def results_note(snapshot: dict | None) -> str:
    """Header suffix saying when the shown test results were measured, so a
    graphic built from a cached snapshot never looks fresher than it is."""
    if not snapshot or not snapshot.get("timestamp"):
        return " | tests: no results recorded"
    day = snapshot["timestamp"][:10]
    commit = (snapshot.get("commit") or "")[:7]
    return f" | tests run: {day}" + (f" @ {commit}" if commit else "")
