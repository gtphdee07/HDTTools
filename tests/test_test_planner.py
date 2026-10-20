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
            "files": ["src/hdttools/breakdown.py"],
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
    plan = plan_for(["src/hdttools/breakdown.py"])
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


@pytest.mark.parametrize("level", ["issue", "session"])
@pytest.mark.parametrize("helper", ["tests/_suite_ledger_helpers.py", "tests/conftest.py", "tests/__init__.py"])
def test_a_changed_test_helper_is_not_planned_as_a_test_file(helper, level):
    """pytest collects nothing from a helper module and exits 5, which a finish run reads as a failed suite."""
    assert not any(helper in command for command in commands(tp.plan([helper], CONFIG, MARKERS, level=level)))


@pytest.mark.parametrize("level", ["issue", "session"])
def test_a_deleted_test_file_is_not_planned_to_run(level):
    """A branch that deletes a test lists it as changed; pytest on a missing file exits 4, which a finish run reads as a failed suite (#135)."""
    plan = tp.plan(["tests/test_gone.py", "tests/test_here.py"], CONFIG, MARKERS, level=level,
                   file_exists=lambda p: p == "tests/test_here.py")
    joined = " ".join(commands(plan))
    assert "tests/test_here.py" in joined
    assert "tests/test_gone.py" not in joined


@pytest.mark.parametrize("level", ["issue", "session"])
def test_a_deleted_web_test_file_is_not_planned_to_run(level):
    """Same as the Python case above for a Web test (#135 deleted web/src/apiShape.test.ts): `npm test -- <missing file>` finds nothing and fails."""
    plan = tp.plan(["web/src/gone.test.ts", "web/src/here.test.ts"], ALL, MARKERS, level=level,
                   file_exists=lambda p: p == "web/src/here.test.ts")
    joined = " ".join(commands(plan))
    assert "here.test.ts" in joined
    assert "gone.test.ts" not in joined


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
    for files in (["uv.lock"], ["src/hdttools/breakdown.py"], [], ["nonsense/x.bin"]):
        assert tp.main(["--files", *files]) == 0
    assert "uv run pytest" in capsys.readouterr().out


def test_planner_exits_zero_even_when_git_fails(capsys):
    def broken_git(_):
        raise tp.GitError("no repo")

    assert tp.main([], git=broken_git) == 0
    assert "git" in capsys.readouterr().out.lower()


def test_main_prints_the_planned_commands(capsys):
    tp.main(["--files", "src/hdttools/database.py"])
    assert 'uv run pytest -m "minor and core and not slow"' in capsys.readouterr().out


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
            "device_covered": [
                "android/app/src/main/java/app/ui/*", "android/app/src/main/java/app/MainActivity.kt",
                "android/app/src/main/AndroidManifest.xml", "android/app/src/androidTest/*",
            ],
            "device_free": ["android/app/src/main/java/app/ui/Scan*.kt", "android/app/src/androidTest/*WeeklyTest.kt"],
            "device_full": [
                "android/app/src/main/java/app/ui/navigation/NavHost.kt", "android/app/src/main/java/app/ui/ViewModel.kt",
                "android/app/src/main/java/app/MainActivity.kt", "android/app/src/main/AndroidManifest.xml",
            ],
            "device_classes": {
                "command": "gradle-device --class {fqcn}",
                "map": [
                    {"from": "android/app/src/main/java/app/ui/screens/*Screen.kt",
                     "test": "android/app/src/androidTest/java/app/ui/screens/{stem}Test.kt"},
                    {"from": "android/app/src/main/java/app/ui/components/*.kt",
                     "test": "android/app/src/androidTest/java/app/ui/components/{stem}Test.kt"},
                    {"from": "android/app/src/androidTest/*Test.kt", "test": "{file}"},
                ],
            },
            "commands": {"minor": "gradle-jvm", "major": "gradle-jvm"},
            "device": "gradle-device",
            "session_end": "android-session-end",
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
            "files": ["src/hdttools/breakdown.py", "web/src/breakdown.ts"],
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
    "android/app/src/androidTest/java/app/ui/screens/HomeScreenTest.kt",
    "android/app/src/androidTest/java/app/ui/screens/DetailScreenTest.kt",
    "android/app/src/androidTest/java/app/ui/components/ChipTest.kt",
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
    out = commands(plan_all(["src/hdttools/breakdown.py"]))
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
    assert commands(plan_all(["android/app/src/main/java/app/domain/Breakdown.kt"], "session")) == ["android-session-end"]


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
    assert commands(plan) == ["uv run pytest", "web-test", "proxy-test", "android-session-end"]


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


