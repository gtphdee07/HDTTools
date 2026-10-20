"""Function tests for scripts/android_session_end.py (#133): the device-free session-end command runs
the JVM unit tests, the decision-logic coverage floor and detekt in that order, and stops on the first
failure naming the step. A fake command runner stands in for Gradle and Python; nothing real runs."""

import importlib.util
import sys
from pathlib import Path

import pytest

from tests._release_test_helpers import FakeRunner

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
for name in ("external_freshness", "paid_call_budget", "release_steps", "android_session_end"):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)

ase = sys.modules["android_session_end"]

JVM = f"{ase.GRADLEW} -p android testDebugUnitTest createDebugUnitTestCoverageReport"
COVERAGE = f"{sys.executable} {_SCRIPTS / 'coverage_gate.py'} --android-logic"
DETEKT = f"{ase.GRADLEW} -p android detekt"


def _run(runner):
    lines: list[str] = []
    code = ase.run([], run_command=runner, out=lines.append)
    return code, lines


def test_runs_the_jvm_tests_then_the_coverage_floor_then_detekt():
    runner = FakeRunner()

    code, _ = _run(runner)

    assert code == 0
    assert runner.calls == [JVM, COVERAGE, DETEKT]


@pytest.mark.parametrize(
    "failing, ran, label",
    [
        (JVM, [JVM], "JVM unit tests"),
        (COVERAGE, [JVM, COVERAGE], "decision-logic coverage floor"),
        (DETEKT, [JVM, COVERAGE, DETEKT], "detekt"),
    ],
)
def test_stops_at_the_first_failing_step_with_its_exit_code_and_name(failing, ran, label):
    runner = FakeRunner({failing: 3})

    code, lines = _run(runner)

    assert code == 3
    assert runner.calls == ran
    assert any(label in line and "failed" in line for line in lines)


def test_a_passing_run_says_so():
    _, lines = _run(FakeRunner())

    assert lines[-1] == "Android session-end run complete."


def test_no_step_needs_a_device():
    for step in ase.STEPS:
        assert not any("connected" in part.lower() or "adb" in part.lower() for part in step["command"])
