"""Interaction tests for .githooks/pre-commit (#87).

The hook rebuilds and stages dashboard.svg on commit. A ticket branch must not
carry a regenerated one (docs/agents/session-handoff.md), so the hook leaves
it alone there. A fake `uv` on PATH records whether the hook tried to
regenerate; nothing real is generated.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

HOOKS = Path(__file__).resolve().parent.parent / ".githooks"


def _git(cwd, *args, env=None):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True, env=env)


def _commit_on(tmp_path, branch):
    repo = tmp_path / "repo"
    repo.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    marker = tmp_path / "uv-called"
    # The hook runs under git's sh, which finds this extensionless script.
    (bin_dir / "uv").write_text(f'#!/bin/sh\necho "$@" >> "{marker.as_posix()}"\necho changed >> dashboard.svg\n', newline="\n")
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    _git(repo, "init", "-q", "-b", branch)
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    _git(repo, "config", "core.hooksPath", str(HOOKS))
    (repo / "dashboard.svg").write_text("<svg/>\n")
    (repo / "a.txt").write_text("a\n")
    _git(repo, "add", "dashboard.svg", "a.txt")
    _git(repo, "commit", "-q", "-m", "first", env=env)
    marker.unlink(missing_ok=True)
    (repo / "a.txt").write_text("b\n")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "-m", "second", env=env)
    files = _git(repo, "show", "--name-only", "--format=", "HEAD").stdout.split()
    return marker.exists(), files


def test_hook_regenerates_and_stages_the_dashboard_on_a_normal_branch(tmp_path):
    called, files = _commit_on(tmp_path, "MPSkills")

    assert called and "dashboard.svg" in files


def test_hook_leaves_the_dashboard_alone_on_a_ticket_branch(tmp_path):
    called, files = _commit_on(tmp_path, "ticket-87")

    assert not called and files == ["a.txt"]