# Android session end and instrumented tests chosen by what changed (#133)

MAIN = "android/app/src/main/java/app/"
ANDROID_TEST = "android/app/src/androidTest/java/app/"
SESSION_END = "android-session-end"
FULL = "gradle-device"
HOME_CLASS = "gradle-device --class app.ui.screens.HomeScreenTest"


def test_android_session_end_for_a_jvm_only_diff_is_the_session_end_command_and_no_instrumented_test():
    for changed in (MAIN + "domain/Breakdown.kt", MAIN + "data/Repo.kt", MAIN + "ui/ScanRetry.kt"):
        plan = plan_all([changed], "session")
        assert commands(plan) == [SESSION_END], changed


def test_android_session_end_command_replaces_the_file_context_and_application_runs():
    one_file = plan_all([MAIN + "domain/Breakdown.kt"], "session")
    several = plan_all([MAIN + "domain/A.kt", MAIN + "domain/B.kt", MAIN + "domain/C.kt"], "session")
    spanning = plan_all([MAIN + "domain/Breakdown.kt", "web/src/api.ts"], "session")
    assert (one_file.scope, commands(one_file)) == ("file", [SESSION_END])
    assert (several.scope, commands(several)) == ("context", [SESSION_END])
    assert spanning.scope == "application" and SESSION_END in commands(spanning)
    assert "gradle-jvm" not in commands(spanning)


def test_android_session_end_runs_for_a_downstream_android_change_too():
    plan = plan_all(["src/hdttools/breakdown.py"], "session")
    assert SESSION_END in commands(plan)


def test_android_issue_level_keeps_its_jvm_command():
    assert commands(plan_all([MAIN + "domain/Breakdown.kt"])) == ["gradle-jvm"]


def test_one_screen_file_lists_only_that_screens_instrumented_class():
    for level in ("issue", "session"):
        plan = plan_all([MAIN + "ui/screens/HomeScreen.kt"], level)
        assert [c for c in commands(plan) if "gradle-device" in c] == [HOME_CLASS], level
        assert [s.kind for s in plan.selections if s.command == HOME_CLASS] == ["device"]


def test_one_component_file_lists_only_that_components_instrumented_class():
    plan = plan_all([MAIN + "ui/components/Chip.kt"], "session")
    assert [c for c in commands(plan) if "gradle-device" in c] == ["gradle-device --class app.ui.components.ChipTest"]


def test_two_changed_screens_share_one_class_command():
    plan = plan_all([MAIN + "ui/screens/HomeScreen.kt", MAIN + "ui/screens/DetailScreen.kt"], "session")
    assert [c for c in commands(plan) if "gradle-device" in c] == [
        "gradle-device --class app.ui.screens.HomeScreenTest,app.ui.screens.DetailScreenTest"
    ]


def test_a_changed_instrumented_test_class_runs_that_class():
    plan = plan_all([ANDROID_TEST + "ui/screens/HomeScreenTest.kt"], "session")
    assert [c for c in commands(plan) if "gradle-device" in c] == [HOME_CLASS]


@pytest.mark.parametrize("changed", [
    MAIN + "ui/navigation/NavHost.kt",
    MAIN + "ui/ViewModel.kt",
    MAIN + "MainActivity.kt",
    "android/app/src/main/AndroidManifest.xml",
])
def test_navigation_view_model_activity_and_manifest_list_the_full_instrumented_suite(changed):
    for level in ("issue", "session"):
        assert [c for c in commands(plan_all([changed], level)) if "gradle-device" in c] == [FULL], level


