"""Shared pytest setup.

Live-provider guard: any test that is not marked `external` and reaches
the real Anthropic client fails instead of making a billed call. Tests
that mock the client (`monkeypatch.setattr(..., "Anthropic", ...)`)
replace this guard for their own duration and are unaffected.

Deselected count under `-n`: xdist workers do the collecting, so the
controller's summary line drops "N deselected". The workers report their
count back and the controller prints it, so a parallel run can be compared
with a serial one (#129).
"""

from __future__ import annotations

import pytest


def _refuse_live_anthropic(*args, **kwargs):
    raise AssertionError(
        "This test reached the real Anthropic client but is not marked "
        "@pytest.mark.external. Mock the client, or mark the test "
        "external so it only runs under `pytest -m external`."
    )


@pytest.fixture(autouse=True)
def _block_live_anthropic_unless_external(request, monkeypatch):
    if request.node.get_closest_marker("external"):
        return
    try:
        import anthropic
    except ImportError:
        return
    monkeypatch.setattr(anthropic, "Anthropic", _refuse_live_anthropic)


_deselected: list = []


def pytest_deselected(items):
    _deselected.extend(items)


def pytest_sessionfinish(session):
    output = getattr(session.config, "workeroutput", None)  # set on xdist workers only
    if output is not None:
        output["deselected"] = len(_deselected)


class _ReportDeselected:
    """Controller side of the above; registered only when xdist is running the tests."""

    def __init__(self) -> None:
        self.counts: set[int] = set()

    def pytest_testnodedown(self, node, error):
        count = getattr(node, "workeroutput", {}).get("deselected")
        if count is not None:
            self.counts.add(count)

    def pytest_terminal_summary(self, terminalreporter):
        if self.counts:
            terminalreporter.write_line(f"deselected: {max(self.counts)} (reported by the xdist workers)")


def pytest_configure(config):
    if config.pluginmanager.hasplugin("xdist") and not hasattr(config, "workerinput") and config.getoption("numprocesses", None):
        config.pluginmanager.register(_ReportDeselected(), "report-deselected-under-xdist")
