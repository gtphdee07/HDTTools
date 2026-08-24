"""Function tests for scripts/coverage_gate.py's pure parsing logic.

Only the parsers and PlatformResult.passed are covered here - they're
pure functions/dataclass logic taking already-read text/data, no
subprocess or filesystem I/O. The get_*_result functions that shell out
to each platform's real toolchain are deliberately not unit-tested here
(they're thin I/O glue, and this repo has no mocking convention for
gradlew/npm/pytest subprocesses) - they're exercised for real by
`scripts/coverage_gate.py`'s own manual runs, documented in
ARCHIVE_TESTING.md.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "coverage_gate.py"
_spec = importlib.util.spec_from_file_location("coverage_gate", _SCRIPT_PATH)
coverage_gate = importlib.util.module_from_spec(_spec)
sys.modules["coverage_gate"] = coverage_gate
_spec.loader.exec_module(coverage_gate)


def test_parse_android_report_computes_percent_from_missed_and_total():
    html = (
        '<tfoot><tr><td>Total</td><td class="bar">4,259 of 14,731</td>'
        '<td class="ctr2">71%</td></tr></tfoot>'
    )
    percent = coverage_gate.parse_android_report(html)
    assert percent == pytest.approx((14731 - 4259) / 14731 * 100)


def test_parse_android_report_raises_when_total_row_is_missing():
    with pytest.raises(ValueError, match="Total"):
        coverage_gate.parse_android_report("<html>no coverage table here</html>")


def test_parse_python_report_reads_percent_covered():
    data = {"totals": {"percent_covered": 79.4392523364486, "num_statements": 963}}
    assert coverage_gate.parse_python_report(data) == pytest.approx(79.4392523364486)


def test_parse_web_report_reads_statements_pct():
    data = {
        "total": {
            "lines": {"pct": 95.2},
            "statements": {"pct": 91.41},
            "functions": {"pct": 86.84},
            "branches": {"pct": 85.44},
        }
    }
    assert coverage_gate.parse_web_report(data) == pytest.approx(91.41)


def test_parse_scan_proxy_output_reads_all_files_line():
    output = (
        "ℹ file           | line % | branch % | funcs % | uncovered lines\n"
        "ℹ  claude.ts     | 100.00 |   100.00 |  100.00 | \n"
        "ℹ ---------------------------------------------------------------\n"
        "ℹ all files      | 100.00 |   100.00 |  100.00 | \n"
        "ℹ ---------------------------------------------------------------\n"
    )
    assert coverage_gate.parse_scan_proxy_output(output) == pytest.approx(100.0)


def test_parse_scan_proxy_output_reads_a_partial_percentage():
    output = "ℹ all files      | 79.44 |   60.00 |  70.00 | \n"
    assert coverage_gate.parse_scan_proxy_output(output) == pytest.approx(79.44)


def test_parse_scan_proxy_output_raises_when_summary_line_is_missing():
    with pytest.raises(ValueError, match="all files"):
        coverage_gate.parse_scan_proxy_output("no coverage output here")


def test_platform_result_passes_when_percent_meets_baseline():
    result = coverage_gate.PlatformResult("Android", 71.0, 71.0, gated=True)
    assert result.passed is True


def test_platform_result_fails_when_percent_drops_below_baseline():
    result = coverage_gate.PlatformResult("Android", 65.0, 71.0, gated=True)
    assert result.passed is False


def test_platform_result_report_only_never_fails_regardless_of_percent():
    result = coverage_gate.PlatformResult("Web", 10.0, None, gated=False)
    assert result.passed is True


def test_platform_result_with_no_measurement_never_fails():
    result = coverage_gate.PlatformResult(
        "Android", None, 71.0, gated=True, note="no device connected"
    )
    assert result.passed is True