def test_the_full_suite_wins_over_a_class_when_both_are_owed():
    plan = plan_all([MAIN + "ui/screens/HomeScreen.kt", MAIN + "ui/navigation/NavHost.kt"], "session")
    assert [c for c in commands(plan) if "gradle-device" in c] == [FULL]


@pytest.mark.parametrize("changed", [
    ANDROID_TEST + "testsupport/Helper.kt",            # an androidTest helper, not a test class
    MAIN + "ui/screens/GhostScreen.kt",                # a screen with no instrumented class
    MAIN + "ui/Home.kt",                               # a ui file no mapping entry places
    MAIN + "ui/components/Orphan.kt",                  # a component with no instrumented class
])
def test_a_changed_file_the_mapping_cannot_place_lists_the_full_suite(changed):
    assert [c for c in commands(plan_all([changed], "session")) if "gradle-device" in c] == [FULL]


def test_a_class_command_never_hides_an_unplaceable_file_next_to_it():
    plan = plan_all([MAIN + "ui/screens/HomeScreen.kt", MAIN + "ui/Home.kt"], "session")
    assert [c for c in commands(plan) if "gradle-device" in c] == [FULL]


def test_a_live_weekly_test_class_is_not_planned_as_an_instrumented_run():
    plan = plan_all([ANDROID_TEST + "ui/screens/PaywallScreenWeeklyTest.kt"], "session")
    assert not [c for c in commands(plan) if "gradle-device" in c]


def test_release_lists_the_full_instrumented_suite_once_and_no_level_lists_a_repeat_count():
    release = plan_all([], "release", release_contexts=["android"])
    assert commands(release).count(FULL) == 1
    every_plan = [release] + [
        plan_all([f], level) for level in ("issue", "session", "release")
        for f in (MAIN + "ui/navigation/NavHost.kt", MAIN + "ui/screens/HomeScreen.kt", MAIN + "domain/Breakdown.kt")
    ]
    for plan in every_plan:
        assert not [c for c in commands(plan) if "--runs" in c or "suite_loop" in c or "times" in c.lower()]


# The real config and the real source tree (the fake map above only proves the rule).

def _real_plan(files, level="session"):
    return tp.plan(files, tp.load_config(), tp.load_markers(), level=level)


REAL_MAIN = "android/app/src/main/java/com/rigcheck/app/"
REAL_FULL = "android/gradlew -p android connectedDebugAndroidTest"


def test_real_config_session_end_for_domain_code_is_the_documented_command():
    assert commands(_real_plan([REAL_MAIN + "domain/Breakdown.kt"])) == ["uv run scripts/android_session_end.py"]


def test_real_config_maps_a_screen_to_its_androidtest_class_with_the_documented_gradle_property():
    plan = _real_plan([REAL_MAIN + "ui/screens/AccountScreen.kt"])
    assert REAL_FULL + " -Pandroid.testInstrumentationRunnerArguments.class=com.rigcheck.app.ui.screens.AccountScreenTest" in commands(plan)
    assert REAL_FULL not in commands(plan)


def test_real_config_places_every_screen_that_has_an_instrumented_class_and_nothing_else_by_accident():
    screens = sorted(p.name for p in (ROOT / "android/app/src/main/java/com/rigcheck/app/ui/screens").glob("*Screen.kt"))
    for screen in screens:
        plan = _real_plan([REAL_MAIN + f"ui/screens/{screen}"])
        has_class = (ROOT / "android/app/src/androidTest/java/com/rigcheck/app/ui/screens" / screen.replace(".kt", "Test.kt")).is_file()
        device = [c for c in commands(plan) if "connectedDebugAndroidTest" in c]
        assert device == ([c for c in device if ".class=" in c] if has_class else [REAL_FULL]), screen


@pytest.mark.parametrize("changed", [
    "ui/navigation/RigCheckNavHost.kt", "ui/RigCheckViewModel.kt", "MainActivity.kt",
])
def test_real_config_lists_the_full_suite_for_navigation_view_model_and_activity(changed):
    assert REAL_FULL in commands(_real_plan([REAL_MAIN + changed]))


