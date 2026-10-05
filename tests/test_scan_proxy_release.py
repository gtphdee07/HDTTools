"""Function tests for scripts/scan_proxy_release.py (#62): step order,
paid-call confirmation, counting and abort, with a fake command runner,
a fake stale-surfaces check and a fake confirm function - no real
network call, deploy or test run."""

import importlib.util
import sys
from pathlib import Path

import pytest

from tests._release_test_helpers import FakeRunner, always_confirm, never_confirm

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
for name in ("paid_call_budget", "release_steps", "scan_proxy_release"):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)

pcb = sys.modules["paid_call_budget"]
spr = sys.modules["scan_proxy_release"]


def test_happy_path_runs_offline_then_external_then_release_then_weekly_in_order():
    runner = FakeRunner()
    budget = pcb.PaidCallBudget(max_calls=3, confirm=always_confirm, out=lambda _: None)
    code = spr.run(
        [], budget=budget, run_command=runner, stale=lambda: ["revenuecat-rest"], out=lambda _: None
    )
    assert code == 0
    assert runner.calls == [
        "npm --prefix workers/scan-proxy test",
        "test-external.ps1",
        "test-release.ps1",
        "test-weekly.ps1",
    ]
    assert budget.spent == 3


def test_no_stale_surfaces_skips_the_external_step():
    runner = FakeRunner()
    budget = pcb.PaidCallBudget(max_calls=3, confirm=always_confirm, out=lambda _: None)
    spr.run([], budget=budget, run_command=runner, stale=lambda: [], out=lambda _: None)
    assert "test-external.ps1" not in runner.calls


def test_a_failing_offline_suite_stops_before_anything_paid_runs():
    runner = FakeRunner(exit_codes={"npm --prefix workers/scan-proxy test": 1})
    budget = pcb.PaidCallBudget(max_calls=3, confirm=always_confirm, out=lambda _: None)
    code = spr.run([], budget=budget, run_command=runner, stale=lambda: [], out=lambda _: None)
    assert code == 1
    assert runner.calls == ["npm --prefix workers/scan-proxy test"]
    assert budget.spent == 0


def test_declining_a_paid_step_skips_it_but_continues_to_the_next():
    runner = FakeRunner()
    budget = pcb.PaidCallBudget(max_calls=3, confirm=never_confirm, out=lambda _: None)
    code = spr.run([], budget=budget, run_command=runner, stale=lambda: [], out=lambda _: None)
    assert code == 0
    assert "test-release.ps1" not in runner.calls
    assert "test-weekly.ps1" not in runner.calls
    assert budget.spent == 0


def test_exceeding_the_declared_maximum_aborts_the_run_before_the_weekly_suite():
    runner = FakeRunner()
    # Only 1 call declared: the release suite (1 call) fits, the weekly suite (2) does not.
    budget = pcb.PaidCallBudget(max_calls=1, confirm=always_confirm, out=lambda _: None)
    code = spr.run([], budget=budget, run_command=runner, stale=lambda: [], out=lambda _: None)
    assert code == 1
    assert runner.calls == ["npm --prefix workers/scan-proxy test", "test-release.ps1"]
    assert "test-weekly.ps1" not in runner.calls


def test_a_failing_paid_step_stops_the_run():
    runner = FakeRunner(exit_codes={"test-release.ps1": 5})
    budget = pcb.PaidCallBudget(max_calls=3, confirm=always_confirm, out=lambda _: None)
    code = spr.run([], budget=budget, run_command=runner, stale=lambda: [], out=lambda _: None)
    assert code == 5
    assert "test-weekly.ps1" not in runner.calls


def test_default_max_paid_calls_covers_exactly_the_release_and_weekly_suites():
    assert spr.DEFAULT_MAX_PAID_CALLS == spr.RELEASE_STEP["paid_calls"] + spr.WEEKLY_STEP["paid_calls"]
