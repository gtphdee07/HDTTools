"""Tests for the session-start verification debt report of #67 (scripts/verification_debt.py).

A small fake context map, a fake `git diff` (ref to changed files) and a fake ledger (context to
last verified commit and time) stand in for the real ones. One test reads a ledger file written by
the ledger's own `record`, so the report and the ledger agree on the timestamp format. The setup
document is checked against the script it tells the owner to hook up."""

import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(_SCRIPTS))


def _load(name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


tp = _load("test_planner")
vl = _load("verification_ledger")
vd = _load("verification_debt")

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
        "android": {"paths": ["android/"], "commands": {"minor": "android-minor", "major": "android-major"},
                    "file": "android-file {rel}", "test_for": [], "context": "android-suite",
                    "session_end": "android-session-end"},
    },
    "interfaces": [
        {"name": "golden", "context": "core", "files": ["src/breakdown.py"],
         "tests": ["tests/test_golden.py"], "shares_with": ["web"], "shares_tests": {"web": "web-golden"}},
    ],
}
NOW = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)
LIMITS = vd.Limits(max_files=15, max_age_days=7)


class Repo:
    """Fake `git diff --name-only <ref>`: the files changed from each ref to the working tree."""

    def __init__(self, **changed_since):
        self.changed_since = changed_since

    def __call__(self, ref):
        value = self.changed_since.get(ref, [])
        if isinstance(value, Exception):
            raise value
        return value


def report_for(repo, commits, *, stamps=None, limits=LIMITS, passed_at=lambda c: None, config=CONFIG):
    stamps = stamps or {}
    return vd.build(config, MARKERS, level="session", limits=limits, diff=repo,
                    verified=lambda context, level: commits.get(context),
                    verified_at=lambda context, level: stamps.get(context), now=NOW, passed_at=passed_at)


def text_for(*args, **kw):
    limits = kw.get("limits", LIMITS)
    return vd.render(report_for(*args, **kw), limits)


ALL_AT = dict(core="old", streamlit="old", web="old", android="old")


# --- The debt: changed files per context since the last verified commit ----------------------

def test_the_debt_names_each_contexts_changed_files_and_the_commit_they_are_measured_from():
    text = text_for(Repo(old=["src/database.py", "web/app.ts"]), {**ALL_AT, "android": "abcdef0123456789"})

    assert "core: 1 file(s) changed since old" in text and "own: src/database.py" in text
    assert "web: 1 file(s) changed since old" in text and "own: web/app.ts" in text


def test_each_context_is_measured_from_its_own_last_verified_commit():
    repo = Repo(old=["src/database.py", "web/app.ts"], new=["web/page.ts"])

    report = report_for(repo, dict(core="old", streamlit="old", web="new", android="new"))

    by_name = {d.name: d for d in report.debts}
    assert by_name["core"].own == ["src/database.py"]
    assert by_name["web"].own == ["web/page.ts"]  # web/app.ts predates web's verified commit
    assert by_name["web"].since == "new"


def test_a_clean_ledger_with_nothing_changed_says_there_is_no_debt():
    text = text_for(Repo(), ALL_AT)

    assert "none: no context has changes since its last recorded pass." in text
    assert "Recommended" not in text and "Tests owed" not in text


def test_files_that_reach_a_context_from_another_are_shown_with_where_they_live():
    text = text_for(Repo(old=["src/breakdown.py"]), ALL_AT)

    assert "streamlit: 1 file(s)" in text and "from core: src/breakdown.py" in text  # streamlit depends on core
    assert "web: 1 file(s)" in text  # web shares the golden-vector interface core provides
    assert "android: " not in text.split("Tests owed")[0]  # android shares nothing with this change


def test_docs_only_changes_add_no_debt():
    text = text_for(Repo(old=["README.md", "docs/notes.txt", "src/CONTEXT.md"]), ALL_AT)

    assert "none: no context has changes" in text


def test_a_long_list_of_files_is_cut_short_with_a_count():
    repo = Repo(old=[f"web/f{i}.ts" for i in range(9)])

    text = text_for(repo, ALL_AT)

    assert "web/f0.ts, web/f1.ts, web/f2.ts, web/f3.ts, web/f4.ts (+4 more)" in text


# --- Contexts with no recorded pass ----------------------------------------------------------

def test_a_context_with_no_recorded_pass_is_named_but_not_counted_or_nudged():
    repo = Repo(old=["src/database.py"], HEAD=["web/uncommitted.ts"] * 40)  # 40 uncommitted web files, no web record

    report = report_for(repo, dict(core="old", streamlit="old", android="old"), limits=vd.Limits(max_files=3, max_age_days=0))

    assert report.no_record == ["web"]
    assert [d.name for d in report.debts] == ["core", "streamlit"]
    assert report.nudges == []
    assert "No recorded session-level pass for: web" in vd.render(report, LIMITS)