def test_real_config_lists_the_full_suite_for_the_manifest():
    assert REAL_FULL in commands(_real_plan(["android/app/src/main/AndroidManifest.xml"]))


def test_real_config_ui_logic_and_the_coverage_allow_list_need_no_device():
    for changed in (REAL_MAIN + "ui/ScanRetry.kt", REAL_MAIN + "data/ScanAttempts.kt", "android/coverage-logic.toml"):
        assert not [c for c in commands(_real_plan([changed])) if "connectedDebugAndroidTest" in c], changed


def test_real_config_the_paid_weekly_device_test_and_number_formatting_need_no_device_run():
    # A changed *WeeklyTest.kt must never map to its own class-level command: that class is the paid live scan.
    for changed in (
        "android/app/src/androidTest/java/com/rigcheck/app/ui/screens/PaywallScreenWeeklyTest.kt",
        REAL_MAIN + "ui/format/NumberFormatting.kt",
    ):
        assert not [c for c in commands(_real_plan([changed])) if "connectedDebugAndroidTest" in c], changed


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


# --- Skipping repeated runs (#128): the ledger marks each suite passed or run ---


def test_each_listed_suite_is_marked_passed_or_run_and_the_run_list_omits_the_passed_ones():
    plan = plan_all(["web/src/api.ts", "workers/scan-proxy/src/scan.ts", "android/app/src/main/java/app/domain/Breakdown.kt"],
                    level="session")
    passed = {"web-test": "a" * 40}

    marks = {v.selection.command: v.passed_tree for v in tp.verdicts(plan, passed.get)}

    assert marks["web-test"] == "a" * 40
    assert marks["android-session-end"] is None
    assert [s.command for s in tp.run_list(plan, passed.get)] == [c for c in commands(plan) if c != "web-test"]


def test_a_suite_that_needs_confirmation_is_never_on_the_run_list_even_when_not_passed():
    plan = plan_all([], "release", release_contexts=["scan-proxy"])

    listed = [s.command for s in tp.run_list(plan, lambda command: None)]

    assert "proxy-weekly" not in listed and "proxy-test" in listed


def test_main_prints_already_passed_at_the_tree_or_run_for_each_suite_and_the_remaining_list(capsys):
    tree = "abcdef12" + "0" * 32
    passed = {"npm --prefix web test": tree}
    tp.main(["--level", "session", "--files", "web/src/api.ts", "workers/scan-proxy/src/index.ts"],
            surfaces=lambda: [], ledger=lambda: passed.get)

    out = capsys.readouterr().out
    lines = {line.split("    # ")[0].split(". ", 1)[1]: line for line in out.splitlines() if "    # " in line}
    assert lines["npm --prefix web test"].endswith("-> already passed at abcdef12")
    assert lines["npm --prefix workers/scan-proxy test"].endswith("-> run")
    to_run = next(line for line in out.splitlines() if line.startswith("To run:"))
    assert "npm --prefix workers/scan-proxy test" in to_run and "npm --prefix web test" not in to_run


def test_main_says_nothing_is_left_to_run_when_every_suite_already_passed(capsys):
    tp.main(["--files", "web/src/api.ts"], surfaces=lambda: [], ledger=lambda: lambda command: "f" * 40)

    assert "To run: nothing" in capsys.readouterr().out


def test_main_marks_every_suite_run_when_the_ledger_cannot_be_read(capsys):
    def broken():
        raise RuntimeError("ledger is unreadable")

    assert tp.main(["--files", "src/hdttools/database.py"], ledger=broken) == 0

    out = capsys.readouterr().out
    assert "-> run" in out and "already passed" not in out
    assert "ledger unavailable" in out


def test_a_session_plan_records_which_contexts_each_suite_depends_on():
    plan = plan_all(["web/src/api.ts", "src/hdttools/database.py"], level="session")

    by_command = {s.command: s.contexts for s in plan.selections}

    assert by_command["web-test"] == ("web",)
    assert set(by_command["uv run pytest"]) == {"core", "streamlit"}  # one command planned for two contexts


