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


# --- All contexts, session-end and release levels (#61): fake context map, markers, surfaces ---

ALL = {
    "dependency_files": ["pyproject.toml", "uv.lock"],
    "scope": {"file_max_files": 2},
    "contexts": {
        "core": {
            "marker": "core", "paths": ["src/hdttools/", "scripts/"],
            "file": "uv run pytest {file}", "test_for": ["tests/test_{stem}.py"],
            "context": "uv run pytest -m core", "application": "uv run pytest",
        },
        "streamlit": {
            "marker": "streamlit", "paths": ["streamlit_app/"],
            "file": "uv run pytest {file}", "test_for": ["tests/test_{stem}.py"],
            "context": "uv run pytest -m streamlit", "application": "uv run pytest",
        },
        "web": {
            "paths": ["web/"], "platform": "web",
            "dependency_files": ["web/package.json"],
            "test_globs": ["web/src/*.test.ts"], "live_globs": ["web/src/external/*"],
            "commands": {"minor": "web-test", "major": "web-test"},
            "file": "web-test -- {rel}", "test_for": ["{dir}/{stem}.test.ts"],
            "context": "web-test", "gate": "freshness --platform web", "external": "web-external",
        },
        "scan-proxy": {
            "paths": ["workers/scan-proxy/"], "platform": "scan-proxy",
            "test_globs": ["workers/scan-proxy/src/*.test.ts"],
            "commands": {"minor": "proxy-sanity", "major": "proxy-test"},
            "file": "proxy-file {rel}", "test_for": ["{dir}/{stem}.test.ts"],
            "context": "proxy-test", "external": "proxy-external",
            "release": [
                {"command": "proxy-test", "reason": "Major suite"},
                {"command": "proxy-weekly", "reason": "old weekly suite", "confirm": True},
            ],
        },
        "android": {
            "paths": ["android/"], "platform": "android",
            "dependency_files": ["android/app/build.gradle.kts"],
            "test_globs": ["android/app/src/test/*"],
            "device_covered": ["android/app/src/main/java/app/ui/*", "android/app/src/androidTest/*"],
            "commands": {"minor": "gradle-jvm", "major": "gradle-jvm"},
            "device": "gradle-device",
            "file": "gradle-jvm --tests {fqcn}", "test_for": ["{dir}/{stem}Test.kt"],
            "dir_rewrite": ["src/main/", "src/test/"],
            "context": "gradle-jvm",
            "release": [
                {"command": "gradle-jvm", "reason": "JVM tests"},
                {"command": "gradle-device", "reason": "instrumented tests"},
            ],
        },
    },
    "interfaces": [
        {
            "name": "golden-vectors", "context": "core",
            "files": ["src/hdttools/api/breakdown.py", "web/src/breakdown.ts"],
            "tests": ["tests/test_breakdown_golden_vectors.py"],
            "shares_with": ["android", "web"],
            "shares_tests": {"web": "web-test -- src/breakdown.test.ts", "android": "gradle-jvm --tests Golden"},
        },
    ],
}
SURFACES = [
    {"name": "supabase-auth", "state": "stale", "platforms": ["web"], "paid": False},
    {"name": "claude-vision", "state": "stale", "platforms": ["scan-proxy"], "paid": True},
    {"name": "revenuecat-rest", "state": "fresh", "platforms": ["scan-proxy", "android"], "paid": False},
    {"name": "play-billing", "state": "planned", "platforms": ["android"], "paid": False},
]
EXISTING_TESTS = {
    "tests/test_database.py",
    "web/src/api.test.ts",
    "workers/scan-proxy/src/scan.test.ts",
    "android/app/src/test/java/app/domain/BreakdownTest.kt",
}


def plan_all(files, level="issue", **kwargs):
    kwargs.setdefault("file_exists", lambda p: p in EXISTING_TESTS)
    return tp.plan(files, ALL, MARKERS, level=level, **kwargs)


def test_issue_level_covers_each_non_python_context_with_its_minor_command():
    assert commands(plan_all(["web/src/api.ts"])) == ["web-test"]
    assert commands(plan_all(["workers/scan-proxy/src/scan.ts"])) == ["proxy-sanity"]
    assert commands(plan_all(["android/app/src/main/java/app/domain/Breakdown.kt"])) == ["gradle-jvm"]