def test_with_no_record_at_all_the_report_says_so_instead_of_claiming_everything_is_verified():
    text = text_for(Repo(HEAD=["src/a.py"]), {})

    assert "No recorded session-level pass for: core, streamlit, web, android" in text
    assert "is verified up to date" not in text


# --- The tests owed ---------------------------------------------------------------------------

def test_the_report_lists_the_tests_the_planner_says_are_owed_for_the_debt():
    report = report_for(Repo(old=["web/app.ts"]), ALL_AT)

    assert [s.command for s in report.owed] == ["web-suite"]


def test_a_suite_that_already_passed_at_this_tree_is_not_listed_as_owed():
    report = report_for(Repo(old=["web/app.ts", "src/database.py"]), ALL_AT, passed_at=lambda c: "tree" if c == "web-suite" else None)

    commands = [s.command for s in report.owed]
    assert "web-suite" not in commands and commands  # core's suites are still owed


def test_a_downstream_context_adds_its_tests_to_what_is_owed():
    commands = [s.command for s in report_for(Repo(old=["src/breakdown.py"]), ALL_AT).owed]

    assert commands == ["core-suite", "streamlit-suite", "web-suite"]  # streamlit depends on core; web shares its interface


# --- The recommendation ----------------------------------------------------------------------

def test_below_both_limits_there_is_no_recommendation():
    report = report_for(Repo(old=["web/a.ts", "web/b.ts"]), ALL_AT, limits=vd.Limits(max_files=3, max_age_days=7),
                        stamps={"web": "2026-10-19T12:00:00Z"})

    assert report.nudges == []


def test_at_the_size_limit_it_recommends_a_context_level_run_through_the_ledger():
    repo = Repo(old=[f"web/f{i}.ts" for i in range(3)])

    text = text_for(repo, ALL_AT, limits=vd.Limits(max_files=3, max_age_days=0))

    assert "Recommended: catch up web with a context-level run, 3 unverified files (limit 3)" in text
    assert "uv run scripts/verification_ledger.py run --context web --level session -- web-suite" in text


def test_the_recommendation_uses_the_contexts_whole_session_command():
    repo = Repo(old=[f"android/f{i}.kt" for i in range(2)])

    nudges = report_for(repo, ALL_AT, limits=vd.Limits(max_files=2, max_age_days=0)).nudges

    assert [(n.context, n.command) for n in nudges] == [("android", "android-session-end")]


def test_past_the_age_limit_with_changes_it_recommends_and_says_how_long_ago():
    report = report_for(Repo(old=["web/a.ts"]), ALL_AT, limits=vd.Limits(max_files=0, max_age_days=7),
                        stamps={"web": "2026-10-10T12:00:00Z"})

    assert [n.context for n in report.nudges] == ["web"]
    assert report.nudges[0].reasons == ["last verified 10 days ago (limit 7 days)"]


def test_an_old_pass_with_nothing_changed_since_is_not_debt():
    report = report_for(Repo(), ALL_AT, stamps={"web": "2026-01-01T00:00:00Z"})

    assert report.nudges == [] and report.debts == []


def test_a_limit_of_zero_switches_that_limit_off():
    repo = Repo(old=[f"web/f{i}.ts" for i in range(50)])

    report = report_for(repo, ALL_AT, limits=vd.Limits(max_files=0, max_age_days=0), stamps={"web": "2020-01-01T00:00:00Z"})

    assert report.nudges == []


def test_a_timestamp_the_report_cannot_read_leaves_the_size_limit_working():
    repo = Repo(old=[f"web/f{i}.ts" for i in range(3)])

    report = report_for(repo, ALL_AT, limits=vd.Limits(max_files=3, max_age_days=1), stamps={"web": "not a date"})

    assert [n.reasons for n in report.nudges] == [["3 unverified files (limit 3)"]]


def test_the_age_comes_from_the_real_ledgers_own_timestamp(tmp_path):
    path = tmp_path / "ledger.json"
    vl.record("web", "session", "pass", revision=vl.Revision("old", "treeold"), path=path, now="2026-10-10T12:00:00Z")

    report = vd.build(CONFIG, MARKERS, level="session", limits=LIMITS, diff=Repo(old=["web/a.ts"]),
                      verified=lambda c, lv: vl.last_verified(c, lv, path=path),
                      verified_at=lambda c, lv: vl.last_verified_at(c, lv, path=path), now=NOW)

    assert [(n.context, n.reasons) for n in report.nudges] == [("web", ["last verified 10 days ago (limit 7 days)"])]
    assert report.no_record == ["core", "streamlit", "android"]


# --- The limits are configurable --------------------------------------------------------------

def test_the_limits_come_from_the_config_and_default_when_it_names_none():
    assert vd.load_limits({"debt": {"level": "release", "max_files": 4, "max_age_days": 2}}) == ("release", vd.Limits(4, 2))
    assert vd.load_limits({}) == ("session", vd.Limits(15, 7))


