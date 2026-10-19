"""Function tests for scripts/dashboard_lib.py (roadmap item #7)."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import dashboard_lib  # noqa: E402

pytestmark = [pytest.mark.core, pytest.mark.minor]


# --- color_for_percent ---


def test_color_for_percent_100_is_blue():
    assert dashboard_lib.color_for_percent(100.0) == "blue"


def test_color_for_percent_above_90_is_green():
    assert dashboard_lib.color_for_percent(91.41) == "green"


def test_color_for_percent_above_80_is_yellow():
    assert dashboard_lib.color_for_percent(85.0) == "yellow"


def test_color_for_percent_at_80_is_red():
    """80% itself is red - the band is strictly '> 80', not '>= 80'."""
    assert dashboard_lib.color_for_percent(80.0) == "red"


def test_color_for_percent_below_80_is_red():
    assert dashboard_lib.color_for_percent(71.09) == "red"


# --- parse_junit_xml: testsuite-attribute schema (pytest/Vitest/Android) ---


def test_parse_junit_xml_reads_a_bare_testsuite_root(tmp_path):
    """Android's per-class Unit-tier files: a bare <testsuite> root."""
    xml_path = tmp_path / "report.xml"
    xml_path.write_text(
        '<testsuite name="x" tests="15" skipped="0" failures="0" errors="0"/>'
    )
    assert dashboard_lib.parse_junit_xml(xml_path) == (15, 15)


def test_parse_junit_xml_reads_testsuites_wrapping_one_testsuite(tmp_path):
    """pytest's schema: <testsuites> with no own counts, one child <testsuite>."""
    xml_path = tmp_path / "report.xml"
    xml_path.write_text(
        '<testsuites name="pytest tests">'
        '<testsuite name="pytest" tests="127" skipped="3" failures="0" errors="0"/>'
        "</testsuites>"
    )
    assert dashboard_lib.parse_junit_xml(xml_path) == (124, 127)


def test_parse_junit_xml_sums_multiple_testsuite_children(tmp_path):
    """Vitest's schema: <testsuites> with its own counts AND several child
    <testsuite> elements - the children are summed, root counts ignored,
    so a skipped test missing from the root total still gets counted."""
    xml_path = tmp_path / "report.xml"
    xml_path.write_text(
        '<testsuites name="vitest tests" tests="71" failures="0" errors="0">'
        '<testsuite name="a.test.ts" tests="10" failures="0" errors="0" skipped="0"/>'
        '<testsuite name="b.test.ts" tests="5" failures="1" errors="0" skipped="1"/>'
        "</testsuites>"
    )
    assert dashboard_lib.parse_junit_xml(xml_path) == (13, 15)


def test_parse_junit_xml_aggregates_a_list_of_paths(tmp_path):
    """Android's Unit tier: one file per test class, passed to parse_junit_xml
    as a list."""
    path_a = tmp_path / "a.xml"
    path_a.write_text('<testsuite tests="15" failures="0" errors="0" skipped="0"/>')
    path_b = tmp_path / "b.xml"
    path_b.write_text('<testsuite tests="3" failures="1" errors="0" skipped="0"/>')
    assert dashboard_lib.parse_junit_xml([path_a, path_b]) == (17, 18)


# --- parse_junit_xml: Node's flat <testcase>-only schema ---


def test_parse_junit_xml_reads_nodes_flat_testcase_schema_all_passing(tmp_path):
    xml_path = tmp_path / "report.xml"
    xml_path.write_text(
        "<testsuites>"
        '<testcase name="a" classname="test"/>'
        '<testcase name="b" classname="test"/>'
        "</testsuites>"
    )
    assert dashboard_lib.parse_junit_xml(xml_path) == (2, 2)


def test_parse_junit_xml_reads_nodes_flat_testcase_schema_with_a_failure(tmp_path):
    xml_path = tmp_path / "report.xml"
    xml_path.write_text(
        "<testsuites>"
        '<testcase name="a" classname="test"/>'
        '<testcase name="b" classname="test"><failure message="boom"/></testcase>'
        "</testsuites>"
    )
    assert dashboard_lib.parse_junit_xml(xml_path) == (1, 2)


def test_parse_junit_xml_raises_when_report_has_neither_schema(tmp_path):
    xml_path = tmp_path / "report.xml"
    xml_path.write_text("<testsuites></testsuites>")
    with pytest.raises(ValueError, match="No <testsuite>"):
        dashboard_lib.parse_junit_xml(xml_path)


# --- render_dashboard_svg ---


def _sample_row(name="Android"):
    return dashboard_lib.PlatformRow(
        name=name,
        minor=("blue", "31/31"),
        major=("green", "39/39"),
        external=("yellow", "3/4"),
        coverage=(71.09, "red"),
    )