def test_issue_level_runs_scan_proxy_major_when_its_dependency_changes():
    config = {**ALL, "contexts": {**ALL["contexts"]}}
    config["contexts"]["scan-proxy"] = {**ALL["contexts"]["scan-proxy"], "dependency_files": ["workers/scan-proxy/package.json"]}
    plan = tp.plan(["workers/scan-proxy/package.json"], config, MARKERS)
    assert commands(plan) == ["proxy-test"]


def test_a_python_dependency_change_does_not_touch_the_non_python_contexts():
    assert commands(plan_all(["uv.lock"])) == ["uv run pytest -m core", "uv run pytest -m streamlit"]


def test_issue_level_shared_interface_plans_the_sharing_contexts_side():
    out = commands(plan_all(["src/hdttools/api/breakdown.py"]))
    assert "web-test -- src/breakdown.test.ts" in out
    assert "gradle-jvm --tests Golden" in out


def test_changed_non_python_test_file_runs_first():
    plan = plan_all(["web/src/api.ts", "web/src/api.test.ts"])
    assert plan.selections[0].kind == "targeted"
    assert plan.selections[0].command == "web-test -- src/api.test.ts"


def test_live_test_files_are_never_planned():
    plan = plan_all(["web/src/external/auth.external.test.ts"])
    assert all("external" not in c for c in commands(plan))
    assert any("live" in n for n in plan.notes)


# Session end: the scope ladder

def test_session_end_one_small_diff_runs_the_file():
    plan = plan_all(["src/hdttools/database.py"], "session")
    assert plan.scope == "file"
    assert commands(plan) == ["uv run pytest tests/test_database.py"]


def test_session_end_file_scope_finds_each_contexts_test_for_the_file():
    assert commands(plan_all(["web/src/api.ts"], "session")) == ["web-test -- src/api.test.ts"]
    assert commands(plan_all(["workers/scan-proxy/src/scan.ts"], "session")) == ["proxy-file src/scan.test.ts"]
    assert commands(plan_all(["android/app/src/main/java/app/domain/Breakdown.kt"], "session")) == [
        "gradle-jvm --tests app.domain.BreakdownTest"
    ]


def test_session_end_file_without_a_test_falls_back_to_the_context():
    plan = plan_all(["web/src/untested.ts"], "session")
    assert plan.scope == "file"
    assert commands(plan) == ["web-test"]
    assert any("no test file" in n for n in plan.notes)


def test_session_end_larger_single_context_diff_runs_the_context():
    plan = plan_all(["web/src/a.ts", "web/src/b.ts", "web/src/c.ts"], "session")
    assert plan.scope == "context"
    assert commands(plan) == ["web-test"]


def test_session_end_diff_across_contexts_runs_the_application():
    plan = plan_all(["web/src/api.ts", "streamlit_app/app.py"], "session")
    assert plan.scope == "application"
    assert commands(plan) == ["uv run pytest", "web-test", "proxy-test", "gradle-jvm"]


def test_session_end_dependency_change_is_at_least_a_context_run():
    plan = plan_all(["web/package.json"], "session")
    assert plan.scope == "context"


def test_session_end_changed_python_test_file_is_run_even_alone():
    assert commands(plan_all(["tests/test_database.py"], "session")) == ["uv run pytest tests/test_database.py"]


# Android instrumented tests

def test_android_diff_outside_device_covered_code_excludes_instrumented_tests():
    for level in ("issue", "session"):
        plan = plan_all(["android/app/src/main/java/app/domain/Breakdown.kt"], level)
        assert "gradle-device" not in commands(plan), level
        assert any("instrumented" in n and "excluded" in n for n in plan.notes), level


def test_android_diff_touching_device_covered_code_adds_instrumented_tests():
    for level in ("issue", "session"):
        plan = plan_all(["android/app/src/main/java/app/ui/Home.kt"], level)
        assert "gradle-device" in commands(plan), level
        assert [s.kind for s in plan.selections if s.command == "gradle-device"] == ["device"]


def test_changing_an_instrumented_test_runs_the_instrumented_tests():
    assert "gradle-device" in commands(plan_all(["android/app/src/androidTest/java/app/ui/HomeTest.kt"]))


