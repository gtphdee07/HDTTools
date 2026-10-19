"""Tests for the planner rules of #66: plan from each context's last verified commit,
queue the downstream contexts of a changed interface or dependency, and let docs-only
changes add nothing. A small fake context map, a fake ledger and a fake `git diff` stand in
for the real ones; one test reads a real ledger file written by the ledger's own `record`."""

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(_SCRIPTS))
_spec = importlib.util.spec_from_file_location("test_planner", _SCRIPTS / "test_planner.py")
tp = importlib.util.module_from_spec(_spec)
sys.modules["test_planner"] = tp
_spec.loader.exec_module(tp)
_ledger_spec = importlib.util.spec_from_file_location("verification_ledger", _SCRIPTS / "verification_ledger.py")
vl = importlib.util.module_from_spec(_ledger_spec)
sys.modules["verification_ledger"] = vl
_ledger_spec.loader.exec_module(vl)

MARKERS = {"external", "minor", "slow", "core", "streamlit"}
CONFIG = {
    "dependency_files": ["pyproject.toml"],
    "docs_globs": ["*.md", "docs/*"],
    "contexts": {
        "core": {"marker": "core", "paths": ["src/"], "file": "uv run pytest {file}", "test_for": [],
                 "context": "core-suite", "application": "all-python"},
        "streamlit": {"marker": "streamlit", "paths": ["app/"], "depends_on": ["core"], "file": "uv run pytest {file}",
                      "test_for": [], "context": "streamlit-suite", "application": "all-python"},
        "web": {"paths": ["web/"], "commands": {"minor": "web-minor", "major": "web-major"}, "file": "web-file {rel}",
                "test_for": [], "context": "web-suite"},
        "proxy": {"paths": ["proxy/"], "commands": {"minor": "proxy-minor", "major": "proxy-major"},
                  "file": "proxy-file {rel}", "test_for": [], "context": "proxy-suite"},
        "android": {"paths": ["android/"], "commands": {"minor": "android-minor", "major": "android-major"},
                    "file": "android-file {rel}", "test_for": [], "context": "android-suite"},
    },
    "interfaces": [
        {"name": "golden", "context": "core", "files": ["src/breakdown.py", "vectors/cases.json", "web/breakdown.ts"],
         "tests": ["tests/test_golden.py"], "shares_with": ["android", "web"],
         "shares_tests": {"web": "web-golden", "android": "android-golden"}},
        {"name": "proxy-http", "context": "proxy", "files": ["proxy/index.ts"], "tests": [], "shares_with": ["android"]},
    ],
}


def commands(plan):
    return [s.command for s in plan.selections]


def plan_for(files, level="issue", config=CONFIG):
    return tp.plan(files, config, MARKERS, level=level)


# --- Downstream contexts of a changed interface or dependency -------------------------------

def test_a_provider_side_interface_change_queues_the_sharing_context_that_has_no_precise_test():
    plan = plan_for(["proxy/index.ts"])

    assert commands(plan) == ["proxy-major", "android-major"]
    assert [s.reason for s in plan.selections][1] == "android Major (downstream of interface proxy-http; includes Minor)"


def test_a_downstream_context_with_a_named_interface_test_runs_that_test_instead_of_its_suite():
    plan = plan_for(["src/breakdown.py"])

    assert commands(plan) == ["uv run pytest -m core", "uv run pytest -m streamlit", "uv run pytest tests/test_golden.py",
                              "android-golden", "web-golden"]
    assert "web-major" not in commands(plan) and "android-major" not in commands(plan)


def test_a_consumer_side_change_does_not_queue_the_provider_context():
    plan = plan_for(["web/breakdown.ts"])

    assert "uv run pytest -m core" not in commands(plan)
    assert "android-major" not in commands(plan)


def test_a_consumer_side_change_does_not_queue_the_other_consumers_either():
    config = copy.deepcopy(CONFIG)
    del config["interfaces"][0]["shares_tests"]["android"]  # android would now fall back to its Major suite

    assert "android-major" in commands(plan_for(["src/breakdown.py"], config=config))
    assert "android-major" not in commands(plan_for(["web/breakdown.ts"], config=config))


def test_a_dependent_context_runs_its_major_suite_when_a_context_it_depends_on_changes():
    plan = plan_for(["src/database.py"])

    assert commands(plan) == ['uv run pytest -m "minor and core"', "uv run pytest -m streamlit"]
    assert plan.selections[1].reason == "streamlit Major (depends on core; includes Minor)"


