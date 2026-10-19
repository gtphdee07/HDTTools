"""Function tests for scripts/verification_ledger.py (#65): the local ledger
of the last commit whose suites passed, per context and level. Fake git and
a fake command runner stand in for the real ones; the ledger file lives in
tmp_path."""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
_spec = importlib.util.spec_from_file_location("verification_ledger", _SCRIPTS / "verification_ledger.py")
vl = importlib.util.module_from_spec(_spec)
sys.modules["verification_ledger"] = vl
_spec.loader.exec_module(vl)

SHA_A = "a" * 40
SHA_B = "b" * 40


class FakeGit:
    """HEAD and tree state; `on_run` lets a test move HEAD or dirty the tree mid-run."""

    def __init__(self, head=SHA_A, clean=True):
        self.head_sha = head
        self.clean = clean

    def head(self) -> str:
        return self.head_sha

    def is_clean(self) -> bool:
        return self.clean


class FakeRunner:
    def __init__(self, code=0, git=None, during=None, error=None):
        self.code = code
        self.calls: list[list[str]] = []
        self.git = git
        self.during = during
        self.error = error

    def __call__(self, command, cwd=None):
        self.calls.append(list(command))
        if self.error:
            raise self.error
        if self.during:
            self.during(self.git)
        return SimpleNamespace(returncode=self.code)


@pytest.fixture
def ledger_path(tmp_path):
    return tmp_path / "ledger.json"


def run(ledger_path, *, git=None, runner=None, context="core", level="session", command=("echo", "ok"), now="t1"):
    git = git or FakeGit()
    runner = runner or FakeRunner()
    result = vl.run_and_record(
        context, level, list(command), path=ledger_path, git=git, run_command=runner, now=now, out=lambda _: None
    )
    return result, runner


def status(ledger_path, commit=SHA_A, context="core", level="session"):
    return vl.status(context, level, commit, path=ledger_path)


def test_a_passing_run_records_its_commit_for_the_context_and_level(ledger_path):
    result, runner = run(ledger_path, context="web", level="issue")

    assert result == 0
    assert runner.calls == [["echo", "ok"]]
    assert status(ledger_path, SHA_A, "web", "issue") == vl.VERIFIED
    assert vl.last_verified("web", "issue", path=ledger_path) == SHA_A


def test_levels_and_contexts_are_recorded_independently(ledger_path):
    run(ledger_path, context="web", level="issue")

    assert status(ledger_path, SHA_A, "web", "session") == vl.UNVERIFIED
    assert status(ledger_path, SHA_A, "core", "issue") == vl.UNVERIFIED


def test_a_later_pass_replaces_the_commit(ledger_path):
    run(ledger_path, git=FakeGit(SHA_A))
    run(ledger_path, git=FakeGit(SHA_B))

    assert vl.last_verified("core", "session", path=ledger_path) == SHA_B


def test_a_failed_run_leaves_the_previous_record_untouched(ledger_path):
    run(ledger_path, git=FakeGit(SHA_A))
    before = ledger_path.read_text(encoding="utf-8")

    result, _ = run(ledger_path, git=FakeGit(SHA_B), runner=FakeRunner(code=1), now="t2")

    assert result == 1
    assert ledger_path.read_text(encoding="utf-8") == before
    assert vl.last_verified("core", "session", path=ledger_path) == SHA_A


def test_a_failed_run_with_no_previous_record_creates_none(ledger_path):
    result, _ = run(ledger_path, runner=FakeRunner(code=2))

    assert result == 2
    assert not ledger_path.exists()
    assert status(ledger_path) == vl.UNVERIFIED


def test_a_run_that_cannot_start_is_skipped_and_leaves_the_record_untouched(ledger_path):
    run(ledger_path, git=FakeGit(SHA_A))
    before = ledger_path.read_text(encoding="utf-8")

    result, _ = run(ledger_path, git=FakeGit(SHA_B), runner=FakeRunner(error=FileNotFoundError("npm")))

    assert result != 0
    assert ledger_path.read_text(encoding="utf-8") == before


def test_an_explicit_skip_is_never_recorded_as_a_pass(ledger_path):
    run(ledger_path, git=FakeGit(SHA_A))
    before = ledger_path.read_text(encoding="utf-8")

    vl.record("core", "session", "skipped", path=ledger_path, git=FakeGit(SHA_B), now="t2")

    assert ledger_path.read_text(encoding="utf-8") == before
    assert status(ledger_path, SHA_B) == vl.STALE


def test_a_failure_outcome_is_never_recorded_as_a_pass(ledger_path):
    vl.record("core", "session", "fail", path=ledger_path, git=FakeGit(SHA_B), now="t2")

    assert not ledger_path.exists()