def test_render_dashboard_svg_produces_well_formed_xml():
    svg = dashboard_lib.render_dashboard_svg([_sample_row()], generated="2026-08-24")
    root = ET.fromstring(svg)  # raises if not well-formed
    assert root.tag.endswith("svg")


def test_render_dashboard_svg_includes_each_platform_name():
    svg = dashboard_lib.render_dashboard_svg(
        [_sample_row("Android"), _sample_row("Web")], generated="2026-08-24"
    )
    assert "Android" in svg
    assert "Web" in svg


def test_render_dashboard_svg_shows_the_generated_date_in_the_header():
    svg = dashboard_lib.render_dashboard_svg([_sample_row()], generated="2026-08-24")
    assert "Graphic generated: 2026-08-24" in svg


def test_render_dashboard_svg_handles_a_not_yet_recorded_external_cell():
    row = dashboard_lib.PlatformRow(
        name="scan-proxy",
        minor=("blue", "9/9"),
        major=("blue", "57/57"),
        external=None,
        coverage=(100.0, "blue"),
    )
    svg = dashboard_lib.render_dashboard_svg([row], generated="2026-08-24")
    ET.fromstring(svg)  # still well-formed
    assert "n/a" in svg


def test_render_dashboard_svg_handles_missing_coverage_data():
    row = dashboard_lib.PlatformRow(
        name="Web",
        minor=("blue", "71/71"),
        major=("blue", "71/71"),
        external=None,
        coverage=None,
    )
    svg = dashboard_lib.render_dashboard_svg([row], generated="2026-08-24")
    ET.fromstring(svg)
    assert "n/a" in svg


def test_render_dashboard_svg_still_shows_a_real_percent_for_report_only_coverage():
    """Web's real coverage number is shown even though coverage_gate.py
    doesn't enforce it yet - report-only means not gated, not hidden."""
    row = dashboard_lib.PlatformRow(
        name="Web",
        minor=("blue", "71/71"),
        major=("blue", "71/71"),
        external=None,
        coverage=(91.41, "green"),
        coverage_gated=False,
    )
    svg = dashboard_lib.render_dashboard_svg([row], generated="2026-08-24")
    ET.fromstring(svg)
    assert "91.4%" in svg
    assert "report-only" in svg


def test_render_dashboard_svg_fits_a_long_external_label_without_overlapping_coverage():
    """Regression test for the real layout bug found from a screenshot:
    a long External label ran into the Coverage column's text."""
    label = dashboard_lib.format_surface_cell(["fresh", "planned", "overridden", "planned"])[1]
    row = dashboard_lib.PlatformRow(
        name="scan-proxy",
        minor=("blue", "9/9"),
        major=("blue", "57/57"),
        external=("red", label),
        coverage=(100.0, "blue"),
    )
    svg = dashboard_lib.render_dashboard_svg([row], generated="2026-08-24")
    root = ET.fromstring(svg)
    texts = root.findall(".//{http://www.w3.org/2000/svg}text")
    external_text = next(t for t in texts if t.text == label)
    coverage_text = next(t for t in texts if t.text == "100.0%")
    external_x = int(external_text.get("x"))
    coverage_x = int(coverage_text.get("x"))
    # A rough but real check: the external label's start plus a generous
    # per-character width estimate must still land left of where the
    # coverage text starts.
    assert external_x + len(external_text.text) * 8 < coverage_x


# --- External cell, python per-context coverage, snapshot rows (#49) ---


def test_format_surface_cell_all_fresh_is_blue():
    assert dashboard_lib.format_surface_cell(["fresh", "fresh"]) == ("blue", "2/2")


def test_format_surface_cell_counts_only_active_surfaces_in_the_score():
    color, label = dashboard_lib.format_surface_cell(["fresh", "stale", "planned"])
    assert (color, label) == ("red", "1/2 (1 planned)")


def test_format_surface_cell_shows_an_overridden_gate_and_does_not_count_it_as_fresh():
    assert dashboard_lib.format_surface_cell(["fresh", "overridden", "planned"]) == ("red", "1/2 (1 planned, 1 overridden)")
    assert dashboard_lib.format_surface_cell(["fresh", "fresh", "overridden"]) == ("red", "2/3 (1 overridden)")


def test_format_surface_cell_counts_failed_and_skipped_surfaces_as_not_fresh():
    assert dashboard_lib.format_surface_cell(["fresh", "failed", "skipped", "planned"]) == (
        "red", "1/3 (1 planned, 1 failed, 1 skipped)")
    assert dashboard_lib.format_surface_cell(["fresh"] * 9 + ["skipped"]) == ("yellow", "9/10 (1 skipped)")


def test_format_surface_cell_only_planned_surfaces_is_red_and_says_so():
    assert dashboard_lib.format_surface_cell(["planned", "planned"]) == ("red", "0/0 (2 planned)")


def test_format_surface_cell_without_surfaces_is_none():
    assert dashboard_lib.format_surface_cell([]) is None


