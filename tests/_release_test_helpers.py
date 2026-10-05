"""Shared fakes for tests/test_scan_proxy_release.py and
tests/test_android_release.py (#62, #63): a fake command runner and
always/never-confirming fakes for scripts/paid_call_budget.PaidCallBudget."""

from __future__ import annotations

from types import SimpleNamespace


class FakeRunner:
    """Fake run_command: records every command run (by its powershell script
    name, or the joined command otherwise) and returns a per-command exit code."""

    def __init__(self, exit_codes: dict[str, int] | None = None):
        self.exit_codes = exit_codes or {}
        self.calls: list[str] = []

    def __call__(self, command, cwd=None):
        name = command[-1] if command[0] == "powershell" else " ".join(command)
        self.calls.append(name)
        return SimpleNamespace(returncode=self.exit_codes.get(name, 0))


def always_confirm(_description: str, _calls: int) -> bool:
    return True


def never_confirm(_description: str, _calls: int) -> bool:
    return False
