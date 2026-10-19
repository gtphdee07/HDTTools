"""Verification ledger (#65; spec #51): the last commit whose suites passed,
per context and level (issue, session, release).

The ledger is a local JSON file inside the git directory, shared by every
worktree and never tracked. Only this runner writes it, by running a test
command and recording the commit only if that command passed:

  uv run scripts/verification_ledger.py run --context web --level session -- npm --prefix web test

Rules:
  - A pass is valid only for the content it ran at. It is recorded with the
    commit and its tree hash (`git rev-parse HEAD^{tree}`), and looked up by
    tree: an amend or a merge commit with no content change reuses the pass,
    any content change loses it. The run must start and end at the same HEAD
    on a tree with no tracked changes; otherwise the suite's own exit code is
    passed through but nothing is recorded.
  - A failed run, a run that could not start and a skipped run leave the
    previous record untouched.
  - The runner sees only the command's exit code. A command that skips its
    work and still exits 0 must exit non-zero (or call `record(..., "skipped")`)
    to avoid being recorded; untracked files are not part of the clean check.
  - Exit codes: the command's own code from `run`; 1 from `check` when not
    verified; 125 for a ledger, git or usage error; 127 if the command could
    not start.

Questions it answers (exit 0 only when verified, so a script can branch on it):

  uv run scripts/verification_ledger.py check --context web --level session
  uv run scripts/verification_ledger.py show

The planner (#66), the session-start report (#67) and the epic gate (#68)
read the ledger through `status`, `is_verified` and `last_verified`.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_planner as planner  # noqa: E402
from release_steps import default_run_command  # noqa: E402

LEDGER_NAME = "hdttools-verification-ledger.json"
LEVELS = planner.LEVELS
LEDGER_ERROR_EXIT = 125  # not 1 (unverified) or 2 (a wrapped suite's own failure codes)
COULD_NOT_START_EXIT = 127
OUTCOMES = ("pass", "fail", "skipped")

VERIFIED = "verified"  # the recorded pass is for the tree asked about
STALE = "stale"  # a pass is recorded, but for a different tree
UNVERIFIED = "unverified"  # no pass recorded


@dataclass(frozen=True)
class Revision:
    """What a pass is about: the commit it ran at and that commit's content (tree)."""

    commit: str
    tree: str


def current_revision(git) -> Revision:
    return Revision(git.head(), git.tree())


class LedgerError(Exception):
    pass


class GitError(Exception):
    pass


class RealGit:
    def __init__(self, root: Path = REPO_ROOT):
        self.root = root

    def _git(self, *args: str) -> str:
        try:
            proc = subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True)
        except OSError as exc:
            raise GitError(str(exc)) from exc
        if proc.returncode != 0:
            raise GitError(proc.stderr.strip() or f"git {' '.join(args)} failed")
        return proc.stdout.strip()

    def head(self) -> str:
        return self._git("rev-parse", "HEAD")

    def tree(self) -> str:
        """The hash of HEAD's content; an amend or a merge with no content change keeps it."""
        return self._git("rev-parse", "HEAD^{tree}")

    def is_clean(self) -> bool:
        """No changes to tracked files (untracked and ignored files do not count)."""
        return self._git("status", "--porcelain", "--untracked-files=no") == ""

    def common_dir(self) -> Path:
        return (self.root / self._git("rev-parse", "--git-common-dir")).resolve()


def default_ledger_path(git=None) -> Path:
    """Inside the shared git directory: one ledger for all worktrees, never tracked."""
    return (git or RealGit()).common_dir() / LEDGER_NAME


def known_contexts() -> list[str]:
    return list(planner.load_config()["contexts"])


def _validate(context: str, level: str) -> None:
    if level not in LEVELS:
        raise ValueError(f"unknown level {level!r}; expected one of {', '.join(LEVELS)}")
    contexts = known_contexts()
    if context not in contexts:
        raise ValueError(f"unknown context {context!r}; expected one of {', '.join(contexts)}")


