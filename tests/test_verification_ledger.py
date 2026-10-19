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
TREE_1 = "1" * 40
TREE_2 = "2" * 40


def tree_of(commit: str) -> str:
    """A commit's own tree unless a test pins one: distinct commits, distinct content."""
    return "tree-" + commit[:8]


class FakeGit:
    """HEAD and tree state; FakeRunner(during=...) moves HEAD or dirties the tree mid-run."""

    def __init__(self, head=SHA_A, clean=True, tree=None):
        self.head_sha = head
        self.tree_sha = tree or tree_of(head)
        self.clean = clean

    def head(self) -> str:
        return self.head_sha

    def tree(self) -> str:
        return self.tree_sha

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


def rev(commit=SHA_A, tree=None):
    return vl.Revision(commit, tree or tree_of(commit))


def status(ledger_path, commit=SHA_A, context="core", level="session", tree=None):
    return vl.status(context, level, rev(commit, tree), path=ledger_path)


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

    assert result == vl.COULD_NOT_START_EXIT
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
    assert vl.is_verified("core", "session", rev(SHA_A), path=ledger_path) is True
    assert vl.is_verified("core", "session", rev(SHA_B), path=ledger_path) is False


def test_a_pass_is_found_again_for_the_same_tree_after_an_amend(ledger_path):
    run(ledger_path, git=FakeGit(SHA_A, tree=TREE_1))

    amended = rev(SHA_B, TREE_1)  # an amend or a no-content merge: new commit, same content
    assert vl.status("core", "session", amended, path=ledger_path) == vl.VERIFIED
    assert vl.is_verified("core", "session", amended, path=ledger_path) is True


def test_a_pass_is_not_found_after_a_content_change(ledger_path):
    run(ledger_path, git=FakeGit(SHA_A, tree=TREE_1))

    changed = rev(SHA_B, TREE_2)
    assert vl.status("core", "session", changed, path=ledger_path) == vl.STALE
    assert vl.is_verified("core", "session", changed, path=ledger_path) is False


def test_a_content_change_back_to_a_recorded_tree_is_verified_again(ledger_path):
    run(ledger_path, git=FakeGit(SHA_A, tree=TREE_1))

    assert vl.status("core", "session", rev(SHA_B, TREE_1), path=ledger_path) == vl.VERIFIED


def test_a_context_never_run_is_unverified_even_with_no_ledger_file(ledger_path):
    assert not ledger_path.exists()
    assert status(ledger_path) == vl.UNVERIFIED
    assert vl.is_verified("core", "session", rev(SHA_A), path=ledger_path) is False
    assert vl.last_verified("core", "session", path=ledger_path) is None


def test_a_run_on_a_dirty_tree_is_not_recorded(ledger_path):
    result, runner = run(ledger_path, git=FakeGit(SHA_A, clean=False))

    assert result == 0  # the suite's own result is passed through
    assert runner.calls
    assert not ledger_path.exists()


def test_a_run_that_started_dirty_is_not_recorded_even_if_the_tree_is_clean_at_the_end(ledger_path):
    # The suite ran on uncommitted changes, so its pass says nothing about the commit,
    # even when the command itself cleans the tree up before it finishes.
    git = FakeGit(SHA_A, clean=False)
    runner = FakeRunner(git=git, during=lambda g: setattr(g, "clean", True))

    result, _ = run(ledger_path, git=git, runner=runner)

    assert result == 0
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
        vl.status("core", "session", rev(SHA_A), path=ledger_path)
    with pytest.raises(vl.LedgerError):
        run(ledger_path)

    assert ledger_path.read_text(encoding="utf-8") == "{not json"


def test_the_ledger_file_holds_commit_time_and_command_per_context_and_level(ledger_path):
    run(ledger_path, context="android", level="release", command=("gradlew", "test"), now="2026-10-18T10:00:00Z")

    data = json.loads(ledger_path.read_text(encoding="utf-8"))
    entry = data["contexts"]["android"]["release"]
    assert entry["commit"] == SHA_A
    assert entry["tree"] == tree_of(SHA_A)
    assert entry["timestamp"] == "2026-10-18T10:00:00Z"
    assert entry["command"] == "gradlew test"


def test_the_default_ledger_lives_inside_the_git_dir_so_it_is_never_tracked(tmp_path):
    git = SimpleNamespace(common_dir=lambda: tmp_path / ".git")

    assert vl.default_ledger_path(git) == tmp_path / ".git" / "hdttools-verification-ledger.json"


