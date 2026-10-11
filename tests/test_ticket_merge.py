"""Function and interaction tests for scripts/ticket_merge.py (#87).

`/ticket-merge <N>` runs in the main checkout. The script's three steps are
tested against a real throwaway repository with a real worktree and a fake
`gh`: preflight (right place, clean, READY TO MERGE posted), `merge --no-ff`
into MPSkills with a commit, and `close` (comment, close, remove the worktree,
delete the branch). Nothing here may ever push.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


common = _load("ticket_common")
merge = _load("ticket_merge")
Result = common.Result

TABLE = "| Criterion | Proven by (test file and name) |\n|---|---|\n| A works | tests/test_a.py::test_a |\n"


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """Main checkout on MPSkills, with a ticket-9 worktree one commit ahead."""
    root = tmp_path / "main"
    root.mkdir()
    _git(root, "init", "-q", "-b", "MPSkills")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "a.txt").write_text("base\n")
    (root / ".gitignore").write_text(".claude/worktrees/\n")  # as in the real repo
    _git(root, "add", "a.txt", ".gitignore")
    _git(root, "commit", "-q", "-m", "base")
    wt =root / ".claude" / "worktrees" / "ticket-9"
    _git(root, "worktree", "add", "-q", str(wt), "-b", "ticket-9", "MPSkills")
    (wt / "feature.txt").write_text("feature\n")
    _git(wt, "add", "feature.txt")
    _git(wt, "commit", "-q", "-m", "feature")
    return root


class Gh:
    def __init__(self, comments=("STATUS: READY TO MERGE\n\nBranch: x",), title="Add the feature"):
        self.comments = [{"body": c} for c in comments]
        self.title = title
        self.calls: list[list[str]] = []

    def __call__(self, cmd, cwd=None):
        cmd = list(cmd)
        self.calls.append(cmd)
        if cmd[0] == "git":
            assert cmd[1] != "push", "a ticket script must never push"
            return common.real_shell(cmd, cwd)
        if cmd[:3] == ["gh", "issue", "view"]:
            return Result(0, json.dumps({"number": 9, "title": self.title, "state": "OPEN", "comments": self.comments}))
        if cmd[:3] == ["gh", "issue", "close"]:
            return Result(0)
        raise AssertionError(f"unexpected command {cmd}")

    def closed_with(self):
        return [c for c in self.calls if c[:3] == ["gh", "issue", "close"]]


def _run(fn, *args, **kw):
    lines = []
    code = fn(*args, out=lines.append, **kw)
    return code, "\n".join(lines)


# --- preflight --------------------------------------------------------------


def test_preflight_passes_in_a_clean_main_checkout_on_mpskills_with_a_ready_ticket(repo):
    assert merge.preflight(9, shell=Gh(), root=repo) == []


def test_preflight_refuses_to_run_from_inside_a_worktree(repo):
    reasons = merge.preflight(9, shell=Gh(), root=repo / ".claude" / "worktrees" / "ticket-9")

    assert any("main checkout" in r for r in reasons)


def test_preflight_requires_mpskills_to_be_checked_out(repo):
    _git(repo, "checkout", "-q", "-b", "elsewhere")

    reasons = merge.preflight(9, shell=Gh(), root=repo)

    assert any("MPSkills" in r for r in reasons)


def test_preflight_requires_a_clean_main_tree(repo):
    (repo / "a.txt").write_text("edited\n")

    assert any("uncommitted" in r.lower() for r in merge.preflight(9, shell=Gh(), root=repo))


def test_preflight_needs_the_ticket_branch_to_have_commits(repo):
    _git(repo, "worktree", "remove", "--force", ".claude/worktrees/ticket-9")
    _git(repo, "branch", "-D", "ticket-9")

    assert any("ticket-9" in r for r in merge.preflight(9, shell=Gh(), root=repo))


def test_preflight_needs_the_latest_status_to_be_ready_to_merge(repo):
    gh = Gh(comments=("STATUS: READY TO MERGE\n", "chatter", "STATUS: PARTIAL\n\nB not done"))

    reasons = merge.preflight(9, shell=gh, root=repo)

    assert any("PARTIAL" in r for r in reasons)
    assert merge.preflight(9, shell=gh, root=repo, allow_status=True) == []


def test_preflight_needs_some_status_comment(repo):
    assert any("STATUS" in r for r in merge.preflight(9, shell=Gh(comments=("hello",)), root=repo))


# --- merge ------------------------------------------------------------------


def test_merge_makes_a_no_ff_merge_commit_on_mpskills(repo):
    before = _git(repo, "rev-parse", "MPSkills")

    code, out = _run(merge.merge, 9, shell=Gh(), root=repo)

    assert code == 0
    parents = _git(repo, "rev-list", "--parents", "-n", "1", "MPSkills").split()
    assert len(parents) == 3 and parents[1] == before
    assert parents[2] == _git(repo, "rev-parse", "ticket-9")
    assert _git(repo, "log", "-1", "--format=%s", "MPSkills") == "Merge #9 Add the feature (ticket-9)"
    assert (repo / "feature.txt").exists()


def test_merge_conflict_is_aborted_and_leaves_the_tree_clean(repo):
    wt = repo / ".claude" / "worktrees" / "ticket-9"
    (wt / "a.txt").write_text("from the ticket\n")
    _git(wt, "commit", "-q", "-am", "ticket edit")
    (repo / "a.txt").write_text("from MPSkills\n")
    _git(repo, "commit", "-q", "-am", "mainline edit")
    before = _git(repo, "rev-parse", "MPSkills")

    code, out = _run(merge.merge, 9, shell=Gh(), root=repo)

    assert code == 1 and "conflict" in out.lower()
    assert _git(repo, "rev-parse", "MPSkills") == before
    assert _git(repo, "status", "--porcelain") == ""


def test_merge_does_not_push(repo, tmp_path):
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "-q", "--bare", str(remote))
    _git(repo, "remote", "add", "origin", str(remote))

    code, _ = _run(merge.merge, 9, shell=Gh(), root=repo)

    assert code == 0
    assert subprocess.run(["git", "rev-parse", "--verify", "-q", "MPSkills"], cwd=remote).returncode != 0


# --- close ------------------------------------------------------------------


def _merged(repo):
    code, _ = _run(merge.merge, 9, shell=Gh(), root=repo)
    assert code == 0


def _comment_file(tmp_path, text=TABLE):
    path = tmp_path / "close.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_close_comments_closes_removes_the_worktree_and_deletes_the_branch(repo, tmp_path):
    _merged(repo)
    gh = Gh()

    code, out = _run(merge.close, 9, _comment_file(tmp_path), shell=gh, root=repo)

    assert code == 0
    [call] = gh.closed_with()
    comment = call[call.index("--comment") + 1]
    assert "Merged into MPSkills" in comment and _git(repo, "rev-parse", "--short", "MPSkills") in comment
    assert "not pushed" in comment.lower()
    assert "| A works | tests/test_a.py::test_a |" in comment
    assert not (repo / ".claude" / "worktrees" / "ticket-9").exists()
    assert "ticket-9" not in _git(repo, "branch", "--list")
    assert "ticket-9" not in _git(repo, "worktree", "list")


def test_close_refuses_when_the_branch_is_not_merged_and_changes_nothing(repo, tmp_path):
    gh = Gh()

    code, out = _run(merge.close, 9, _comment_file(tmp_path), shell=gh, root=repo)

    assert code == 1 and "not merged" in out.lower()
    assert gh.closed_with() == []
    assert (repo / ".claude" / "worktrees" / "ticket-9").exists()
    assert "ticket-9" in _git(repo, "branch", "--list")


def test_close_needs_a_criterion_to_test_table_in_the_comment(repo, tmp_path):
    _merged(repo)
    gh = Gh()

    code, out = _run(merge.close, 9, _comment_file(tmp_path, "all good"), shell=gh, root=repo)

    assert code == 1 and "table" in out.lower()
    assert gh.closed_with() == []


def test_close_does_not_push(repo, tmp_path):
    _merged(repo)
    gh = Gh()

    _run(merge.close, 9, _comment_file(tmp_path), shell=gh, root=repo)

    assert not [c for c in gh.calls if c[:2] == ["git", "push"]]


def test_a_worktree_that_will_not_go_is_reported_with_the_issue_already_closed(repo, tmp_path):
    _merged(repo)
    real = Gh()

    def shell(cmd, cwd=None):
        if list(cmd)[:3] == ["git", "worktree", "remove"]:
            return Result(1, "", "error: the folder is in use by another process")
        return real(cmd, cwd)

    code, out = _run(merge.close, 9, _comment_file(tmp_path), shell=shell, root=repo)

    assert code == 1 and "worktree-setup.md" in out
    assert len(real.closed_with()) == 1


# --- Windows: a worktree whose path is too long for git to delete ------------


TOO_LONG = "error: failed to delete 'X/.claude/worktrees/ticket-9': Filename too long"


def _remove_fails(real, message, rmdir_calls, *, simulate_rmdir=True):
    """A shell where `git worktree remove` fails with `message`; records any long-path rmdir."""

    def shell(cmd, cwd=None):
        cmd = list(cmd)
        if cmd[:3] == ["git", "worktree", "remove"]:
            return Result(1, "", message)
        if cmd[:2] == ["cmd", "/c"]:
            rmdir_calls.append(cmd)
            if simulate_rmdir:  # what the real `rmdir /s /q` would do to the folder
                shutil.rmtree(cmd[-1].removeprefix("\\\\?\\"), ignore_errors=True)
            return Result(0)
        return real(cmd, cwd)

    return shell


def test_long_path_remove_command_is_a_plain_recursive_rmdir_with_the_long_path_prefix(tmp_path):
    cmd = merge.long_path_remove_command(tmp_path / "wt")

    assert cmd == ["cmd", "/c", "rmdir", "/s", "/q", "\\\\?\\" + str(tmp_path / "wt")]


def test_close_removes_a_worktree_git_cannot_delete_because_its_path_is_too_long(repo, tmp_path):
    _merged(repo)
    gh, rmdir_calls = Gh(), []
    shell = _remove_fails(gh, TOO_LONG, rmdir_calls)
    target = (repo / ".claude" / "worktrees" / "ticket-9").resolve()

    code, out = _run(merge.close, 9, _comment_file(tmp_path), shell=shell, root=repo, windows=True)

    assert code == 0, out
    assert rmdir_calls == [merge.long_path_remove_command(target)]
    assert not target.exists()
    assert "ticket-9" not in _git(repo, "branch", "--list")
    assert "ticket-9" not in _git(repo, "worktree", "list")
    assert len(gh.closed_with()) == 1


def test_close_never_force_deletes_a_worktree_git_refused_for_another_reason(repo, tmp_path):
    _merged(repo)
    gh, rmdir_calls = Gh(), []
    shell = _remove_fails(gh, "fatal: cannot remove a locked working tree", rmdir_calls)

    code, out = _run(merge.close, 9, _comment_file(tmp_path), shell=shell, root=repo, windows=True)

    assert code == 1 and "worktree-setup.md" in out
    assert rmdir_calls == []
    assert (repo / ".claude" / "worktrees" / "ticket-9").exists()
    assert "ticket-9" in _git(repo, "branch", "--list")


# --- a worktree git will not remove because files in it need a decision ------


def _dirty_close(repo, tmp_path, *, windows):
    """Closes ticket 9 for real (real git, real worktree) after leaving files in the worktree."""
    wt = repo / ".claude" / "worktrees" / "ticket-9"
    (wt / "notes.txt").write_text("scratch\n")  # untracked
    (wt / "feature.txt").write_text("edited after the commit\n")  # modified
    _merged(repo)
    gh = Gh()
    code, out = _run(merge.close, 9, _comment_file(tmp_path), shell=gh, root=repo, windows=windows)
    return code, out, gh, wt


@pytest.mark.parametrize("windows", [True, False])
def test_a_worktree_with_uncommitted_files_is_reported_by_file_name_not_as_a_long_path(repo, tmp_path, windows):
    code, out, gh, wt = _dirty_close(repo, tmp_path, windows=windows)

    assert code == 1
    assert "notes.txt" in out and "feature.txt" in out
    assert "nothing was removed" in out.lower()
    assert "worktree-setup.md" not in out and "long-path" not in out.lower() and "windows" not in out.lower()


@pytest.mark.parametrize("windows", [True, False])
def test_a_worktree_with_uncommitted_files_is_left_exactly_as_it_was_and_the_issue_stays_closed(repo, tmp_path, windows):
    code, out, gh, wt = _dirty_close(repo, tmp_path, windows=windows)

    assert (wt / "notes.txt").read_text() == "scratch\n"
    assert (wt / "feature.txt").read_text() == "edited after the commit\n"
    assert "ticket-9" in _git(repo, "branch", "--list")
    assert str(wt.resolve()).replace("\\", "/") in _git(repo, "worktree", "list").replace("\\", "/")
    assert len(gh.closed_with()) == 1


def test_the_long_path_fallback_runs_only_on_windows(repo, tmp_path):
    _merged(repo)
    gh, rmdir_calls = Gh(), []
    shell = _remove_fails(gh, TOO_LONG, rmdir_calls)

    code, out = _run(merge.close, 9, _comment_file(tmp_path), shell=shell, root=repo, windows=False)

    assert code == 1 and "worktree-setup.md" in out
    assert rmdir_calls == []
    assert (repo / ".claude" / "worktrees" / "ticket-9").exists()


def test_a_long_path_delete_that_leaves_the_folder_behind_is_reported_not_hidden(repo, tmp_path):
    _merged(repo)
    gh, rmdir_calls = Gh(), []
    shell = _remove_fails(gh, TOO_LONG, rmdir_calls, simulate_rmdir=False)

    code, out = _run(merge.close, 9, _comment_file(tmp_path), shell=shell, root=repo, windows=True)

    assert code == 1 and "still there" in out.lower()
    assert len(gh.closed_with()) == 1


def test_the_fallback_only_ever_targets_the_tickets_own_worktree_folder(repo):
    target = merge.worktree_folder(repo, 9)

    assert target == (repo / ".claude" / "worktrees" / "ticket-9").resolve()
    with pytest.raises(ValueError):
        merge.worktree_folder(repo, -1)


def test_preflight_refuses_commits_added_after_the_status_comment(repo):
    wt = repo / ".claude" / "worktrees" / "ticket-9"
    vouched = _git(wt, "rev-parse", "--short", "HEAD")
    comment = f"STATUS: READY TO MERGE\n\nBranch: `ticket-9` at `{vouched}` (worktree: `w`; pushed: no)"
    assert merge.preflight(9, shell=Gh(comments=(comment,)), root=repo) == []

    (wt / "late.txt").write_text("late\n")
    _git(wt, "add", "late.txt")
    _git(wt, "commit", "-q", "-m", "late")

    reasons = merge.preflight(9, shell=Gh(comments=(comment,)), root=repo)

    assert any("after it" in r and vouched in r for r in reasons)