def _load(path: Path) -> dict:
    if not path.exists():
        return {"contexts": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LedgerError(f"verification ledger {path} is unreadable ({exc}); fix or delete it") from exc
    contexts = data.get("contexts") if isinstance(data, dict) else None
    if not isinstance(contexts, dict) or not all(isinstance(v, dict) for v in contexts.values()):
        raise LedgerError(f"verification ledger {path} has an unexpected shape; fix or delete it")
    return data


def _entry(data: dict, context: str, level: str) -> dict | None:
    entry = data["contexts"].get(context, {}).get(level)
    return entry if isinstance(entry, dict) and entry.get("commit") and entry.get("tree") else None


def last_verified(context: str, level: str, *, path: Path | None = None) -> str | None:
    """The commit of the last recorded pass, or None."""
    entry = _entry(_load(path or default_ledger_path()), context, level)
    return entry["commit"] if entry else None


def _state(entry: dict | None, revision: Revision) -> str:
    """A pass holds for any commit with the same tree: an amend keeps it, a content change loses it."""
    if entry is None:
        return UNVERIFIED
    return VERIFIED if entry["tree"] == revision.tree else STALE


def status(context: str, level: str, revision: Revision, *, path: Path | None = None) -> str:
    entry = _entry(_load(path or default_ledger_path()), context, level)
    return _state(entry, revision)


def is_verified(context: str, level: str, revision: Revision, *, path: Path | None = None) -> bool:
    """Is this context verified at this commit's content, for this level?"""
    return status(context, level, revision, path=path) == VERIFIED


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record(
    context: str,
    level: str,
    outcome: str,
    *,
    command: str = "",
    revision: Revision | None = None,
    path: Path | None = None,
    git=None,
    now: str | None = None,
) -> bool:
    """Writes the ledger only for a pass; a fail or skip changes nothing.
    Returns whether the ledger was written."""
    _validate(context, level)
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {OUTCOMES}, got {outcome!r}")
    git = git or RealGit()
    target = path or default_ledger_path(git)
    data = _load(target)  # an unreadable ledger is an error even for a fail or skip
    if outcome != "pass":
        return False
    revision = revision or current_revision(git)
    data["contexts"].setdefault(context, {})[level] = {
        "commit": revision.commit,
        "tree": revision.tree,
        "timestamp": now or _now(),
        "command": command,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, scratch = tempfile.mkstemp(dir=target.parent, prefix=target.name + ".", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
    os.replace(scratch, target)
    return True


def run_and_record(
    context: str,
    level: str,
    command: list[str],
    *,
    path: Path | None = None,
    git=None,
    run_command=default_run_command,
    now: str | None = None,
    out: Callable[[str], None] = print,
) -> int:
    """Runs the command and records a pass at the commit it started on.
    Returns the command's exit code (non-zero if it could not start)."""
    _validate(context, level)
    git = git or RealGit()
    target = path or default_ledger_path(git)
    _load(target)  # refuse before running anything if the ledger cannot be updated
    start = current_revision(git)
    clean = git.is_clean()
    try:
        code = run_command(command, cwd=REPO_ROOT).returncode
    except OSError as exc:
        out(f"could not start {command[0]!r} ({exc}); {context}/{level} not recorded.")
        return COULD_NOT_START_EXIT
    label = f"{context}/{level}"
    if code != 0:
        out(f"{label}: failed (exit {code}); ledger unchanged.")
    elif not clean:
        out(f"{label}: passed, but the tree had uncommitted changes to tracked files; not recorded. Commit, then re-run.")
    elif current_revision(git) != start or not git.is_clean():
        out(f"{label}: passed, but HEAD or the tree changed during the run; not recorded. Re-run.")
    else:
        record(context, level, "pass", command=" ".join(command), revision=start, path=target, git=git, now=now)
        out(f"{label}: verified at {start.commit[:8]} (tree {start.tree[:8]}).")
    return code


def main(
    argv: list[str] | None = None,
    *,
    path: Path | None = None,
    git=None,
    run_command=default_run_command,
    out: Callable[[str], None] = print,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("run", "check"):
        p = sub.add_parser(name)
        p.add_argument("--context", required=True)
        p.add_argument("--level", required=True, choices=LEVELS)
    sub.choices["run"].add_argument("command", nargs=argparse.REMAINDER, help="after --: the test command to run")
    sub.add_parser("show")
    args = parser.parse_args(argv)

    git = git or RealGit()
    try:
        target = path or default_ledger_path(git)
        if args.action == "run":
            command = args.command[1:] if args.command[:1] == ["--"] else args.command
            if not command:
                parser.error("run needs a command after --")
            return run_and_record(args.context, args.level, command, path=target, git=git,
                                  run_command=run_command, out=out)
        if args.action == "check":
            _validate(args.context, args.level)
            revision = current_revision(git)
            result = status(args.context, args.level, revision, path=target)
            out(f"{args.context}/{args.level}: {result} at {revision.commit[:8]} (tree {revision.tree[:8]})")
            return 0 if result == VERIFIED else 1
        data = _load(target)
        revision = current_revision(git)
        shown = False
        for c in sorted(data["contexts"]):
            for lv in sorted(data["contexts"][c]):
                e = _entry(data, c, lv)
                if e:
                    out(f"{c}/{lv}: {_state(e, revision)}; last pass {e['commit'][:8]} (tree {e['tree'][:8]}) at {e.get('timestamp', '?')}")
                    shown = True
        if not shown:
            out("verification ledger is empty")
        return 0
    except (LedgerError, GitError, ValueError) as exc:
        out(str(exc))
        return LEDGER_ERROR_EXIT


if __name__ == "__main__":
    sys.exit(main())
