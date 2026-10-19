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

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))  # coverage_gate.py imports coverage_lib

_SCRIPT_PATH = _SCRIPTS_DIR / "coverage_gate.py"
_spec = importlib.util.spec_from_file_location("coverage_gate", _SCRIPT_PATH)
coverage_gate = importlib.util.module_from_spec(_spec)
sys.modules["coverage_gate"] = coverage_gate
_spec.loader.exec_module(coverage_gate)

import coverage_lib  # noqa: E402
from tests._coverage_fakes import write_fake_jvm_report  # noqa: E402


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


# --- Android: JVM floor on decision logic (#130) --------------------------

_PKGS = ("com.x.domain", "com.x.data", "com.x.ui")


def _scope(**overrides):
    base = dict(
        allow=("com.x.domain.A", "com.x.data.B"),
        waived_classes={},
        waived_packages={"com.x.ui.screens": "Compose, device-verified"},
        watched_packages=_PKGS,
    )
    base.update(overrides)
    return coverage_lib.AndroidLogicScope(**base)


def _report(tmp_path, missed_a, extra=None):
    packages = {
        "com.x.domain": [("A", missed_a, 100 - missed_a)],
        "com.x.data": [("B", 0, 100)],
        "com.x.ui.screens": [("Screen", 900, 0)],
    }
    packages.update(extra or {})
    return write_fake_jvm_report(tmp_path / "jvm", packages)


def _scope_file(tmp_path):
    path = tmp_path / "scope.toml"
    path.write_text(
        'watched_packages = ["com.x.domain", "com.x.data", "com.x.ui"]\n'
        'allow = ["com.x.domain.A", "com.x.data.B"]\n'
        '[waive_packages]\n"com.x.ui.screens" = "Compose, device-verified"\n',
        encoding="utf-8",
    )
    return path


def _fail_if_called(*args, **kwargs):
    raise AssertionError("must not shell out")


def test_android_logic_passes_above_the_floor(tmp_path):
    result = coverage_gate.check_android_logic(_report(tmp_path, missed_a=8), _scope())
    assert result.percent == pytest.approx(96.0)
    assert result.baseline == 95.0
    assert result.gated is True
    assert result.passed is True


def test_android_logic_fails_below_the_floor_and_names_the_aggregate(tmp_path):
    result = coverage_gate.check_android_logic(_report(tmp_path, missed_a=12), _scope())
    assert result.percent == pytest.approx(94.0)
    assert result.passed is False
    assert any("94.0" in problem and "95.0" in problem for problem in result.problems)


def test_android_logic_at_exactly_the_floor_passes(tmp_path):
    result = coverage_gate.check_android_logic(_report(tmp_path, missed_a=10), _scope())
    assert result.percent == pytest.approx(95.0)
    assert result.passed is True


def test_android_logic_fails_when_an_allow_listed_class_is_not_in_the_report(tmp_path):
    scope = _scope(allow=("com.x.domain.A", "com.x.data.B", "com.x.data.Renamed"))
    result = coverage_gate.check_android_logic(_report(tmp_path, missed_a=0), scope)
    assert result.passed is False
    assert any("com.x.data.Renamed" in problem for problem in result.problems)


def test_android_logic_lists_an_unclassified_class_but_does_not_fail(tmp_path):
    report = _report(tmp_path, missed_a=0, extra={"com.x.ui": [("BrandNew", 500, 0)]})
    result = coverage_gate.check_android_logic(report, _scope())
    assert result.passed is True
    assert result.problems == []
    assert any("com.x.ui.BrandNew" in warning for warning in result.warnings)


def test_android_logic_ignores_a_waived_package_whatever_its_coverage(tmp_path):
    # com.x.ui.screens.Screen is 0% covered in _report; the gate still passes.
    result = coverage_gate.check_android_logic(_report(tmp_path, missed_a=0), _scope())
    assert result.percent == pytest.approx(100.0)
    assert result.warnings == []