# Stale surfaces

def test_session_end_runs_a_stale_free_surface_of_a_touched_context():
    plan = plan_all(["web/src/api.ts"], "session", surfaces=SURFACES)
    surface = [s for s in plan.selections if s.kind == "surface"]
    assert [(s.command, s.action) for s in surface] == [("web-external", "run")]


def test_a_stale_paid_surface_is_listed_as_needing_confirmation_never_run():
    plan = plan_all(["workers/scan-proxy/src/scan.ts"], "session", surfaces=SURFACES)
    surface = [s for s in plan.selections if s.kind == "surface"]
    assert [(s.command, s.action) for s in surface] == [("proxy-external", "confirm")]


def test_fresh_surfaces_are_left_alone_and_planned_ones_are_only_noted():
    plan = plan_all(["android/app/src/main/java/app/domain/Breakdown.kt"], "session", surfaces=SURFACES)
    assert not [s for s in plan.selections if s.kind == "surface"]
    assert any("play-billing" in n for n in plan.notes)


def test_surfaces_of_untouched_contexts_are_not_planned():
    plan = plan_all(["web/src/api.ts"], "session", surfaces=SURFACES)
    assert all(s.command != "proxy-external" for s in plan.selections)


# Release

def test_release_lists_everything_for_each_releasable_context():
    plan = plan_all([], "release")
    out = commands(plan)
    assert {"proxy-test", "proxy-weekly", "gradle-jvm", "gradle-device"} <= set(out)
    assert "freshness --platform web" in out
    assert any("core" in n and "no full-run release" in n for n in plan.notes)


def test_release_includes_instrumented_tests_whatever_the_diff():
    assert "gradle-device" in commands(plan_all(["README.md"], "release"))


def test_release_marks_paid_old_suites_and_stale_paid_surfaces_as_needing_confirmation():
    plan = plan_all([], "release", surfaces=SURFACES)
    by_command = {s.command: s.action for s in plan.selections}
    assert by_command["proxy-weekly"] == "confirm"
    assert by_command["proxy-external"] == "confirm"
    assert by_command["web-external"] == "run"
    assert by_command["gradle-jvm"] == "run"


def test_release_can_be_limited_to_one_context():
    plan = plan_all([], "release", release_contexts=["android"])
    assert commands(plan) == ["gradle-jvm", "gradle-device"]


def test_release_of_a_context_without_a_full_run_says_so():
    plan = plan_all([], "release", release_contexts=["streamlit"])
    assert plan.selections == []
    assert any("streamlit" in n and "no full-run release" in n for n in plan.notes)


def test_main_prints_the_level_scope_and_confirmation_tag(capsys):
    fake = [{"name": "claude-vision", "state": "stale", "platforms": ["scan-proxy"], "paid": True}]
    assert tp.main(["--level", "release", "--context", "scan-proxy"], surfaces=lambda: fake) == 0
    out = capsys.readouterr().out
    assert "Release test plan" in out
    assert "[CONFIRM]" in out and "test-weekly.ps1" in out


def test_main_session_level_survives_unreadable_surface_freshness(capsys):
    def broken():
        raise RuntimeError("registry down")

    assert tp.main(["--level", "session", "--files", "streamlit_app/app.py"], surfaces=broken) == 0
    assert "surface freshness unavailable" in capsys.readouterr().out


# --- Command checks: each planned selection picks what the planner says ---


def _pytest_selections(plan):
    return [s for s in plan.selections if s.command.startswith("uv run pytest")]


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
    assert {c["marker"] for c in config["contexts"].values() if "marker" in c} <= markers


def test_real_config_interface_tests_exist():
    for iface in tp.load_config()["interfaces"]:
        for test in iface["tests"]:
            assert (ROOT / test).is_file(), test


def test_every_planned_selection_collects_tests_and_none_are_external(real_plan):
    assert real_plan.selections
    for sel in _pytest_selections(real_plan):
        ids = _collect(sel.command)
        assert ids, sel.command
        assert not any("test_claude_vision_external" in i for i in ids), sel.command


def test_planned_interface_selection_runs_exactly_its_test_file(real_plan):
    sels = [s for s in _pytest_selections(real_plan) if s.kind == "interface"]
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
