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
