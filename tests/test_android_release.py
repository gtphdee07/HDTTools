"""Function tests for scripts/android_release.py (#63): step order, the
missing-device failure, paid-call confirmation/counting/abort for the old
weekly suite, with a fake command runner, a fake device list, a fake
stale-surfaces check and a fake confirm function - no real device, test
run, deploy or network call."""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests._release_test_helpers import FakeRunner, always_confirm, never_confirm

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
for name in ("paid_call_budget", "release_steps", "android_release"):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)

pcb = sys.modules["paid_call_budget"]
ar = sys.modules["android_release"]


def test_happy_path_runs_every_step_in_order():
    runner = FakeRunner()
    budget = pcb.PaidCallBudget(max_calls=2, confirm=always_confirm, out=lambda _: None)
    code = ar.run(
        [], budget=budget, run_command=runner, devices=lambda: ["emulator-5554"],
        stale=lambda: ["revenuecat-rest"], out=lambda _: None,
    )
    assert code == 0
    assert runner.calls == [
        f"{ar.GRADLEW} -p android testDebugUnitTest",
        f"{ar.GRADLEW} -p android connectedDebugAndroidTest",
        "test-external.ps1",
        "test-weekly.ps1",
    ]
    assert budget.spent == 2


def test_no_device_fails_the_run_rather_than_skipping():
    runner = FakeRunner()
    budget = pcb.PaidCallBudget(max_calls=2, confirm=always_confirm, out=lambda _: None)
    code = ar.run(
        [], budget=budget, run_command=runner, devices=lambda: [],
        stale=lambda: [], out=lambda _: None,
    )
    assert code == 1
    # JVM step still ran (it needs no device); nothing after the device check did.
    assert runner.calls == [f"{ar.GRADLEW} -p android testDebugUnitTest"]


def test_an_unresolvable_adb_fails_the_run_cleanly_rather_than_raising():
    runner = FakeRunner()
    budget = pcb.PaidCallBudget(max_calls=2, confirm=always_confirm, out=lambda _: None)

    def raising_devices():
        raise RuntimeError("adb not found on PATH and neither ANDROID_SDK_ROOT nor ANDROID_HOME is set.")

    messages = []
    code = ar.run(
        [], budget=budget, run_command=runner, devices=raising_devices,
        stale=lambda: [], out=messages.append,
    )
    assert code == 1
    assert any("adb not found" in m for m in messages)
    assert "test-weekly.ps1" not in runner.calls


def test_a_failing_jvm_suite_stops_before_the_device_check():
    runner = FakeRunner(exit_codes={f"{ar.GRADLEW} -p android testDebugUnitTest": 1})
    budget = pcb.PaidCallBudget(max_calls=2, confirm=always_confirm, out=lambda _: None)
    devices_called = []
    code = ar.run(
        [], budget=budget, run_command=runner,
        devices=lambda: (devices_called.append(1) or ["emulator-5554"]),
        stale=lambda: [], out=lambda _: None,
    )
    assert code == 1
    assert devices_called == []


def test_no_stale_surfaces_skips_the_external_step():
    runner = FakeRunner()
    budget = pcb.PaidCallBudget(max_calls=2, confirm=always_confirm, out=lambda _: None)
    ar.run(
        [], budget=budget, run_command=runner, devices=lambda: ["emulator-5554"],
        stale=lambda: [], out=lambda _: None,
    )
    assert "test-external.ps1" not in runner.calls


def test_declining_the_weekly_suite_skips_it_without_failing_the_run():
    runner = FakeRunner()
    budget = pcb.PaidCallBudget(max_calls=2, confirm=never_confirm, out=lambda _: None)
    code = ar.run(
        [], budget=budget, run_command=runner, devices=lambda: ["emulator-5554"],
        stale=lambda: [], out=lambda _: None,
    )
    assert code == 0
    assert "test-weekly.ps1" not in runner.calls
    assert budget.spent == 0


def test_exceeding_the_declared_maximum_aborts_before_the_weekly_suite():
    runner = FakeRunner()
    budget = pcb.PaidCallBudget(max_calls=1, confirm=always_confirm, out=lambda _: None)
    code = ar.run(
        [], budget=budget, run_command=runner, devices=lambda: ["emulator-5554"],
        stale=lambda: [], out=lambda _: None,
    )
    assert code == 1
    assert "test-weekly.ps1" not in runner.calls


def test_a_failing_instrumented_suite_stops_the_run():
    runner = FakeRunner(exit_codes={f"{ar.GRADLEW} -p android connectedDebugAndroidTest": 3})
    budget = pcb.PaidCallBudget(max_calls=2, confirm=always_confirm, out=lambda _: None)
    code = ar.run(
        [], budget=budget, run_command=runner, devices=lambda: ["emulator-5554"],
        stale=lambda: [], out=lambda _: None,
    )
    assert code == 3
    assert "test-weekly.ps1" not in runner.calls


def test_connected_devices_excludes_unauthorized_and_offline_entries():
    runner_output = (
        "List of devices attached\n"
        "emulator-5554\tdevice\n"
        "ABC123\tunauthorized\n"
        "XYZ789\toffline\n"
        "\n"
    )

    def fake_run(command, capture_output=None, text=None):
        return SimpleNamespace(stdout=runner_output)

    assert ar.connected_devices(adb="adb", run_command=fake_run) == ["emulator-5554"]


def test_default_max_paid_calls_matches_the_weekly_steps_declared_cost():
    assert ar.DEFAULT_MAX_PAID_CALLS == ar.WEEKLY_STEP["paid_calls"]
