"""Shared paid-call confirmation and counter (#62), used by the Worker and
Android release commands (scripts/scan_proxy_release.py,
scripts/android_release.py) and reusable by future paid External surfaces
(the Anthropic surface, #37).

A release run declares a maximum number of paid calls it is willing to
make (`PaidCallBudget(max_calls=...)`). Before each paid step, the owner
is asked to confirm, naming the step and how many calls it costs;
declining skips just that step. A step that would push the running total
over the maximum raises `BudgetExceeded` instead of prompting or running,
so a release aborts rather than silently running over budget.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


class BudgetExceeded(Exception):
    pass


def _prompt_confirm(description: str, calls: int) -> bool:
    reply = input(f"{description} will make {calls} paid call(s). Continue? [y/N] ")
    return reply.strip().lower() in ("y", "yes")


@dataclass
class PaidCallBudget:
    max_calls: int
    confirm: Callable[[str, int], bool] = None
    out: Callable[[str], None] = print
    spent: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if self.confirm is None:
            self.confirm = _prompt_confirm

    def confirm_and_spend(self, description: str, calls: int) -> bool:
        """True if the step was confirmed and should run; False if the owner
        declined. Raises BudgetExceeded (before prompting) if running it would
        push the total over max_calls."""
        if self.spent + calls > self.max_calls:
            raise BudgetExceeded(
                f"{description} needs {calls} paid call(s); "
                f"{self.spent} of {self.max_calls} already spent this run"
            )
        if not self.confirm(description, calls):
            self.out(f"Declined: {description}")
            return False
        self.spent += calls
        self.out(f"Confirmed: {description} ({calls} paid call(s); {self.spent}/{self.max_calls} spent)")
        return True
