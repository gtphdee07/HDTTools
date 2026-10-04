"""Shared pytest setup.

Live-provider guard: any test that is not marked `external` and reaches
the real Anthropic client fails instead of making a billed call. Tests
that mock the client (`monkeypatch.setattr(..., "Anthropic", ...)`)
replace this guard for their own duration and are unaffected.
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