def test_python_percent_for_sums_only_files_under_the_prefix():
    report = {"files": {
        "src/hdttools/a.py": {"summary": {"covered_lines": 8, "num_statements": 10}},
        r"src\hdttools\b.py": {"summary": {"covered_lines": 2, "num_statements": 10}},
        "streamlit_app/app.py": {"summary": {"covered_lines": 10, "num_statements": 10}},
    }}
    assert dashboard_lib.python_percent_for(report, "src/hdttools/") == 50.0
    assert dashboard_lib.python_percent_for(report, "streamlit_app/") == 100.0


def test_python_percent_for_no_matching_files_is_none():
    assert dashboard_lib.python_percent_for({"files": {}}, "src/hdttools/") is None


def test_snapshot_entry_round_trips_into_a_row_with_live_external_cell():
    entry = dashboard_lib.snapshot_entry(("green", "9/10"), None, (86.1, "yellow"), False)
    row = dashboard_lib.row_from_snapshot("Core", entry, ("blue", "2/2"))
    assert row.minor == ("green", "9/10") and row.major is None
    assert row.coverage == (86.1, "yellow") and row.coverage_gated is False
    assert row.external == ("blue", "2/2")


def test_row_from_snapshot_missing_platform_renders_everything_n_a():
    row = dashboard_lib.row_from_snapshot("Web", None, None)
    assert (row.minor, row.major, row.coverage, row.external) == (None,) * 4


def test_results_note_shows_the_measured_date_and_short_commit():
    snap = {"timestamp": "2026-10-04T12:00:00Z", "commit": "abcdef1234567"}
    assert dashboard_lib.results_note(snap) == " | tests run: 2026-10-04 @ abcdef1"


def test_results_note_without_a_snapshot_says_no_results():
    assert "no results" in dashboard_lib.results_note(None)


def test_render_dashboard_svg_shows_the_external_column_and_results_note():
    row = dashboard_lib.PlatformRow("Web", None, None, ("yellow", "1/2 (3 planned)"), None)
    svg = dashboard_lib.render_dashboard_svg([row], "2026-10-04", " | tests run: 2026-10-03")
    ET.fromstring(svg)
    assert "External" in svg and "1/2 (3 planned)" in svg and "tests run: 2026-10-03" in svg
    assert "Surfaces" not in svg


# --- per-surface list (#44) ---

_ALL_STATES = ("fresh", "stale", "failed", "skipped", "overridden", "planned")


def _surface_rows():
    return [
        dashboard_lib.SurfaceRow(f"surface-{state}", state, ("web", "scan-proxy") if state == "fresh" else ("web",))
        for state in _ALL_STATES
    ]


def _svg_texts(svg):
    root = ET.fromstring(svg)  # raises if not well-formed
    return [t.text for t in root.findall(".//{http://www.w3.org/2000/svg}text")]


def test_per_surface_list_shows_every_surface_with_its_state():
    svg = dashboard_lib.render_dashboard_svg([_sample_row()], "2026-10-19", surface_rows=_surface_rows())
    texts = _svg_texts(svg)
    assert "External surfaces" in texts
    for state in _ALL_STATES:
        assert f"surface-{state}" in texts
        assert any(t and t.startswith(state) for t in texts), state


def test_per_surface_list_says_a_planned_surface_is_not_covered():
    svg = dashboard_lib.render_dashboard_svg([_sample_row()], "2026-10-19", surface_rows=_surface_rows())
    assert "planned - not covered" in _svg_texts(svg)
    assert "fresh - not covered" not in _svg_texts(svg)


def test_per_surface_list_names_the_platforms_that_depend_on_each_surface():
    svg = dashboard_lib.render_dashboard_svg([_sample_row()], "2026-10-19", surface_rows=_surface_rows())
    assert "web, scan-proxy" in _svg_texts(svg)


def test_per_surface_list_gives_each_state_its_own_dot_colour_and_planned_is_grey():
    svg = dashboard_lib.render_dashboard_svg([], "2026-10-19", surface_rows=_surface_rows())
    dots = [c.get("fill") for c in ET.fromstring(svg).findall(".//{http://www.w3.org/2000/svg}circle")]
    assert len(dots) == len(_ALL_STATES)
    assert dots[-1] == "#8b949e"  # planned is grey, never a pass or fail colour
    assert dots[0] != dots[2]  # fresh and failed do not look alike


def test_no_surface_rows_means_no_surface_section_and_the_graphic_is_shorter():
    plain = dashboard_lib.render_dashboard_svg([_sample_row()], "2026-10-19")
    listed = dashboard_lib.render_dashboard_svg([_sample_row()], "2026-10-19", surface_rows=_surface_rows())
    assert "External surfaces" not in _svg_texts(plain)
    height = lambda s: int(ET.fromstring(s).get("height"))  # noqa: E731
    assert height(listed) > height(plain)
