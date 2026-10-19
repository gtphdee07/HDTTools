"""Shared plumbing for the ticket workflow scripts (#87): ticket_start.py,
ticket_finish.py and ticket_merge.py back the /ticket-start, /ticket-finish
and /ticket-merge skills (docs/agents/ticket-skills.md).

Every script talks to git and gh through a `Shell` so its decision logic can
be tested with a fake one; `real_shell` is the only place a captured process
starts (ticket_start.py also streams the long setup run directly).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

BASE_BRANCH = "MPSkills"

# Planned suite kinds /ticket-finish and /ticket-merge never run for a ticket (#128): they need a device,
# the owner's go-ahead, or the stale-External bundle at the end of the round.
NOT_RUN_HERE = ("surface", "device", "gate", "release")


def runs_here(selection) -> bool:
    """Is this planned suite one the ticket scripts run (and the ledger vouches for)?"""
    return selection.action == "run" and selection.kind not in NOT_RUN_HERE


@dataclass(frozen=True)
class Result:
    code: int
    out: str = ""
    err: str = ""

    @property
    def ok(self) -> bool:
        return self.code == 0


Shell = Callable[[Sequence[str], "Path | None"], Result]


def real_shell(cmd: Sequence[str], cwd: Path | None = None) -> Result:
    # npm, gh and uv resolve to .cmd/.exe shims on Windows; subprocess needs the full name.
    exe = shutil.which(cmd[0]) or cmd[0]
    p = subprocess.run([exe, *cmd[1:]], cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    return Result(p.returncode, p.stdout, p.stderr)


def git(shell: Shell, root: Path, *cmd: str) -> Result:
    return shell(["git", *cmd], root)


def git_out(shell: Shell, root: Path, *cmd: str) -> str:
    return git(shell, root, *cmd).out.strip()


def branch_name(n: int) -> str:
    return f"ticket-{n}"


def worktree_relpath(n: int) -> str:
    return f".claude/worktrees/ticket-{n}"


def scratch_path(n: int, temp: Path | None = None) -> Path:
    """The live-notes file docs/agents/session-handoff.md names, outside the repo."""
    return (temp or Path(tempfile.gettempdir())) / "hdttools-status" / f"ticket-{n}.md"


def ticket_from_branch(branch: str) -> int | None:
    m = re.fullmatch(r"ticket-(\d+)", branch)
    return int(m.group(1)) if m else None


def main_checkout(shell: Shell, cwd: Path) -> Path | None:
    """The main checkout is the parent of the git dir every worktree shares."""
    r = shell(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd)
    return Path(r.out.strip()).parent if r.ok and r.out.strip() else None


def gh_issue(shell: Shell, cwd: Path, n: int, fields: str = "number,title,state,assignees,labels,body,comments") -> dict | None:
    r = shell(["gh", "issue", "view", str(n), "--json", fields], cwd)
    return json.loads(r.out) if r.ok and r.out.strip() else None
