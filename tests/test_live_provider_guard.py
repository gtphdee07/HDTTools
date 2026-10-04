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


def test_the_live_claude_vision_file_is_marked_external():
    from tests import test_claude_vision_external as live

    assert "external" in {m.name for m in live.pytestmark}


def test_the_default_run_excludes_external(pytestconfig):
    assert "not external" in pytestconfig.getini("addopts")


def test_every_test_file_that_gates_on_the_real_key_is_marked_external():
    """A file that reads the real key to decide whether to run is a live
    test; it must carry `external` so the default run deselects it."""
    from pathlib import Path

    unmarked = []
    for path in sorted(Path(__file__).parent.glob("test_*.py")):
        if path == Path(__file__):
            continue
        source = path.read_text(encoding="utf-8")
        if 'getenv("ANTHROPIC_API_KEY")' in source or "environ.get(\"ANTHROPIC_API_KEY\")" in source:
            if "pytest.mark.external" not in source:
                unmarked.append(path.name)
    assert unmarked == []
