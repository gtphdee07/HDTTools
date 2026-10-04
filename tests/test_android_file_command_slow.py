"""The documented Android file command really runs one class (#52).

Compiles and runs the Kotlin JVM tests, so it is `slow` and not `minor`: the
fast Minor run skips it, an unfiltered `uv run pytest` runs it, and the
planner lists it at Android release. Offline; no device.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from tests.test_context_test_commands import ANDROID, ANDROID_CLASS, ANDROID_FILE_CMD, _gradle

pytestmark = [pytest.mark.core, pytest.mark.slow]


def test_android_file_command_runs_exactly_that_class():
    assert ANDROID_FILE_CMD == f"./gradlew testDebugUnitTest --tests {ANDROID_CLASS}"
    # Clean first so a cached or earlier full run cannot stand in for this one.
    _gradle("cleanTestDebugUnitTest", "testDebugUnitTest", "--tests", ANDROID_CLASS, timeout=900)
    results = sorted((ANDROID / "app/build/test-results/testDebugUnitTest").glob("TEST-*.xml"))
    assert [p.name for p in results] == [f"TEST-{ANDROID_CLASS}.xml"]
    suite = ET.parse(results[0]).getroot()
    assert int(suite.get("tests")) > 0 and int(suite.get("failures")) == 0 and int(suite.get("errors")) == 0
