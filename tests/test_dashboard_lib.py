"""Function tests for scripts/dashboard_lib.py (roadmap item #7)."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import dashboard_lib  # noqa: E402


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


# --- format_external_cell ---


def test_format_external_cell_returns_none_when_never_recorded():
    assert dashboard_lib.format_external_cell([]) is None


def test_format_external_cell_single_suite_passed_is_blue():
    color, label = dashboard_lib.format_external_cell(
        [{"passed": True, "timestamp": "2026-08-24T16:50:57Z"}]
    )
    assert color == "blue"
    assert label == "1/1 (2026-08-24)"


def test_format_external_cell_single_suite_failed_is_red():
    color, label = dashboard_lib.format_external_cell(
        [{"passed": False, "timestamp": "2026-08-20T00:00:00Z"}]
    )
    assert color == "red"
    assert label == "0/1 (2026-08-20)"


def test_format_external_cell_combines_two_suites_and_uses_oldest_timestamp():
    color, label = dashboard_lib.format_external_cell(
        [
            {"passed": True, "timestamp": "2026-08-24T00:00:00Z"},
            {"passed": True, "timestamp": "2026-08-20T00:00:00Z"},
        ]
    )
    assert color == "blue"
    assert label == "2/2 (2026-08-20)"


def test_format_external_cell_one_of_two_failed_is_red():
    """50% falls below the '>80' yellow band, so it's red, not yellow."""
    color, _ = dashboard_lib.format_external_cell(
        [
            {"passed": True, "timestamp": "2026-08-24T00:00:00Z"},
            {"passed": False, "timestamp": "2026-08-24T00:00:00Z"},
        ]
    )
    assert color == "red"


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
    svg = dashboard_lib.render_dashboard_svg([_sample_row()])
    root = ET.fromstring(svg)  # raises if not well-formed
    assert root.tag.endswith("svg")


def test_render_dashboard_svg_includes_each_platform_name():
    svg = dashboard_lib.render_dashboard_svg(
        [_sample_row("Android"), _sample_row("Web")]
    )
    assert "Android" in svg
    assert "Web" in svg


def test_render_dashboard_svg_handles_a_not_yet_recorded_external_cell():
    row = dashboard_lib.PlatformRow(
        name="scan-proxy",
        minor=("blue", "9/9"),
        major=("blue", "57/57"),
        external=None,
        coverage=(100.0, "blue"),
    )
    svg = dashboard_lib.render_dashboard_svg([row])
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
    svg = dashboard_lib.render_dashboard_svg([row])
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
    svg = dashboard_lib.render_dashboard_svg([row])
    ET.fromstring(svg)
    assert "91.4%" in svg
    assert "report-only" in svg
