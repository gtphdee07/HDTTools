"""The `external` marker is the only way a test may reach a live provider,
and a default run never selects it (see `[tool.pytest.ini_options]` in
`pyproject.toml`, and `tests/conftest.py` for the runtime guard)."""

from __future__ import annotations

import pytest

from hdttools import vision_client

pytestmark = [pytest.mark.core, pytest.mark.minor]


def test_an_unmarked_test_that_reaches_the_real_anthropic_client_fails():
    with pytest.raises(AssertionError, match="not marked"):
        vision_client.extract_via_claude(b"x", "image/jpeg", "s", "t", "d", {})


def test_the_live_claude_vision_file_is_marked_external(pytestconfig):
    from tests import test_claude_vision_external as live

    marks = live.pytestmark if isinstance(live.pytestmark, list) else [live.pytestmark]
    assert "external" in {m.name for m in marks}


def test_the_default_run_excludes_external(pytestconfig):
    assert "not external" in pytestconfig.getini("addopts")
