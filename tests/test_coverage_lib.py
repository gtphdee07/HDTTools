"""Function tests for scripts/coverage_lib.py's coverage-report parsers.

Extracted from tests/test_coverage_gate.py 2026-08-24 (roadmap item #7)
when the parsers themselves moved out of coverage_gate.py into this
shared module - see coverage_lib.py's own docstring for why. Pure
functions taking already-read text/data, no subprocess or filesystem I/O.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import coverage_lib  # noqa: E402


def test_parse_android_report_computes_percent_from_missed_and_total():
    html = (
        '<tfoot><tr><td>Total</td><td class="bar">4,259 of 14,731</td>'
        '<td class="ctr2">71%</td></tr></tfoot>'
    )
    percent = coverage_lib.parse_android_report(html)
    assert percent == pytest.approx((14731 - 4259) / 14731 * 100)


def test_parse_android_report_raises_when_total_row_is_missing():
    with pytest.raises(ValueError, match="Total"):
        coverage_lib.parse_android_report("<html>no coverage table here</html>")


# Real per-package row snippet shape (top-level JaCoCo index.html, item #8
# 2026-09-09): a package below the exclusion threshold - e.g. an isolated
# research spike like ui.experiments.cameraoverlay, never reachable from
# production, same spirit as BoundOCR being kept outside Python's
# coverage.py `source` - shouldn't drag down the app-wide real number.
_REPORT_WITH_TWO_PACKAGES = (
    '<table><tbody>'
    '<tr><td id="a0"><a href="com.rigcheck.app.ui.experiments.cameraoverlay/index.html" '
    'class="el_package">com.rigcheck.app.ui.experiments.cameraoverlay</a></td>'
    '<td class="bar" id="b0">'
    '<img src="jacoco-resources/redbar.gif" width="27" height="10" title="1,636" alt="1,636"/>'
    '<img src="jacoco-resources/greenbar.gif" width="2" height="10" title="154" alt="154"/>'
    '</td><td class="ctr2" id="c0">8%</td></tr>'
    '<tr><td id="a1"><a href="com.rigcheck.app.ui.screens/index.html" '
    'class="el_package">com.rigcheck.app.ui.screens</a></td>'
    '<td class="bar" id="b1">'
    '<img src="jacoco-resources/redbar.gif" width="18" height="10" title="1,079" alt="1,079"/>'
    '<img src="jacoco-resources/greenbar.gif" width="101" height="10" title="6,016" alt="6,016"/>'
    '</td><td class="ctr2" id="c1">84%</td></tr>'
    '</tbody></table>'
    '<tfoot><tr><td>Total</td><td class="bar">2,715 of 8,885</td><td class="ctr2">69%</td></tr></tfoot>'
)


def test_parse_android_report_excludes_a_named_package_from_the_total():
    # Excluding cameraoverlay's 1,636 missed/1,790 total should leave
    # exactly screens' own 1,079 missed/7,095 total.
    percent = coverage_lib.parse_android_report(
        _REPORT_WITH_TWO_PACKAGES,
        exclude_packages=("com.rigcheck.app.ui.experiments.cameraoverlay",),
    )
    assert percent == pytest.approx((7095 - 1079) / 7095 * 100)


def test_parse_android_report_with_no_exclusions_matches_the_unmodified_total():
    percent = coverage_lib.parse_android_report(_REPORT_WITH_TWO_PACKAGES)
    assert percent == pytest.approx((8885 - 2715) / 8885 * 100)


def test_parse_android_report_raises_for_an_exclude_package_not_in_the_report():
    with pytest.raises(ValueError, match="not_a_real_package"):
        coverage_lib.parse_android_report(
            _REPORT_WITH_TWO_PACKAGES, exclude_packages=("not_a_real_package",)
        )


def test_parse_python_report_reads_percent_covered():
    data = {"totals": {"percent_covered": 79.4392523364486, "num_statements": 963}}
    assert coverage_lib.parse_python_report(data) == pytest.approx(79.4392523364486)


def test_parse_web_report_reads_statements_pct():
    data = {
        "total": {
            "lines": {"pct": 95.2},
            "statements": {"pct": 91.41},
            "functions": {"pct": 86.84},
            "branches": {"pct": 85.44},
        }
    }
    assert coverage_lib.parse_web_report(data) == pytest.approx(91.41)


def test_parse_scan_proxy_output_reads_all_files_line():
    output = (
        "ℹ file           | line % | branch % | funcs % | uncovered lines\n"
        "ℹ  claude.ts     | 100.00 |   100.00 |  100.00 | \n"
        "ℹ ---------------------------------------------------------------\n"
        "ℹ all files      | 100.00 |   100.00 |  100.00 | \n"
        "ℹ ---------------------------------------------------------------\n"
    )
    assert coverage_lib.parse_scan_proxy_output(output) == pytest.approx(100.0)


def test_parse_scan_proxy_output_reads_a_partial_percentage():
    output = "ℹ all files      | 79.44 |   60.00 |  70.00 | \n"
    assert coverage_lib.parse_scan_proxy_output(output) == pytest.approx(79.44)


def test_parse_scan_proxy_output_raises_when_summary_line_is_missing():
    with pytest.raises(ValueError, match="all files"):
        coverage_lib.parse_scan_proxy_output("no coverage output here")
