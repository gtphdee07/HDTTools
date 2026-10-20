"""pytest plugin for scripts/run_external_pytest.py: records which surface each
selected test belongs to as a `surface` property, which pytest writes into the
JUnit XML. Pytest markers are not otherwise in that file, and the wrapper
(external_wrapper.py) needs the surface to record each one from its own tests.
"""

from __future__ import annotations

import os


def marker_name(surface: str) -> str:
    """The pytest marker a surface's tests carry: its name with hyphens as underscores
    (`anthropic-python` is marked `anthropic_python`), since `pytest.mark.<name>` and the
    `markers` setting need an identifier."""
    return surface.replace("-", "_")


def pytest_collection_modifyitems(items):
    surfaces = [s for s in os.environ.get("EXTERNAL_SURFACES", "").split(",") if s]
    for item in items:
        for surface in surfaces:
            if item.get_closest_marker(marker_name(surface)):
                item.user_properties.append(("surface", surface))