def test_cli_check_and_show_answer_by_tree_so_a_pass_survives_an_amend(ledger_path):
    run(ledger_path, git=FakeGit(SHA_A, tree=TREE_1))
    args = ["check", "--context", "core", "--level", "session"]
    lines: list[str] = []

    assert vl.main(args, path=ledger_path, git=FakeGit(SHA_B, tree=TREE_1), out=lines.append) == 0
    assert vl.main(args, path=ledger_path, git=FakeGit(SHA_B, tree=TREE_2), out=lines.append) == 1

    lines.clear()
    vl.main(["show"], path=ledger_path, git=FakeGit(SHA_B, tree=TREE_1), out=lines.append)
    assert any("verified" in line and "stale" not in line for line in lines)
    lines.clear()
    vl.main(["show"], path=ledger_path, git=FakeGit(SHA_B, tree=TREE_2), out=lines.append)
    assert any("stale" in line for line in lines)


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


def test_a_ledger_with_a_malformed_context_is_reported_not_crashed(ledger_path):
    ledger_path.write_text('{"contexts": {"web": 1}}', encoding="utf-8")
    lines: list[str] = []

    code = vl.main(["show"], path=ledger_path, git=FakeGit(), out=lines.append)

    assert code == vl.LEDGER_ERROR_EXIT
    assert any("unexpected shape" in line for line in lines)


def test_ledger_errors_use_an_exit_code_a_wrapped_suite_does_not(ledger_path):
    ledger_path.write_text("{not json", encoding="utf-8")

    code = vl.main(["check", "--context", "core", "--level", "issue"],
                   path=ledger_path, git=FakeGit(), out=lambda _: None)

    assert code == vl.LEDGER_ERROR_EXIT
    assert code not in (1, 2)


def test_cli_run_splits_the_wrapped_command_after_the_double_dash(ledger_path):
    runner = FakeRunner()

    vl.main(["run", "--context", "core", "--level", "issue", "--", "uv", "run", "pytest", "-m", "minor"],
            path=ledger_path, git=FakeGit(), run_command=runner, out=lambda _: None)

    assert runner.calls == [["uv", "run", "pytest", "-m", "minor"]]


def _git(root, *args):
    import subprocess

    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                   cwd=root, check=True, capture_output=True)


@pytest.fixture
def throwaway_repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    (root / "a.txt").write_text("one", encoding="utf-8")
    _git(root, "add", "a.txt")
    _git(root, "commit", "-q", "-m", "first")
    return root


def test_real_git_reports_head_and_whether_tracked_files_changed(throwaway_repo):
    git = vl.RealGit(throwaway_repo)
    assert len(git.head()) == 40
    assert git.is_clean() is True

    (throwaway_repo / "untracked.txt").write_text("x", encoding="utf-8")
    assert git.is_clean() is True  # untracked files do not count

    (throwaway_repo / "a.txt").write_text("two", encoding="utf-8")
    assert git.is_clean() is False


def test_real_git_ledger_is_in_the_git_dir_and_shared_with_a_worktree(throwaway_repo, tmp_path):
    main = vl.RealGit(throwaway_repo)
    worktree = tmp_path / "wt"
    _git(throwaway_repo, "worktree", "add", "-q", "-b", "side", str(worktree))

    assert vl.default_ledger_path(main) == (throwaway_repo / ".git").resolve() / vl.LEDGER_NAME
    assert vl.default_ledger_path(vl.RealGit(worktree)) == vl.default_ledger_path(main)


def test_real_git_tree_survives_an_amend_and_changes_with_content(throwaway_repo):
    git = vl.RealGit(throwaway_repo)
    first = vl.Revision(git.head(), git.tree())

    _git(throwaway_repo, "commit", "-q", "--amend", "-m", "reworded")
    amended = vl.Revision(git.head(), git.tree())
    assert amended.commit != first.commit
    assert amended.tree == first.tree

    (throwaway_repo / "a.txt").write_text("two", encoding="utf-8")
    _git(throwaway_repo, "commit", "-q", "-am", "content change")
    assert git.tree() != first.tree


def test_a_real_amend_reuses_a_pass_and_a_real_content_change_does_not(throwaway_repo, tmp_path):
    git = vl.RealGit(throwaway_repo)
    ledger = tmp_path / "ledger.json"
    vl.run_and_record("core", "issue", ["x"], path=ledger, git=git, run_command=FakeRunner(), out=lambda _: None)
    recorded = vl.Revision(git.head(), git.tree())
    assert vl.status("core", "issue", recorded, path=ledger) == vl.VERIFIED

    _git(throwaway_repo, "commit", "-q", "--amend", "-m", "reworded")
    assert vl.status("core", "issue", vl.Revision(git.head(), git.tree()), path=ledger) == vl.VERIFIED

    (throwaway_repo / "a.txt").write_text("two", encoding="utf-8")
    _git(throwaway_repo, "commit", "-q", "-am", "content change")
    assert vl.status("core", "issue", vl.Revision(git.head(), git.tree()), path=ledger) == vl.STALE