def test_a_change_to_the_dependent_context_does_not_queue_what_it_depends_on():
    assert commands(plan_for(["app/main.py"])) == ['uv run pytest -m "minor and streamlit"']


def test_dependents_are_followed_transitively():
    config = copy.deepcopy(CONFIG)
    config["contexts"]["android"]["depends_on"] = ["streamlit"]

    plan = plan_for(["src/database.py"], config=config)

    assert commands(plan) == ['uv run pytest -m "minor and core"', "uv run pytest -m streamlit", "android-major"]


def test_a_dependency_with_globs_queues_the_dependent_only_for_the_files_it_imports():
    config = copy.deepcopy(CONFIG)
    config["contexts"]["streamlit"]["depends_on"] = {"core": ["src/lib/*"]}
    config["contexts"]["core"]["paths"] = ["src/", "tools/"]

    assert commands(plan_for(["src/lib/ocr.py"], config=config)) == ['uv run pytest -m "minor and core"', "uv run pytest -m streamlit"]
    assert commands(plan_for(["tools/build.py"], config=config)) == ['uv run pytest -m "minor and core"']
    assert commands(plan_for(["tools/build.py"], "session", config=config)) == ["core-suite"]


def test_a_context_already_touched_is_not_also_queued_as_downstream():
    plan = plan_for(["src/database.py", "app/main.py"])

    assert commands(plan) == ['uv run pytest -m "minor and core"', 'uv run pytest -m "minor and streamlit"']


def test_session_end_adds_the_downstream_contexts_run_to_the_touched_contexts_run():
    plan = plan_for(["proxy/index.ts"], "session")

    assert commands(plan) == ["proxy-suite", "android-suite"]
    assert [s.kind for s in plan.selections] == ["context", "downstream"]
    assert plan.scope == "file"  # the ladder counts the touched contexts only


def test_session_end_follows_a_context_dependency_to_the_dependent_context():
    assert commands(plan_for(["src/database.py"], "session")) == ["core-suite", "streamlit-suite"]


def test_an_application_run_already_covers_the_downstream_contexts():
    plan = plan_for(["src/database.py", "web/app.ts"], "session")

    assert plan.scope == "application"
    assert not [s for s in plan.selections if s.kind == "downstream"]


def test_a_shared_fixture_with_no_owner_queues_the_provider_and_every_sharing_context():
    plan = plan_for(["vectors/cases.json"], "session")

    assert sorted(commands(plan)) == sorted(["core-suite", "web-suite", "android-suite", "streamlit-suite"])


# --- Docs-only changes add nothing -----------------------------------------------------------

@pytest.mark.parametrize("level", ["issue", "session"])
def test_docs_only_changes_plan_nothing_even_inside_a_contexts_own_directory(level):
    plan = plan_for(["README.md", "docs/guide.md", "src/CONTEXT.md", "web/README.md", "app/notes.md"], level)

    assert plan.selections == []
    assert plan.notes == ["docs-only change; no tests planned"]


@pytest.mark.parametrize("level", ["issue", "session"])
def test_docs_beside_code_add_nothing_to_the_codes_plan(level):
    assert commands(plan_for(["src/database.py", "src/CONTEXT.md", "docs/guide.md"], level)) == commands(
        plan_for(["src/database.py"], level))


def test_docs_do_not_count_toward_the_size_of_the_diff():
    code_only = plan_for(["src/a.py"], "session")
    with_docs = plan_for(["src/a.py", "src/b.md", "src/c.md"], "session")

    assert code_only.scope == with_docs.scope == "file"


def test_a_docs_glob_is_only_what_the_config_names():
    config = copy.deepcopy(CONFIG)
    config["docs_globs"] = []

    assert commands(plan_for(["src/CONTEXT.md"], config=config)) != []


# --- Plan from each context's last verified commit -------------------------------------------

BASE = "HEAD"


class Repo:
    """Fake `git diff --name-only <ref>`: the files changed from each ref to the working tree."""

    def __init__(self, **changed_since):
        self.changed_since = changed_since
        self.asked = []

    def __call__(self, ref):
        self.asked.append(ref)
        value = self.changed_since.get(ref, [])
        if isinstance(value, Exception):
            raise value
        return value


def ledger(**commits):
    """A fake ledger: context -> last verified commit (the same commit at every level)."""
    return lambda context, level: commits.get(context)


