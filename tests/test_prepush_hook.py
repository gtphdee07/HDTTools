"""Interaction test for .githooks/pre-push (#43): a real `git push` runs the hook, hands the
pushed refs to scripts/external_gate.py on stdin, and the gate's exit code decides whether
the push goes through. A fake `uv` on PATH records the call; the real gate is tested in
tests/test_external_gate.py."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

HOOKS = Path(__file__).resolve().parent.parent / ".githooks"


def _git(cwd, *args, env=None, check=True):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check, env=env)


@pytest.fixture
def pushing(tmp_path):
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    bin_dir = tmp_path / "bin"
    for path in (repo, bin_dir):
        path.mkdir()
    _git(tmp_path, "init", "-q", "--bare", str(remote))
    _git(repo, "init", "-q", "-b", "MPSkills")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    _git(repo, "config", "core.hooksPath", str(HOOKS))
    _git(repo, "remote", "add", "origin", str(remote))
    (repo / "a.txt").write_text("a\n")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "-m", "first", env={**os.environ, "PATH": os.environ["PATH"]})

    seen, verdict = tmp_path / "seen", tmp_path / "verdict"
    verdict.write_text("0")
    # The hook runs under git's sh, which finds this extensionless script.
    (bin_dir / "uv").write_text(
        f'#!/bin/sh\necho "$@" > "{seen.as_posix()}"\ncat >> "{seen.as_posix()}"\nexit "$(cat "{verdict.as_posix()}")"\n',
        newline="\n",
    )
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}

    def push(exit_code):
        verdict.write_text(str(exit_code))
        return _git(repo, "push", "origin", "MPSkills", env=env, check=False)

    return repo, remote, seen, push


def test_the_hook_hands_the_pushed_refs_to_the_gate_and_its_verdict_lets_the_push_through(pushing):
    repo, remote, seen, push = pushing

    result = push(0)

    assert result.returncode == 0
    called = seen.read_text().splitlines()
    assert called[0].startswith("run ") and called[0].split()[1].endswith("external_gate.py")
    assert called[0].split()[2:] == ["pre-push", "origin", str(remote)]
    local_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    assert called[1].split() == ["refs/heads/MPSkills", local_sha, "refs/heads/MPSkills", "0" * 40]
    assert _git(remote, "rev-parse", "MPSkills").stdout.strip() == local_sha


def test_a_blocking_gate_stops_the_push_and_no_verify_skips_the_hook(pushing):
    repo, remote, seen, push = pushing

    blocked = push(1)

    assert blocked.returncode != 0
    assert _git(remote, "rev-parse", "--verify", "-q", "MPSkills", check=False).returncode != 0

    seen.unlink()
    bypassed = _git(repo, "push", "--no-verify", "origin", "MPSkills", check=False)
    assert bypassed.returncode == 0
    assert not seen.exists()