def test_the_shipped_config_sets_both_limits_as_whole_numbers():
    config = tp.load_config()

    level, limits = vd.load_limits(config)

    assert level in tp.LEVELS
    assert isinstance(config["debt"]["max_files"], int) and isinstance(config["debt"]["max_age_days"], int)
    assert limits.max_files > 0 and limits.max_age_days > 0


def run_main(argv, **kw):
    lines = []
    kw.setdefault("git", Repo())
    kw.setdefault("verified", lambda c, lv: "old")
    kw.setdefault("verified_at", lambda c, lv: None)
    kw.setdefault("ledger", lambda: (lambda command: None))
    code = vd.main(argv, out=lines.append, now=NOW, **kw)
    return code, "\n".join(lines)


def test_a_command_line_limit_overrides_the_config_for_one_run(monkeypatch):
    monkeypatch.setattr(tp, "load_config", lambda *a, **k: CONFIG | {"debt": {"max_files": 100, "max_age_days": 0}})
    git = Repo(old=["web/a.ts", "web/b.ts"])

    _, quiet = run_main([], git=git)
    _, loud = run_main(["--max-files", "2"], git=git)

    assert "Recommended" not in quiet and "Recommended: catch up web" in loud


# --- It never blocks and never runs tests -----------------------------------------------------

def test_the_hook_prints_one_json_object_the_owner_and_claude_both_get():
    code, out = run_main(["--hook"], git=Repo(old=["web/a.ts"]))

    data = json.loads(out)
    assert code == 0
    assert "web: 1 file(s) changed" in data["systemMessage"]
    assert data["hookSpecificOutput"] == {"hookEventName": "SessionStart", "additionalContext": data["systemMessage"]}


def test_when_nothing_is_owed_the_hook_still_says_there_is_no_debt():
    _, out = run_main(["--hook"], git=Repo())

    assert "none" in json.loads(out)["systemMessage"]


@pytest.mark.parametrize("hook", [[], ["--hook"]])
def test_a_git_failure_is_reported_and_exits_zero(hook):
    def broken(ref):
        raise tp.GitError("not a git repository")

    code, out = run_main(hook, git=broken, verified=lambda c, lv: None)

    assert code == 0 and "unavailable" in out


@pytest.mark.parametrize("hook", [[], ["--hook"]])
def test_an_unreadable_ledger_is_reported_and_exits_zero(hook):
    def unreadable(context, level):
        raise vl.LedgerError("verification ledger is unreadable")

    code, out = run_main(hook, verified=unreadable)

    assert code == 0 and "ledger unavailable" in out


def test_a_broken_suite_lookup_does_not_stop_the_report():
    def broken():
        raise RuntimeError("no git")

    code, out = run_main([], git=Repo(old=["web/a.ts"]), ledger=broken)

    assert code == 0 and "web: 1 file(s) changed" in out


def test_a_bad_argument_exits_zero():
    code, out = run_main(["--max-files", "many"])

    assert code == 0 and "bad arguments" in out


def test_a_stray_argument_is_ignored():
    code, out = run_main(["--hook", "--something-new"], git=Repo())

    assert code == 0 and json.loads(out)["systemMessage"]


def test_building_the_report_starts_no_process(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError(f"started a process: {args}")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)

    code, out = run_main([], git=Repo(old=[f"web/f{i}.ts" for i in range(20)]))

    assert code == 0 and "Recommended" in out  # past the limit, and it only printed the command


def test_the_ledger_is_read_not_written(tmp_path):
    path = tmp_path / "ledger.json"
    vl.record("web", "session", "pass", revision=vl.Revision("old", "t"), path=path, now="2026-10-10T12:00:00Z")
    before = path.read_bytes()

    vd.build(CONFIG, MARKERS, level="session", limits=LIMITS, diff=Repo(old=["web/a.ts"] * 30),
             verified=lambda c, lv: vl.last_verified(c, lv, path=path),
             verified_at=lambda c, lv: vl.last_verified_at(c, lv, path=path), now=NOW)

    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["ledger.json"]


# --- The setup document -----------------------------------------------------------------------

DOC = ROOT / "docs" / "agents" / "verification-debt.md"


def test_the_setup_document_gives_a_session_start_hook_that_calls_the_script():
    text = DOC.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)```", text, re.S)

    hooks = [json.loads(b)["hooks"]["SessionStart"] for b in blocks if '"SessionStart"' in b]

    assert hooks, "the document has no SessionStart settings snippet"
    command = hooks[0][0]["hooks"][0]["command"]
    assert hooks[0][0]["hooks"][0]["type"] == "command" and isinstance(hooks[0][0]["hooks"][0]["timeout"], int)
    assert "scripts/verification_debt.py" in command and "--hook" in command
    assert (ROOT / "scripts" / "verification_debt.py").is_file()


def test_the_setup_document_names_where_the_limits_are_set():
    text = DOC.read_text(encoding="utf-8")

    assert "scripts/test_planner_config.json" in text
    assert "max_files" in text and "max_age_days" in text