def since_verified(repo, verified, level="issue", **kw):
    return tp.plan_since_verified(CONFIG, MARKERS, level=level, diff=repo, verified=verified, base=BASE, **kw)


ALL_AT = dict(core="old", streamlit="old", web="old", android="old", proxy="old")


def test_a_committed_but_unverified_change_is_planned_though_the_working_tree_is_clean():
    repo = Repo(old=["src/database.py"])  # committed after the last verified commit; HEAD itself diffs to nothing

    assert commands(plan_for([])) == []  # what the default mode plans
    assert commands(since_verified(repo, ledger(**ALL_AT))) == ['uv run pytest -m "minor and core"', "uv run pytest -m streamlit"]


def test_each_context_is_planned_from_its_own_last_verified_commit():
    repo = Repo(old=["src/database.py", "web/app.ts"], new=["web/page.ts"])
    verified = ledger(core="old", streamlit="old", web="new", android="new", proxy="new")

    plan = since_verified(repo, verified)

    # web/app.ts was committed before web's verified commit, so only web/page.ts is web's debt
    assert commands(plan) == ['uv run pytest -m "minor and core"', "uv run pytest -m streamlit", "web-minor"]
    assert sorted(set(repo.asked)) == ["new", "old"]


def test_a_context_verified_after_a_change_is_not_planned_for_it():
    repo = Repo(old=["web/app.ts"])  # nothing changed since the commit the web suite last passed at
    verified = ledger(core="old", streamlit="old", web="new", android="new", proxy="new")

    assert commands(since_verified(repo, verified)) == []


def test_a_downstream_context_verified_after_the_change_is_not_queued():
    repo = Repo(old=["src/database.py"])
    verified = ledger(core="old", streamlit="new", web="new", android="new", proxy="new")

    assert commands(since_verified(repo, verified)) == ['uv run pytest -m "minor and core"']


def test_an_interface_test_is_planned_only_for_the_sides_that_are_unverified():
    repo = Repo(old=["src/breakdown.py"])
    verified = ledger(core="old", streamlit="new", web="new", android="old", proxy="new")

    assert commands(since_verified(repo, verified)) == [
        "uv run pytest -m core", "uv run pytest tests/test_golden.py", "android-golden"]


def test_a_context_never_verified_is_planned_from_the_base_and_says_so():
    repo = Repo(**{BASE: ["web/app.ts"]})

    plan = since_verified(repo, ledger())

    assert commands(plan) == ["web-minor"]
    assert "web: never verified at the issue level; planned from HEAD" in plan.notes


def test_a_verified_commit_git_cannot_read_falls_back_to_the_base():
    repo = Repo(gone=tp.GitError("bad object"), **{BASE: ["web/app.ts"]})

    plan = since_verified(repo, ledger(web="gone"))

    assert "web-minor" in commands(plan)
    assert "web: last verified commit gone is not readable; planned from HEAD" in plan.notes


def test_an_unreadable_ledger_plans_every_context_from_the_base():
    def broken(context, level):
        raise RuntimeError("ledger is corrupt")

    plan = since_verified(Repo(**{BASE: ["web/app.ts"]}), broken)

    assert commands(plan) == ["web-minor"]
    assert any("ledger unavailable (ledger is corrupt)" in n for n in plan.notes)


def test_the_ledger_is_asked_for_the_planned_level():
    asked = []

    def verified(context, level):
        asked.append(level)

    since_verified(Repo(), verified, level="session")

    assert set(asked) == {"session"}


def test_a_fully_verified_tree_says_nothing_is_planned():
    plan = since_verified(Repo(), ledger(**ALL_AT))

    assert plan.selections == []
    assert "every context is verified up to date; nothing planned" in plan.notes


def test_docs_committed_since_the_verified_commit_add_nothing():
    plan = since_verified(Repo(old=["docs/guide.md", "src/CONTEXT.md"]), ledger(**ALL_AT))

    assert plan.selections == []


def test_docs_are_not_counted_among_the_files_changed_since_a_contexts_verified_commit():
    plan = since_verified(Repo(old=["src/CONTEXT.md", "src/database.py"]), ledger(**ALL_AT))

    assert "core: 1 file(s) changed since old" in plan.notes


def test_session_end_plans_from_the_verified_commits_with_downstream_contexts():
    repo = Repo(old=["proxy/index.ts"])

    plan = since_verified(repo, ledger(**ALL_AT), level="session")

    assert commands(plan) == ["proxy-suite", "android-suite"]


