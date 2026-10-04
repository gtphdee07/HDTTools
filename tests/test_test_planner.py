"""Tests for scripts/test_planner.py (#60): given changed files, which Python
tests the advisory planner picks at the per-issue level. Config and marker
set are faked; the command checks at the bottom run real `pytest
--collect-only` to confirm each planned selection picks what the planner
says."""

import importlib.util
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core]

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("test_planner", ROOT / "scripts" / "test_planner.py")
tp = importlib.util.module_from_spec(_spec)
sys.modules["test_planner"] = tp
_spec.loader.exec_module(tp)

MARKERS = {"external", "minor", "slow", "core", "streamlit"}
CONFIG = {
    "dependency_files": ["pyproject.toml", "uv.lock"],
    "contexts": {
        "core": {"marker": "core", "paths": ["src/hdttools/", "scripts/"]},
        "streamlit": {"marker": "streamlit", "paths": ["streamlit_app/"]},
    },
    "interfaces": [
        {
            "name": "ocr-output-keys",
            "context": "core",
            "files": ["src/hdttools/*_ocr.py", "streamlit_app/fields.py"],
            "tests": ["tests/test_ocr_output_key_contracts.py"],
            "shares_with": ["streamlit"],
        },
        {
            "name": "golden-vectors",
            "context": "core",
            "files": ["src/hdttools/api/breakdown.py"],
            "tests": ["tests/test_breakdown_golden_vectors.py"],
            "shares_with": ["android", "web"],
        },
    ],
}


def commands(plan):
    return [s.command for s in plan.selections]


def plan_for(files, config=CONFIG, markers=MARKERS):
    return tp.plan(files, config, markers)


def test_internal_change_plans_only_the_contexts_minor_suite():
    plan = plan_for(["src/hdttools/database.py"])
    assert commands(plan) == ['uv run pytest -m "minor and core"']


def test_a_streamlit_change_plans_the_streamlit_minor_suite():
    plan = plan_for(["streamlit_app/app.py"])
    assert commands(plan) == ['uv run pytest -m "minor and streamlit"']


def test_public_interface_change_adds_major_and_the_interface_tests():
    plan = plan_for(["src/hdttools/api/breakdown.py"])
    assert commands(plan) == [
        "uv run pytest -m core",
        "uv run pytest tests/test_breakdown_golden_vectors.py",
    ]
    assert any("android" in n and "web" in n for n in plan.notes)


def test_interface_shared_with_another_context_plans_that_contexts_side_too():
    plan = plan_for(["streamlit_app/fields.py"])
    assert commands(plan) == [
        'uv run pytest -m streamlit',
        "uv run pytest tests/test_ocr_output_key_contracts.py",
    ]


def test_dependency_change_forces_major_for_every_python_context():
    plan = plan_for(["uv.lock"])
    assert commands(plan) == ["uv run pytest -m core", "uv run pytest -m streamlit"]


def test_changed_test_file_runs_first_as_the_targeted_test():
    plan = plan_for(["src/hdttools/database.py", "tests/test_database.py"])
    assert commands(plan)[0] == "uv run pytest tests/test_database.py"
    assert plan.selections[0].kind == "targeted"


def test_files_outside_every_python_context_plan_nothing_and_say_so():
    plan = plan_for(["web/src/app.tsx", "README.md"])
    assert plan.selections == []
    assert plan.notes


def test_no_changed_files_plans_nothing():
    assert plan_for([]).selections == []


def test_windows_separators_are_normalised():
    assert commands(plan_for([r"src\hdttools\database.py"])) == ['uv run pytest -m "minor and core"']


def test_a_marker_missing_from_the_marker_set_is_skipped_with_a_note():
    plan = plan_for(["src/hdttools/database.py"], markers={"external"})
    assert plan.selections == []
    assert any("minor" in n or "core" in n for n in plan.notes)


def test_planner_exits_zero_whatever_it_plans(capsys):
    for files in (["uv.lock"], ["src/hdttools/api/breakdown.py"], [], ["nonsense/x.bin"]):
        assert tp.main(["--files", *files]) == 0
    assert "uv run pytest" in capsys.readouterr().out


def test_planner_exits_zero_even_when_git_fails(capsys):
    def broken_git(_):
        raise tp.GitError("no repo")

    assert tp.main([], git=broken_git) == 0
    assert "git" in capsys.readouterr().out.lower()


def test_main_prints_the_planned_commands(capsys):
    tp.main(["--files", "src/hdttools/database.py"])
    assert 'uv run pytest -m "minor and core"' in capsys.readouterr().out


# --- Command checks: each planned selection picks what the planner says ---


def _collect(command: str) -> list[str]:
    args = shlex.split(command)
    assert args[:3] == ["uv", "run", "pytest"]
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", *args[3:]],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return [line for line in out.splitlines() if "::" in line]


@pytest.fixture(scope="module")
def real_plan():
    config = tp.load_config()
    markers = tp.load_markers()
    return tp.plan(
        ["src/hdttools/api/breakdown.py", "src/hdttools/database.py", "streamlit_app/fields.py"],
        config, markers,
    )


def test_real_config_names_only_declared_markers():
    markers = tp.load_markers()
    config = tp.load_config()
    assert {c["marker"] for c in config["contexts"].values()} <= markers


def test_real_config_interface_tests_exist():
    for iface in tp.load_config()["interfaces"]:
        for test in iface["tests"]:
            assert (ROOT / test).is_file(), test


def test_every_planned_selection_collects_tests_and_none_are_external(real_plan):
    assert real_plan.selections
    for sel in real_plan.selections:
        ids = _collect(sel.command)
        assert ids, sel.command
        assert not any("test_claude_vision_external" in i for i in ids), sel.command


def test_planned_interface_selection_runs_exactly_its_test_file(real_plan):
    sels = [s for s in real_plan.selections if s.kind == "interface"]
    assert sels
    for sel in sels:
        files = {t for t in shlex.split(sel.command) if t.startswith("tests/")}
        assert {i.split("::")[0] for i in _collect(sel.command)} == files


def test_minor_selection_is_a_strict_subset_of_the_same_contexts_major():
    minor = set(_collect('uv run pytest -m "minor and core"'))
    major = set(_collect("uv run pytest -m core"))
    assert minor and minor < major


def test_streamlit_and_core_selections_do_not_overlap():
    assert not set(_collect("uv run pytest -m streamlit")) & set(_collect("uv run pytest -m core"))
