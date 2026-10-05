"""Function tests for scripts/paid_call_budget.py: confirmation, counting
and abort, with a fake confirm function (#62)."""

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
_spec = importlib.util.spec_from_file_location("paid_call_budget", _SCRIPTS / "paid_call_budget.py")
pcb = importlib.util.module_from_spec(_spec)
sys.modules["paid_call_budget"] = pcb
_spec.loader.exec_module(pcb)


class FakeConfirm:
    def __init__(self, answer: bool = True):
        self.answer = answer
        self.asked: list[tuple[str, int]] = []

    def __call__(self, description: str, calls: int) -> bool:
        self.asked.append((description, calls))
        return self.answer


def budget(max_calls: int, answer: bool = True) -> tuple["pcb.PaidCallBudget", FakeConfirm]:
    confirm = FakeConfirm(answer)
    return pcb.PaidCallBudget(max_calls=max_calls, confirm=confirm, out=lambda _: None), confirm


def test_confirmed_step_runs_and_is_counted():
    b, confirm = budget(max_calls=5)
    assert b.confirm_and_spend("step a", 2) is True
    assert confirm.asked == [("step a", 2)]
    assert b.spent == 2


def test_declined_step_does_not_run_and_is_not_counted():
    b, confirm = budget(max_calls=5, answer=False)
    assert b.confirm_and_spend("step a", 2) is False
    assert b.spent == 0


def test_spend_accumulates_across_multiple_confirmed_steps():
    b, _ = budget(max_calls=5)
    b.confirm_and_spend("step a", 2)
    b.confirm_and_spend("step b", 2)
    assert b.spent == 4


def test_a_step_that_would_exceed_the_maximum_aborts_without_prompting():
    b, confirm = budget(max_calls=3)
    with pytest.raises(pcb.BudgetExceeded):
        b.confirm_and_spend("step a", 4)
    assert confirm.asked == []
    assert b.spent == 0


def test_a_step_that_would_exceed_the_remaining_budget_aborts():
    b, confirm = budget(max_calls=3)
    b.confirm_and_spend("step a", 2)
    with pytest.raises(pcb.BudgetExceeded):
        b.confirm_and_spend("step b", 2)
    assert confirm.asked == [("step a", 2)]
    assert b.spent == 2


def test_a_step_exactly_at_the_remaining_budget_is_allowed():
    b, _ = budget(max_calls=3)
    b.confirm_and_spend("step a", 2)
    assert b.confirm_and_spend("step b", 1) is True
    assert b.spent == 3


def test_a_zero_call_step_still_confirms_but_never_exceeds_a_zero_budget():
    b, confirm = budget(max_calls=0)
    assert b.confirm_and_spend("free step", 0) is True
    assert confirm.asked == [("free step", 0)]
    assert b.spent == 0


def test_default_confirm_prompts_on_stdin(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")
    b = pcb.PaidCallBudget(max_calls=5, out=lambda _: None)
    assert b.confirm_and_spend("step a", 1) is True


def test_default_confirm_treats_anything_but_y_or_yes_as_declined(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    b = pcb.PaidCallBudget(max_calls=5, out=lambda _: None)
    assert b.confirm_and_spend("step a", 1) is False
