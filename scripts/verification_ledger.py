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

Per-suite passes (#128): the same file also remembers, for each suite command,
every tree it passed at (`suites` section, newest SUITE_PASSES_KEPT per
command), so /ticket-finish and /ticket-merge can skip a suite that already
passed on this exact content:

  uv run scripts/verification_ledger.py suite -- uv run pytest -n auto -m "core and not slow"
  uv run scripts/verification_ledger.py check-suite "uv run pytest ..."

`suite_verdict` answers "did suite S pass at tree T?" and never raises: a
failed, skipped or declined record, a missing ledger and an unreadable ledger
all answer "run it". A fail, skip or declined run also drops a pass recorded for
that same tree, so a flaky suite is not vouched for.
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
OUTCOMES = ("pass", "fail", "skipped", "declined")  # declined: a paid suite the owner did not approve
SUITE_PASSES_KEPT = 25  # per suite command, newest first; older trees are forgotten

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
        return {"contexts": {}, "suites": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LedgerError(f"verification ledger {path} is unreadable ({exc}); fix or delete it") from exc
    contexts = data.get("contexts") if isinstance(data, dict) else None
    if not isinstance(contexts, dict) or not all(isinstance(v, dict) for v in contexts.values()):
        raise LedgerError(f"verification ledger {path} has an unexpected shape; fix or delete it")
    suites = data.setdefault("suites", {})
    if not isinstance(suites, dict) or not all(
        isinstance(trees, dict) and all(isinstance(e, dict) for e in trees.values()) for trees in suites.values()
    ):
        raise LedgerError(f"verification ledger {path} has an unexpected shape; fix or delete it")
    return data


def _entry(data: dict, context: str, level: str) -> dict | None:
    entry = data["contexts"].get(context, {}).get(level)
    return entry if isinstance(entry, dict) and entry.get("commit") and entry.get("tree") else None


def last_verified(context: str, level: str, *, path: Path | None = None) -> str | None:
    """The commit of the last recorded pass, or None."""
    entry = _entry(_load(path or default_ledger_path()), context, level)
    return entry["commit"] if entry else None


def last_verified_at(context: str, level: str, *, path: Path | None = None) -> str | None:
    """The UTC timestamp (`%Y-%m-%dT%H:%M:%SZ`) of the last recorded pass, or None."""
    entry = _entry(_load(path or default_ledger_path()), context, level)
    return entry.get("timestamp") if entry else None


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
    _write(target, data)
    return True


def _write(target: Path, data: dict) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, scratch = tempfile.mkstemp(dir=target.parent, prefix=target.name + ".", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
    os.replace(scratch, target)


def suite_key(command: str) -> str:
    """A suite is identified by its command line, whitespace-normalised."""
    return " ".join(command.split())


@dataclass(frozen=True)
class SuiteVerdict:
    skip: bool  # True only when a pass is recorded for exactly this content
    reason: str
    tree: str = ""


def suite_verdict(command: str, revision: Revision, *, path: Path | None = None, git=None) -> SuiteVerdict:
    """Did this suite pass at this tree? Never raises: anything the ledger cannot vouch for
    (no record, a non-pass record, no ledger, an unreadable ledger, no git) is "run it"."""
    try:
        data = _load(path or default_ledger_path(git))
    except (LedgerError, GitError, OSError) as exc:
        return SuiteVerdict(False, f"run: ledger unavailable ({exc})")
    entry = data["suites"].get(suite_key(command), {}).get(revision.tree)
    if entry is not None and entry.get("outcome") == "pass":
        return SuiteVerdict(True, f"already passed at tree {revision.tree[:8]}", revision.tree)
    return SuiteVerdict(False, "run: no recorded pass at this tree")


def last_suite_pass_tree(command: str, *, path: Path | None = None, git=None) -> str | None:
    """The tree of the newest recorded pass of this suite (any tree), or None. Never raises."""
    try:
        data = _load(path or default_ledger_path(git))
    except (LedgerError, GitError, OSError):
        return None
    passes = [(e.get("timestamp", ""), tree) for tree, e in data["suites"].get(suite_key(command), {}).items()
              if e.get("outcome") == "pass"]
    return max(passes)[1] if passes else None


def record_suite(
    command: str,
    outcome: str,
    *,
    revision: Revision | None = None,
    carried_from: str | None = None,
    path: Path | None = None,
    git=None,
    now: str | None = None,
) -> bool:
    """Remember a suite result for a tree. Only a pass is written; a fail, skipped or declined
    result writes nothing except dropping a pass already held for the same tree. `carried_from`
    marks a pass derived from an earlier tree whose relevant files did not change. Returns
    whether the ledger was written."""
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {OUTCOMES}, got {outcome!r}")
    git = git or RealGit()
    target = path or default_ledger_path(git)
    data = _load(target)
    revision = revision or current_revision(git)
    key = suite_key(command)
    trees = data["suites"].setdefault(key, {})
    if outcome != "pass":
        dropped = trees.pop(revision.tree, None) is not None
        if not trees:
            del data["suites"][key]
        if dropped:
            _write(target, data)
        return dropped
    entry = {"commit": revision.commit, "outcome": "pass", "timestamp": now or _now()}
    if carried_from:
        entry["carried_from"] = carried_from
    trees[revision.tree] = entry
    for tree in sorted(trees, key=lambda t: (trees[t].get("timestamp", ""), t), reverse=True)[SUITE_PASSES_KEPT:]:
        del trees[tree]
    _write(target, data)
    return True


def _run_guarded(label, command, *, git, run_command, out, on_pass) -> int:
    """Runs the command and calls `on_pass(revision)` only if it passed on a clean tree whose
    HEAD and tree did not move. Returns the command's exit code (127 if it could not start)."""
    start = current_revision(git)
    clean = git.is_clean()
    try:
        code = run_command(command, cwd=REPO_ROOT).returncode
    except OSError as exc:
        out(f"could not start {command[0]!r} ({exc}); {label} not recorded.")
        return COULD_NOT_START_EXIT
    if code != 0:
        out(f"{label}: failed (exit {code}); ledger unchanged.")
    elif not clean:
        out(f"{label}: passed, but the tree had uncommitted changes to tracked files; not recorded. Commit, then re-run.")
    elif current_revision(git) != start or not git.is_clean():
        out(f"{label}: passed, but HEAD or the tree changed during the run; not recorded. Re-run.")
    else:
        on_pass(start)
        out(f"{label}: verified at {start.commit[:8]} (tree {start.tree[:8]}).")
    return code


def run_suite_and_record(
    command: list[str],
    *,
    path: Path | None = None,
    git=None,
    run_command=default_run_command,
    now: str | None = None,
    out: Callable[[str], None] = print,
    key: str | None = None,
) -> int:
    """Runs a suite and remembers a pass for the tree it ran at (same guards as run_and_record).
    `key` is the suite's command line as the planner writes it; splitting it into an argument list
    loses its quotes, so a caller that split it passes the original to be recorded and looked up."""
    git = git or RealGit()
    target = path or default_ledger_path(git)
    _load(target)  # refuse before running anything if the ledger cannot be updated
    text = key or " ".join(command)
    return _run_guarded(
        text, command, git=git, run_command=run_command, out=out,
        on_pass=lambda rev: record_suite(text, "pass", revision=rev, path=target, git=git, now=now),
    )


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
    return _run_guarded(
        f"{context}/{level}", command, git=git, run_command=run_command, out=out,
        on_pass=lambda rev: record(context, level, "pass", command=" ".join(command), revision=rev,
                                   path=target, git=git, now=now),
    )


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
    sub.add_parser("suite").add_argument("command", nargs=argparse.REMAINDER, help="after --: the suite command to run and remember")
    sub.add_parser("check-suite").add_argument("command", help="the suite command line, quoted")
    args = parser.parse_args(argv)

    git = git or RealGit()
    try:
        target = path or default_ledger_path(git)
        if args.action == "suite":
            command = args.command[1:] if args.command[:1] == ["--"] else args.command
            if not command:
                parser.error("suite needs a command after --")
            return run_suite_and_record(command, path=target, git=git, run_command=run_command, out=out)
        if args.action == "check-suite":
            if not git.is_clean():
                out(f"{args.command}: run: uncommitted changes to tracked files, so no recorded pass vouches for this tree")
                return 1
            verdict = suite_verdict(args.command, current_revision(git), path=target)
            out(f"{args.command}: {verdict.reason}")
            return 0 if verdict.skip else 1
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
