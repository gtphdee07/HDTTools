"""Interaction tests for scripts/promote_release.py (#175): the command that moves the `release`
branch (Cloudflare Pages' production branch) to a chosen MPSkills commit. Everything runs against
throwaway git repositories: a bare "origin" and a clone with an MPSkills branch. Nothing here
touches the real repository, the network or Cloudflare."""

from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
for _name in ("external_freshness", "record_external_result", "external_gate", "promote_release"):
    if _name not in sys.modules:
        _spec = importlib.util.spec_from_file_location(_name, _SCRIPTS / f"{_name}.py")
        _module = importlib.util.module_from_spec(_spec)
        sys.modules[_name] = _module
        _spec.loader.exec_module(_module)

pr = sys.modules["promote_release"]

ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
       "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}


def git(cwd, *args, check=True):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check, env=ENV).stdout.strip()


def commit(repo, message, **files):
    for name, text in files.items():
        path = repo / name.replace("__", "/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


class World:
    """A bare origin and a clone on MPSkills. c1 is live on release; c2 changes docs only; c3 changes web/."""

    def __init__(self, tmp_path):
        self.tmp = tmp_path
        self.origin = tmp_path / "origin.git"
        self.repo = tmp_path / "repo"
        self.repo.mkdir()
        git(tmp_path, "init", "-q", "--bare", str(self.origin))
        git(self.repo, "init", "-q", "-b", "MPSkills")
        git(self.repo, "remote", "add", "origin", str(self.origin))
        self.c1 = commit(self.repo, "first", web__app_ts="1\n", docs__a_md="1\n")
        self.c2 = commit(self.repo, "docs only", docs__a_md="2\n")
        self.c3 = commit(self.repo, "web change", web__app_ts="3\n", web__other_ts="3\n")
        git(self.repo, "push", "-q", "origin", f"{self.c1}:refs/heads/release")
        self.out: list[str] = []

    def release(self):
        return git(self.origin, "rev-parse", "--verify", "-q", "release", check=False)

    def promote(self, commit_ish, *, yes=True, answer=None, create=False):
        self.out.clear()
        code = pr.promote(
            commit_ish, git=pr.Git(self.repo), create=create, yes=yes,
            ask=None if answer is None else (lambda _prompt: answer), out=self.out.append,
        )
        return code, "\n".join(self.out)


@pytest.fixture
def world(tmp_path):
    return World(tmp_path)


def test_fast_forwards_release_to_a_commit_on_mpskills(world):
    code, out = world.promote(world.c3)

    assert code == 0
    assert world.release() == world.c3
    assert "now at" in out


def test_the_default_commit_is_the_tip_of_mpskills(world):
    # main() with no commit argument resolves the name MPSkills.
    code = pr.main(["--yes"], git=pr.Git(world.repo), stdin=io.StringIO(), out=world.out.append)

    assert code == 0 and world.release() == world.c3


def test_it_prints_the_changed_files_under_web_before_pushing_and_nothing_else(world):
    code, out = world.promote(world.c3, yes=False, answer="n")

    assert code == 2
    assert "2 file(s) under web/" in out
    assert "web/app_ts" in out and "web/other_ts" in out
    assert "docs/a.md" not in out
    assert world.release() == world.c1  # printed, not pushed


def test_it_says_when_nothing_under_web_changed(world):
    code, out = world.promote(world.c2)

    assert code == 0
    assert "Nothing under web/ changed" in out
    assert "web/app_ts" not in out
    assert world.release() == world.c2


def test_it_refuses_a_commit_that_is_not_on_mpskills(world):
    git(world.repo, "checkout", "-q", "-b", "side", world.c1)
    side = commit(world.repo, "side work", web__side_ts="x\n")
    git(world.repo, "checkout", "-q", "MPSkills")

    code, out = world.promote(side)

    assert code == 1 and "not on MPSkills" in out
    assert world.release() == world.c1


def test_it_refuses_something_that_is_not_a_commit(world):
    code, out = world.promote("no-such-ref")

    assert code == 1 and "not a commit" in out
    assert world.release() == world.c1


def test_it_refuses_a_move_that_is_not_a_fast_forward(world):
    git(world.repo, "push", "-q", "origin", f"{world.c3}:refs/heads/release")

    code, out = world.promote(world.c2)  # backwards: would rewrite release

    assert code == 1 and "not a fast-forward" in out
    assert world.release() == world.c3


def test_it_refuses_when_release_has_a_commit_that_is_not_on_mpskills_even_if_this_clone_lacks_it(world):
    # Someone else put a commit on release. This clone has never seen it: the command asks the
    # remote, fetches the commit, and then sees that the move would drop it.
    other = world.tmp / "other"
    git(world.tmp, "clone", "-q", str(world.origin), str(other))
    git(other, "checkout", "-q", "-B", "work", "origin/release")
    foreign = commit(other, "hotfix straight on release", web__hotfix_ts="h\n")
    git(other, "push", "-q", "origin", f"{foreign}:refs/heads/release")
    assert git(world.repo, "cat-file", "-t", foreign, check=False) == ""

    code, out = world.promote(world.c3)

    assert code == 1 and "not a fast-forward" in out
    assert world.release() == foreign


def test_a_run_nobody_confirmed_pushes_nothing(world):
    no_terminal = world.promote(world.c3, yes=False, answer=None)
    said_no = world.promote(world.c3, yes=False, answer="no")
    empty = world.promote(world.c3, yes=False, answer="")

    assert [no_terminal[0], said_no[0], empty[0]] == [2, 2, 2]
    assert "nobody confirmed" in no_terminal[1]
    assert world.release() == world.c1


def test_a_typed_yes_pushes(world):
    code, _ = world.promote(world.c3, yes=False, answer=" Y ")

    assert code == 0 and world.release() == world.c3


def test_the_command_line_without_a_terminal_or_yes_does_not_push(world):
    code = pr.main([world.c3], git=pr.Git(world.repo), stdin=io.StringIO(), out=world.out.append)

    assert code == 2 and world.release() == world.c1


def test_promoting_the_commit_release_is_already_at_does_nothing(world):
    code, out = world.promote(world.c1)

    assert code == 0 and "already at" in out and world.release() == world.c1


def test_a_missing_release_branch_is_created_only_with_create(world):
    git(world.origin, "update-ref", "-d", "refs/heads/release")

    refused = world.promote(world.c2)
    assert refused[0] == 1 and "--create" in refused[1] and world.release() == ""

    created = world.promote(world.c2, create=True)
    assert created[0] == 0 and world.release() == world.c2


def test_it_never_bypasses_the_pre_push_hook(world):
    hooks = world.tmp / "hooks"
    hooks.mkdir()
    (hooks / "pre-push").write_text("#!/bin/sh\necho blocked by the gate >&2\nexit 1\n", newline="\n")
    git(world.repo, "config", "core.hooksPath", str(hooks))

    code, out = world.promote(world.c3)

    assert code == 1 and "unchanged" in out
    assert world.release() == world.c1


def test_it_never_forces_even_when_the_remote_moved_after_the_check(world, monkeypatch):
    # alt is on MPSkills (merged) and fast-forwards c1, which is what the check sees. Then someone moves
    # release to c2, which alt does not contain: git's own refusal of the non-fast-forward must stop the push.
    git(world.repo, "checkout", "-q", "-b", "alt", world.c1)
    alt = commit(world.repo, "alt", docs__alt_md="a\n")
    git(world.repo, "checkout", "-q", "MPSkills")
    git(world.repo, "merge", "-q", "--no-ff", "-m", "merge alt", "alt")
    real = pr.remote_release_tip

    def stale_view(g, remote):
        tip = real(g, remote)  # reads c1
        git(world.repo, "push", "-q", "origin", f"{world.c2}:refs/heads/release")
        return tip

    monkeypatch.setattr(pr, "remote_release_tip", stale_view)

    code, out = world.promote(alt)

    assert code == 1 and "unchanged" in out
    assert world.release() == world.c2
