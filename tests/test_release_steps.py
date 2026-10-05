"""Function tests for scripts/release_steps.py's run_paid_step (#62, #63):
confirm, run, decline and abort, isolated from the two release scripts
that use it - with a fake command runner and a fake confirm function."""

import importlib.util
import sys
from pathlib import Path

import pytest

from tests._release_test_helpers import FakeRunner, always_confirm, never_confirm

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
for name in ("paid_call_budget", "release_steps"):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)

pcb = sys.modules["paid_call_budget"]
rs = sys.modules["release_steps"]

STEP = {"name": "a paid step", "command": ["powershell", "-NoProfile", "-File", "x.ps1"],
        "cwd": Path("."), "paid_calls": 2}


def test_a_confirmed_passing_step_runs_and_returns_none():
    runner = FakeRunner()
    budget = pcb.PaidCallBudget(max_calls=5, confirm=always_confirm, out=lambda _: None)
    result = rs.run_paid_step(STEP, budget=budget, run_command=runner, out=lambda _: None)
    assert result is None
    assert runner.calls == ["x.ps1"]
    assert budget.spent == 2


def test_a_declined_step_does_not_run_and_returns_none():
    runner = FakeRunner()
    budget = pcb.PaidCallBudget(max_calls=5, confirm=never_confirm, out=lambda _: None)
    result = rs.run_paid_step(STEP, budget=budget, run_command=runner, out=lambda _: None)
    assert result is None
    assert runner.calls == []
    assert budget.spent == 0


def test_a_step_that_would_exceed_the_budget_aborts_with_exit_code_one():
    runner = FakeRunner()
    budget = pcb.PaidCallBudget(max_calls=1, confirm=always_confirm, out=lambda _: None)
    result = rs.run_paid_step(STEP, budget=budget, run_command=runner, out=lambda _: None)
    assert result == 1
    assert runner.calls == []


def test_a_confirmed_failing_step_returns_its_exit_code():
    runner = FakeRunner(exit_codes={"x.ps1": 7})
    budget = pcb.PaidCallBudget(max_calls=5, confirm=always_confirm, out=lambda _: None)
    result = rs.run_paid_step(STEP, budget=budget, run_command=runner, out=lambda _: None)
    assert result == 7
    # The spend is still counted - the owner confirmed and the call was made.
    assert budget.spent == 2
