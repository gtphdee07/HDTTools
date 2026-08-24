"""Function tests for scripts/coverage_gate.py's PlatformResult threshold logic.

The report parsers themselves moved to scripts/coverage_lib.py 2026-08-24
(roadmap item #7, shared with the dashboard) - see
tests/test_coverage_lib.py for those. Only PlatformResult.passed's
baseline-floor logic is covered here - the get_*_result functions that
shell out to each platform's real toolchain are deliberately not
unit-tested (thin I/O glue, no mocking convention for gradlew/npm/pytest
subprocesses in this repo) - they're exercised for real by
scripts/coverage_gate.py's own manual runs, documented in
ARCHIVE_TESTING.md.
"""

import importlib.util
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))  # coverage_gate.py imports coverage_lib

_SCRIPT_PATH = _SCRIPTS_DIR / "coverage_gate.py"
_spec = importlib.util.spec_from_file_location("coverage_gate", _SCRIPT_PATH)
coverage_gate = importlib.util.module_from_spec(_spec)
sys.modules["coverage_gate"] = coverage_gate
_spec.loader.exec_module(coverage_gate)


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