def test_android_logic_floor_is_95_and_the_old_device_baseline_is_gone():
    assert coverage_gate.ANDROID_LOGIC_FLOOR == 95.0
    assert not hasattr(coverage_gate, "ANDROID_BASELINE")


def test_platform_result_with_a_problem_fails_even_at_a_high_percent():
    result = coverage_gate.PlatformResult("Android", 100.0, 95.0, gated=True, problems=["stale"])
    assert result.passed is False


def test_get_android_result_reads_the_jvm_report_without_a_device_or_gradle(tmp_path, monkeypatch):
    monkeypatch.setattr(coverage_gate, "ANDROID_JVM_REPORT", _report(tmp_path, missed_a=0))
    monkeypatch.setattr(coverage_gate, "ANDROID_LOGIC_SCOPE", _scope_file(tmp_path))
    monkeypatch.setattr(coverage_gate, "_run", _fail_if_called)
    assert coverage_gate.get_android_result(refresh=False).passed is True


def test_get_android_result_builds_the_jvm_report_with_unit_tests_only(tmp_path, monkeypatch):
    calls = []

    def fake_run(cmd, cwd):
        calls.append(cmd)
        _report(tmp_path, missed_a=0)

        class Done:
            returncode = 0
            stdout = ""

        return Done()

    monkeypatch.setattr(coverage_gate, "ANDROID_JVM_REPORT", tmp_path / "jvm")
    monkeypatch.setattr(coverage_gate, "ANDROID_LOGIC_SCOPE", _scope_file(tmp_path))
    monkeypatch.setattr(coverage_gate, "_run", fake_run)
    result = coverage_gate.get_android_result(refresh=True)
    assert result.passed is True
    assert len(calls) == 1
    assert "testDebugUnitTest" in calls[0]
    assert "createDebugUnitTestCoverageReport" in calls[0]
    assert not any("connected" in part.lower() or "androidtest" in part.lower() for part in calls[0])


def test_get_android_result_reports_an_error_when_the_gradle_build_fails(tmp_path, monkeypatch):
    class Failed:
        returncode = 1
        stdout = "BUILD FAILED"

    monkeypatch.setattr(coverage_gate, "ANDROID_JVM_REPORT", tmp_path / "missing")
    monkeypatch.setattr(coverage_gate, "ANDROID_LOGIC_SCOPE", _scope_file(tmp_path))
    monkeypatch.setattr(coverage_gate, "_run", lambda cmd, cwd: Failed())
    result = coverage_gate.get_android_result(refresh=False)
    assert result.percent is None
    assert result.gated is True


def test_device_report_absence_is_informational_and_never_fails_or_runs_gradle(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(coverage_gate, "ANDROID_DEVICE_REPORT", tmp_path / "none.html")
    monkeypatch.setattr(coverage_gate, "_run", _fail_if_called)
    result = coverage_gate.get_android_device_result()
    assert result.gated is False
    assert result.baseline is None
    assert result.percent is None
    assert result.passed is True


def test_device_report_present_is_shown_but_never_gated(tmp_path, monkeypatch):
    report = tmp_path / "index.html"
    report.write_text(
        '<tfoot><tr><td>Total</td><td class="bar">400 of 1,000</td></tr></tfoot>',
        encoding="utf-8",
    )
    monkeypatch.setattr(coverage_gate, "ANDROID_DEVICE_REPORT", report)
    monkeypatch.setattr(coverage_gate, "ANDROID_EXCLUDED_PACKAGES", ())
    result = coverage_gate.get_android_device_result()
    assert result.percent == pytest.approx(60.0)
    assert result.gated is False
    assert result.passed is True


def test_the_tracked_scope_file_loads_and_lists_the_decision_logic():
    scope = coverage_lib.load_android_logic_scope(coverage_gate.ANDROID_LOGIC_SCOPE)
    assert "com.rigcheck.app.domain.BreakdownKt" in scope.allow
    assert "com.rigcheck.app.data.AccountManager" in scope.allow
    assert "com.rigcheck.app.ui.screens" in scope.waived_packages
    assert all(reason.strip() for reason in scope.waived_classes.values())
