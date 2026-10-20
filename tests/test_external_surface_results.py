"""The pytest side of #89: run_external_pytest.py's pytest invocation writes
JUnit XML that external_wrapper.surface_results can attribute per surface.
Runs a throwaway pytest in a temp dir; no live calls."""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
import external_wrapper as ew  # noqa: E402

_spec = importlib.util.spec_from_file_location("run_external_pytest", _SCRIPTS / "run_external_pytest.py")
rep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rep)


def test_command_selects_the_surfaces_markers_and_loads_the_plugin():
    cmd = rep.command(["a", "b"], None)[3:]  # past "python -m pytest"
    assert cmd[cmd.index("-m") + 1] == "external and (a or b)"
    assert cmd[cmd.index("-p") + 1] == "external_surface_plugin"
    assert not any(c.startswith("--junitxml") for c in cmd)


def test_command_selects_a_hyphenated_surface_by_its_underscored_marker():
    cmd = rep.command(["anthropic-python", "other"], None)[3:]
    assert cmd[cmd.index("-m") + 1] == "external and (anthropic_python or other)"


def test_a_hyphenated_surfaces_marked_tests_are_attributed_to_it_by_name(tmp_path):
    (tmp_path / "test_surfaces.py").write_text(
        "import pytest\n"
        "@pytest.mark.anthropic_python\n"
        "def test_python_ok(): pass\n"
        "@pytest.mark.anthropic\n"
        "def test_worker_bad(): assert False\n",
        encoding="utf-8",
    )
    results = tmp_path / "results.xml"
    env = {**os.environ, "EXTERNAL_SURFACES": "anthropic-python", "PYTHONPATH": str(_SCRIPTS)}
    subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "external_surface_plugin", "-p", "no:cacheprovider",
         f"--junitxml={results}", "-W", "ignore", str(tmp_path)],
        cwd=tmp_path, env=env, capture_output=True,
    )
    got = ew.read_results_file(results, ["anthropic-python"], ew.TAG_FORMATS["marker"])
    assert got == {"anthropic-python": ew.Counts(passed=1)}


def test_command_writes_junit_only_when_the_wrapper_asks():
    assert "--junitxml=/tmp/r.xml" in rep.command(["a"], "/tmp/r.xml")


def test_every_surfaces_marked_tests_are_attributed_to_it_in_the_junit_file(tmp_path):
    (tmp_path / "test_surfaces.py").write_text(
        "import pytest\n"
        "@pytest.mark.a\n"
        "def test_a_ok(): pass\n"
        "@pytest.mark.a\n"
        "def test_a_bad(): assert False\n"
        "@pytest.mark.b\n"
        "def test_b_ok(): pass\n"
        "def test_unmarked(): pass\n",
        encoding="utf-8",
    )
    results = tmp_path / "results.xml"
    env = {**os.environ, "EXTERNAL_SURFACES": "a,b", "PYTHONPATH": str(_SCRIPTS)}
    subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "external_surface_plugin", "-p", "no:cacheprovider",
         f"--junitxml={results}", "-W", "ignore", str(tmp_path)],
        cwd=tmp_path, env=env, capture_output=True,
    )
    got = ew.read_results_file(results, ["a", "b"], ew.TAG_FORMATS["marker"])
    assert got == {"a": ew.Counts(passed=1, failed=1), "b": ew.Counts(passed=1)}