def test_a_pass_is_valid_only_for_the_commit_it_ran_at(ledger_path):
    run(ledger_path, git=FakeGit(SHA_A))

    assert status(ledger_path, SHA_A) == vl.VERIFIED
    assert status(ledger_path, SHA_B) == vl.STALE
    assert vl.is_verified("core", "session", SHA_A, path=ledger_path) is True
    assert vl.is_verified("core", "session", SHA_B, path=ledger_path) is False


def test_a_context_never_run_is_unverified_even_with_no_ledger_file(ledger_path):
    assert not ledger_path.exists()
    assert status(ledger_path) == vl.UNVERIFIED
    assert vl.is_verified("core", "session", SHA_A, path=ledger_path) is False
    assert vl.last_verified("core", "session", path=ledger_path) is None


def test_a_run_on_a_dirty_tree_is_not_recorded(ledger_path):
    result, runner = run(ledger_path, git=FakeGit(SHA_A, clean=False))

    assert result == 0  # the suite's own result is passed through
    assert runner.calls
    assert not ledger_path.exists()


def test_a_run_during_which_head_moved_is_not_recorded(ledger_path):
    git = FakeGit(SHA_A)
    runner = FakeRunner(git=git, during=lambda g: setattr(g, "head_sha", SHA_B))

    result, _ = run(ledger_path, git=git, runner=runner)

    assert result == 0
    assert not ledger_path.exists()


def test_a_run_that_dirtied_the_tree_is_not_recorded(ledger_path):
    git = FakeGit(SHA_A)
    runner = FakeRunner(git=git, during=lambda g: setattr(g, "clean", False))

    run(ledger_path, git=git, runner=runner)

    assert not ledger_path.exists()


def test_an_unknown_level_or_context_is_rejected_without_running(ledger_path):
    runner = FakeRunner()

    with pytest.raises(ValueError):
        vl.run_and_record("core", "weekly", ["x"], path=ledger_path, git=FakeGit(), run_command=runner)
    with pytest.raises(ValueError):
        vl.run_and_record("nowhere", "issue", ["x"], path=ledger_path, git=FakeGit(), run_command=runner)

    assert runner.calls == []


def test_an_unreadable_ledger_is_reported_and_never_overwritten(ledger_path):
    ledger_path.write_text("{not json", encoding="utf-8")

    with pytest.raises(vl.LedgerError):
        vl.status("core", "session", SHA_A, path=ledger_path)
    with pytest.raises(vl.LedgerError):
        run(ledger_path)

    assert ledger_path.read_text(encoding="utf-8") == "{not json"


def test_the_ledger_file_holds_commit_time_and_command_per_context_and_level(ledger_path):
    run(ledger_path, context="android", level="release", command=("gradlew", "test"), now="2026-10-18T10:00:00Z")

    data = json.loads(ledger_path.read_text(encoding="utf-8"))
    entry = data["contexts"]["android"]["release"]
    assert entry["commit"] == SHA_A
    assert entry["timestamp"] == "2026-10-18T10:00:00Z"
    assert entry["command"] == "gradlew test"


def test_the_default_ledger_lives_inside_the_git_dir_so_it_is_never_tracked(tmp_path):
    git = SimpleNamespace(common_dir=lambda: tmp_path / ".git")

    assert vl.default_ledger_path(git) == tmp_path / ".git" / "hdttools-verification-ledger.json"


def test_cli_run_passes_the_command_exit_code_through(ledger_path):
    git = FakeGit()
    code = vl.main(
        ["run", "--context", "core", "--level", "issue", "--", "echo", "ok"],
        path=ledger_path, git=git, run_command=FakeRunner(code=3), out=lambda _: None,
    )

    assert code == 3
    assert not ledger_path.exists()


def test_cli_check_exits_zero_only_when_verified_at_head(ledger_path):
    lines: list[str] = []
    args = ["check", "--context", "core", "--level", "session"]
    assert vl.main(args, path=ledger_path, git=FakeGit(SHA_A), out=lines.append) == 1

    run(ledger_path, git=FakeGit(SHA_A))
    assert vl.main(args, path=ledger_path, git=FakeGit(SHA_A), out=lines.append) == 0
    assert vl.main(args, path=ledger_path, git=FakeGit(SHA_B), out=lines.append) == 1
    assert any("verified" in line for line in lines)


def test_cli_show_lists_every_recorded_entry(ledger_path):
    run(ledger_path, context="web", level="issue")
    lines: list[str] = []

    assert vl.main(["show"], path=ledger_path, git=FakeGit(SHA_B), out=lines.append) == 0

    text = "\n".join(lines)
    assert "web" in text and "issue" in text and SHA_A[:8] in text