def test_a_commit_the_real_ledger_holds_is_the_one_the_planner_diffs_from(tmp_path):
    path = tmp_path / "ledger.json"
    vl.record("web", "issue", "pass", revision=vl.Revision("c" * 40, "t" * 40), path=path)
    repo = Repo(**{"c" * 40: ["web/app.ts"], BASE: ["src/database.py"]})

    plan = since_verified(repo, lambda c, l: vl.last_verified(c, l, path=path))

    assert "web-minor" in commands(plan)  # web: planned from the recorded commit
    assert "uv run pytest -m core" not in " ".join(commands(plan))  # others: never verified, planned from the base
    assert "c" * 40 in repo.asked


# --- The command line -------------------------------------------------------------------------

def test_main_since_verified_prints_the_plan_and_the_per_context_sources(capsys):
    repo = Repo(old=["src/hdttools/database.py"])

    code = tp.main(["--since-verified", "--level", "session"], git=repo, surfaces=lambda: [],
                   ledger=lambda: (lambda command: None),
                   verified=lambda context, level: "old")

    out = capsys.readouterr().out
    assert code == 0
    assert "Session-end test plan" in out
    assert "uv run pytest tests/test_database.py" in out
    assert 'uv run pytest -m "streamlit and not slow"' in out  # streamlit imports core
    assert "core: 1 file(s) changed since old" in out
    assert "web: nothing to verify since old" in out


def test_main_since_verified_is_ignored_for_a_release_and_for_explicit_files(capsys):
    repo = Repo()

    tp.main(["--since-verified", "--level", "release", "--context", "android"], git=repo, surfaces=lambda: [],
            ledger=lambda: (lambda c: None), verified=lambda c, l: pytest.fail("ledger must not be read"))
    release = capsys.readouterr().out
    tp.main(["--since-verified", "--files", "src/hdttools/database.py"], git=repo,
            ledger=lambda: (lambda c: None), verified=lambda c, l: pytest.fail("ledger must not be read"))
    explicit = capsys.readouterr().out

    assert "--since-verified ignored: a release plans everything" in release
    assert "--since-verified ignored: --files names the changed files" in explicit
    assert 'uv run pytest -m "minor and core' in explicit


def test_main_since_verified_never_blocks_when_git_fails(capsys):
    def broken(ref):
        raise tp.GitError("no repo")

    assert tp.main(["--since-verified"], git=broken, verified=lambda c, l: None) == 0
    assert "could not plan" in capsys.readouterr().out


# --- The shipped config ------------------------------------------------------------------------

REAL = tp.load_config()
REAL_MARKERS = tp.load_markers()


def real_commands(files, level="issue"):
    return commands(tp.plan(files, REAL, REAL_MARKERS, level=level))


def test_real_config_docs_only_changes_plan_nothing():
    for level in ("issue", "session"):
        assert real_commands(["src/hdttools/CONTEXT.md", "web/CONTEXT.md", "docs/agents/ticket-skills.md"], level) == []


def test_real_config_a_scan_proxy_http_change_queues_the_android_unit_tests():
    assert "android/gradlew -p android testDebugUnitTest" in real_commands(["workers/scan-proxy/src/request.ts"])
    assert "android/gradlew -p android testDebugUnitTest" in real_commands(["workers/scan-proxy/src/request.ts"], "session")


def test_real_config_a_core_change_queues_the_streamlit_tests_because_streamlit_imports_core():
    assert any("streamlit" in c for c in real_commands(["src/hdttools/ocr_common.py"]))
    assert any("streamlit" in c for c in real_commands(["src/hdttools/ocr_common.py"], "session"))


def test_real_config_a_scripts_change_does_not_queue_streamlit_which_never_imports_scripts():
    for level in ("issue", "session"):
        assert not any("streamlit" in c for c in real_commands(["scripts/coverage_lib.py"], level)), level


def test_real_config_every_depends_on_names_a_declared_context():
    contexts = REAL["contexts"]
    for name, ctx in contexts.items():
        assert set(ctx.get("depends_on", [])) <= set(contexts), name


def test_an_unowned_interface_file_does_not_queue_the_provider_that_is_already_verified():
    # vectors/cases.json belongs to no context; the interface's provider (core) is verified after
    # the change, and only the web side is behind. Core's own suite must not be planned.
    repo = Repo(old=["vectors/cases.json"])
    verified = ledger(core="new", streamlit="new", web="old", android="new", proxy="new")

    assert commands(since_verified(repo, verified)) == ["web-golden"]