WEB_SUITE = tp.Selection("context", "web-test", "web context run", contexts=("web",))
PYTHON_SUITE = tp.Selection("context", "uv run pytest -m core", "core context run", contexts=("core", "streamlit"))


@pytest.mark.parametrize("changed, affected", [
    (["docs/agents/ticket-skills.md"], False),               # docs only reach Python tests
    (["README.md"], False),
    (["tests/test_new.py"], False),                          # tests are Python
    (["web/src/api.ts"], True),
    (["workers/scan-proxy/src/scan.ts"], False),
    (["src/hdttools/database.py"], False),                   # Python code does not change the web suite
    (["web/src/breakdown.ts"], True),                        # an interface file shared with web
    (["src/hdttools/breakdown.py"], True),               # ...whose other side is Python
    (["test-vectors/breakdown_cases.json"], True),           # unowned and unknown: could be anything
    (["docs/x.md", "web/package.json"], True),
])
def test_a_web_suite_is_affected_only_by_files_it_can_depend_on(changed, affected):
    assert tp.suite_affected(WEB_SUITE, changed, ALL) is affected


@pytest.mark.parametrize("changed, affected", [
    (["docs/agents/ticket-skills.md"], True),
    (["tests/test_new.py"], True),
    (["pyproject.toml"], True),
    (["src/hdttools/database.py"], True),
    (["streamlit_app/app.py"], True),                        # the Python suites share one run
    (["web/src/api.ts"], True),                              # Python tests scan web and Android sources too
    (["android/app/src/main/java/app/domain/Breakdown.kt"], True),
    (["test-vectors/breakdown_cases.json"], True),
])
def test_a_python_suite_is_affected_by_any_changed_file(changed, affected):
    assert tp.suite_affected(PYTHON_SUITE, changed, ALL) is affected


def test_a_suite_with_no_known_dependencies_is_affected_by_any_change():
    assert tp.suite_affected(tp.Selection("targeted", "x", "r"), ["docs/a.md"], ALL) is True


def test_the_slow_tooling_tests_are_affected_by_the_non_python_files_that_trigger_them():
    """The tooling group is triggered by web/package.json and the like, files no Python context owns."""
    config = {**ALL, "slow": [{"name": "tooling", "triggers": ["scripts/*", "web/package.json"], "tests": ["tests/test_x.py"]}]}
    plan = tp.plan(["scripts/a.py"], config, MARKERS | {"slow"}, level="session")

    slow = next(s for s in plan.selections if s.kind == "slow")

    assert set(slow.contexts) == {"core", "streamlit"}
    for changed in ("web/package.json", "scripts/b.py", "android/app/build.gradle.kts"):
        assert tp.suite_affected(slow, [changed], config) is True, changed


# --- Command checks: each planned selection picks what the planner says ---


def _pytest_selections(plan):
    return [s for s in plan.selections if s.command.startswith("uv run pytest")]


def _collect(command: str) -> list[str]:
    args = shlex.split(command)
    assert args[:3] == ["uv", "run", "pytest"]
    rest = args[3:]
    if "-n" in rest:  # collecting needs no workers; starting them would only slow the check
        at = rest.index("-n")
        rest = rest[:at] + rest[at + 2:]
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", *rest],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return [line for line in out.splitlines() if "::" in line]


@pytest.fixture(scope="module")
def real_plan():
    config = tp.load_config()
    markers = tp.load_markers()
    return tp.plan(
        ["src/hdttools/breakdown.py", "src/hdttools/database.py", "streamlit_app/fields.py"],
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


@pytest.mark.slow
def test_every_planned_selection_collects_tests_and_none_are_external(real_plan):
    assert real_plan.selections
    for sel in _pytest_selections(real_plan):
        ids = _collect(sel.command)
        assert ids, sel.command
        assert not any("test_claude_vision_external" in i for i in ids), sel.command


@pytest.mark.slow
def test_planned_interface_selection_runs_exactly_its_test_file(real_plan):
    sels = [s for s in _pytest_selections(real_plan) if s.kind == "interface"]
    assert sels
    for sel in sels:
        files = {t for t in shlex.split(sel.command) if t.startswith("tests/")}
        assert {i.split("::")[0] for i in _collect(sel.command)} == files


@pytest.mark.slow
def test_minor_selection_is_a_strict_subset_of_the_same_contexts_major():
    minor = set(_collect('uv run pytest -m "minor and core"'))
    major = set(_collect("uv run pytest -m core"))
    assert minor and minor < major


@pytest.mark.slow
def test_streamlit_and_core_selections_do_not_overlap():
    assert not set(_collect("uv run pytest -m streamlit")) & set(_collect("uv run pytest -m core"))


# --- Slow tests are owed only when the diff touches what they check (#129) ---

SLOW_CONFIG = {
    **ALL,
    "slow": [
        {"name": "tooling", "triggers": ["scripts/*", "pyproject.toml"], "tests": ["tests/test_tooling.py"]},
        {"name": "ocr-photos", "triggers": ["src/hdttools/*_ocr.py", "ExampleDocs/*"], "tests": ["tests/test_photos.py", "tests/test_pools.py"]},
    ],
}
SLOW_ALL = tp.SLOW_PYTEST
TOOLING_OWED = SLOW_ALL + " tests/test_tooling.py"
PHOTOS_OWED = SLOW_ALL + " tests/test_photos.py tests/test_pools.py"


def plan_slow(files, level="issue", **kwargs):
    kwargs.setdefault("file_exists", lambda p: p in EXISTING_TESTS)
    return tp.plan(files, SLOW_CONFIG, MARKERS, level=level, **kwargs)


def slow_commands(plan):
    return [s.command for s in plan.selections if s.kind == "slow"]


def test_the_python_suites_leave_out_slow_tests_when_the_config_names_slow_groups():
    assert commands(plan_slow(["src/hdttools/database.py"])) == ['uv run pytest -m "minor and core and not slow"']
    assert commands(plan_slow(["streamlit_app/app.py"])) == ['uv run pytest -m "minor and streamlit and not slow"']
    assert commands(plan_slow(["uv.lock"])) == ['uv run pytest -m "core and not slow"', 'uv run pytest -m "streamlit and not slow"']


@pytest.mark.parametrize("level", ["issue", "session"])
def test_a_diff_that_touches_only_src_hdttools_owes_no_slow_test(level):
    plan = plan_slow(["src/hdttools/database.py", "src/hdttools/models.py"], level)
    assert slow_commands(plan) == []
    assert any("slow" in n for n in plan.notes)


@pytest.mark.parametrize("level", ["issue", "session"])
def test_changing_the_planner_owes_the_tooling_tests_and_not_the_photo_ones(level):
    assert slow_commands(plan_slow(["scripts/test_planner.py"], level)) == [TOOLING_OWED]


@pytest.mark.parametrize("level", ["issue", "session"])
def test_changing_ocr_code_or_a_photo_fixture_owes_the_photo_tests(level):
    assert slow_commands(plan_slow(["src/hdttools/truck_tag_ocr.py"], level)) == [PHOTOS_OWED]
    assert slow_commands(plan_slow(["ExampleDocs/AddieTag.jpg"], level)) == [PHOTOS_OWED]


def test_a_diff_matching_two_groups_owes_both():
    assert slow_commands(plan_slow(["pyproject.toml", "ExampleDocs/AddieTag.jpg"], "session")) == [TOOLING_OWED, PHOTOS_OWED]


def test_release_lists_every_slow_test_whatever_the_diff():
    assert slow_commands(plan_slow([], "release")) == [SLOW_ALL]
    assert slow_commands(plan_slow([], "release", release_contexts=["android"])) == [SLOW_ALL]


def test_every_slow_command_repeats_not_external_because_a_second_m_replaces_addopts():
    assert tp.SLOW_PYTEST.endswith('-m "slow and not external"')
    for level in ("issue", "session", "release"):
        for command in slow_commands(plan_slow(["scripts/test_planner.py", "ExampleDocs/GooseTag.jpg"], level)):
            assert '"slow and not external"' in command


def test_a_config_without_slow_groups_plans_no_slow_selection():
    assert slow_commands(plan_all(["scripts/test_planner.py"])) == []
    assert slow_commands(plan_all([], "release")) == []


# Real config: the criteria of #129 against scripts/test_planner_config.json.

REAL_TOOLING_TESTS = {
    "tests/test_test_planner.py",
    "tests/test_context_test_commands.py",
    "tests/test_android_file_command_slow.py",
}


def real_slow(files, level):
    return slow_commands(tp.plan(files, tp.load_config(), tp.load_markers(), level=level))


def named_test_files(command):
    return {t for t in shlex.split(command) if t.startswith("tests/")}


@pytest.mark.parametrize("level", ["issue", "session"])
def test_real_config_owes_no_slow_test_for_a_src_hdttools_only_diff(level):
    assert real_slow(["src/hdttools/database.py"], level) == []
    assert real_slow(["src/hdttools/models.py", "src/hdttools/scale_ticket.py"], level) == []


@pytest.mark.parametrize("level", ["issue", "session"])
@pytest.mark.parametrize("changed", ["scripts/test_planner.py", "scripts/test_planner_config.json", "pyproject.toml"])
def test_real_config_owes_the_tooling_tests_when_the_planner_or_pyproject_change(level, changed):
    (command,) = real_slow([changed], level)
    assert REAL_TOOLING_TESTS <= named_test_files(command)


@pytest.mark.parametrize("level", ["issue", "session"])
@pytest.mark.parametrize("changed", ["src/hdttools/truck_tag_ocr.py", "src/hdttools/ocr_common.py", "ExampleDocs/GooseTag.jpg", "ExampleDocs/golden_fields.json"])
def test_real_config_owes_the_ocr_tests_when_ocr_code_or_photo_fixtures_change(level, changed):
    files = set().union(*(named_test_files(c) for c in real_slow([changed], level)))
    assert {"tests/test_real_photo_ocr_accuracy.py", "tests/test_scale_ticket_real_photo.py", "tests/test_streamlit_app.py"} <= files
    assert not files & REAL_TOOLING_TESTS


def test_real_config_lists_all_slow_tests_at_release():
    assert real_slow([], "release") == [SLOW_ALL]


def test_real_config_python_context_and_application_commands_leave_out_slow_tests():
    contexts = tp.load_config()["contexts"]
    for name in ("core", "streamlit"):
        for key in ("context", "application"):
            assert "not slow" in contexts[name][key], (name, key)


@pytest.mark.slow
def test_a_bare_uv_run_pytest_still_collects_the_slow_tests():
    bare = {i.split("::")[0] for i in _collect("uv run pytest")}
    slow = {i.split("::")[0] for i in _collect('uv run pytest -m "slow and not external"')}
    assert slow and slow <= bare
    assert "tests/test_android_file_command_slow.py" in bare


def test_the_root_testing_doc_states_the_parallel_command_and_every_slow_group_trigger():
    doc = (ROOT / "TESTING.md").read_text(encoding="utf-8")
    section = doc.split("## Python test commands", 1)[1].split("\n## ", 1)[0]
    assert "uv run pytest -n auto" in section
    assert tp.SLOW_PYTEST in section
    for trigger in ("scripts/", "pyproject.toml", "ExampleDocs/", "streamlit_app/", "hdttools/breakdown.py", "_ocr.py"):
        assert trigger in section, trigger


@pytest.mark.slow
def test_every_slow_marked_test_file_is_named_by_a_real_config_group():
    named = {t for group in tp.load_config()["slow"] for t in group["tests"]}
    marked = {i.split("::")[0] for i in _collect('uv run pytest -m "slow and not external"')}
    assert marked and marked <= named, sorted(marked - named)
    assert all((ROOT / t).is_file() for t in named)
