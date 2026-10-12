"""Merges a finished ticket into MPSkills (#87).

Backs the /ticket-merge skill (docs/agents/ticket-skills.md). Run it from the
main checkout, after the skill has re-verified the work independently.

Usage:
    uv run scripts/ticket_merge.py preflight <N> [--allow-status]
    uv run scripts/ticket_merge.py baseline <N>
    uv run scripts/ticket_merge.py merge <N>
    uv run scripts/ticket_merge.py close <N> --comment-file FILE

`preflight` exits 1 unless this is the main checkout, MPSkills is checked out
and clean, `ticket-<N>` has commits, and the ticket's latest `STATUS:` comment
is READY TO MERGE (`--allow-status` accepts PARTIAL/BLOCKED when the owner has
decided to merge anyway). `baseline` says whether MPSkills has moved since the
ticket was cut (BASELINE UNCHANGED means the merged tree equals the branch tip, so
the merged-tree test run can be skipped). `merge` makes a `--no-ff` merge commit on MPSkills,
aborting cleanly on a conflict. `close` posts FILE (a criterion-to-test table)
with the merge sha, closes the issue, removes the worktree and deletes the
branch. On Windows, when git cannot delete the worktree because its path is too
long (deep node_modules), `close` finishes the delete itself with a long-path
`rmdir`, only for that error and only for ticket N's own worktree folder. When git
refuses because the worktree has modified or untracked files, `close` lists them,
removes nothing and leaves the decision (commit, discard, keep) to the owner.
Nothing here pushes: that stays the owner's call.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ticket_common import (  # noqa: E402
    BASE_BRANCH, Shell, branch_name, gh_issue, git, main_checkout, real_shell, worktree_relpath,
)


def latest_status_comment(comments: list[dict]) -> str | None:
    """The newest comment that starts with `STATUS:`."""
    for c in reversed(comments):
        body = (c.get("body") or "").lstrip()
        if body.startswith("STATUS:"):
            return body
    return None


def preflight(n: int, *, shell: Shell, root: Path, allow_status: bool = False) -> list[str]:
    reasons = []
    top = git(shell, root, "rev-parse", "--show-toplevel").out.strip()
    main = main_checkout(shell, root)
    if main is None or not top or Path(top).resolve() != main.resolve():
        reasons.append("Not the main checkout; run this from the repository's main checkout, not from a worktree.")
    current = git(shell, root, "branch", "--show-current").out.strip()
    if current != BASE_BRANCH:
        reasons.append(f"{BASE_BRANCH} must be checked out here (found {current or 'a detached HEAD'}).")
    if git(shell, root, "status", "--porcelain").out.strip():
        reasons.append("The main checkout has uncommitted changes.")

    ahead = git(shell, root, "rev-list", "--count", f"{BASE_BRANCH}..{branch_name(n)}")
    if not ahead.ok or not ahead.out.strip().isdigit() or int(ahead.out) == 0:
        reasons.append(f"Branch {branch_name(n)} is missing or has no commits ahead of {BASE_BRANCH}.")

    issue = gh_issue(shell, root, n, "number,title,state,comments")
    if issue is None:
        reasons.append(f"Could not read ticket #{n} with gh.")
    else:
        comment = latest_status_comment(issue.get("comments", []))
        if comment is None:
            reasons.append(f"Ticket #{n} has no STATUS: comment; run /ticket-finish in its worktree first.")
        else:
            status = comment.splitlines()[0].strip()
            if status != "STATUS: READY TO MERGE" and not allow_status:
                reasons.append(f"The latest status is `{status}`, not READY TO MERGE.")
            reported = re.search(rf"`{re.escape(branch_name(n))}` at `([0-9a-f]+)`", comment)
            tip = git(shell, root, "rev-parse", branch_name(n)).out.strip()
            if reported and tip and not tip.startswith(reported.group(1)):
                reasons.append(
                    f"{branch_name(n)} is at {tip[:7]} but the STATUS comment vouches for {reported.group(1)}; "
                    "commits were added after it. Re-run /ticket-finish."
                )
    return reasons


def baseline_status(n: int, *, shell: Shell, root: Path) -> tuple[bool, str]:
    """Whether MPSkills has moved since ticket N was cut, so the merged tree could
    differ from the branch tip. When it has not, the merge result is exactly the
    code the branch's tests already ran against, and re-running them on the merged
    tree repeats that run. Returns (moved, message); anything uncomparable counts
    as moved, so the safe default is to test."""
    cut = git(shell, root, "merge-base", BASE_BRANCH, branch_name(n))
    tip = git(shell, root, "rev-parse", BASE_BRANCH)
    if not cut.ok or not tip.ok:
        return True, (
            f"BASELINE MOVED (could not compare {branch_name(n)} with {BASE_BRANCH}): treat it as moved and "
            "run the planner on the merged tree after the merge."
        )
    cut_sha, tip_sha = cut.out.strip(), tip.out.strip()
    if cut_sha == tip_sha:
        return False, (
            f"BASELINE UNCHANGED: {branch_name(n)} was cut from the current {BASE_BRANCH} tip ({tip_sha[:7]}), so the "
            "merged tree will be identical to the branch tip. Skip the merged-tree test run; the worktree run covered this code."
        )
    count = git(shell, root, "rev-list", "--count", f"{cut_sha}..{BASE_BRANCH}").out.strip() or "?"
    files = [f for f in git(shell, root, "diff", "--name-only", cut_sha, BASE_BRANCH).out.splitlines() if f]
    listing = "".join(f"\n  {f}" for f in files[:20]) + (f"\n  ... and {len(files) - 20} more" if len(files) > 20 else "")
    plural = "commit" if count == "1" else "commits"
    return True, (
        f"BASELINE MOVED: {BASE_BRANCH} has {count} {plural} that {branch_name(n)} was not cut from; "
        f"they changed:{listing or ' (no files)'}\n"
        "After the merge, run `uv run scripts/test_planner.py --level issue --base HEAD^1` on the merged tree "
        "and run what it lists."
    )


def merge(n: int, *, shell: Shell, root: Path, out: Callable[[str], None] = print) -> int:
    issue = gh_issue(shell, root, n, "number,title") or {}
    title = issue.get("title") or f"ticket {n}"
    message = f"Merge #{n} {title} ({branch_name(n)})"
    result = git(shell, root, "merge", "--no-ff", "-m", message, branch_name(n))
    if not result.ok:
        git(shell, root, "merge", "--abort")
        out(f"Merge conflict merging {branch_name(n)} into {BASE_BRANCH}; the merge was aborted and nothing changed.")
        out(result.out.strip() or result.err.strip())
        return 1
    out(f"Merged {branch_name(n)} into {BASE_BRANCH} at {git(shell, root, 'rev-parse', '--short', 'HEAD').out.strip()} (not pushed).")
    return 0


def worktree_folder(root: Path, n: int) -> Path:
    """The one folder the long-path fallback may delete: ticket N's own worktree."""
    if n < 1:
        raise ValueError(f"not a ticket number: {n}")
    target = (root / worktree_relpath(n)).resolve()
    if target.parent != (root / ".claude" / "worktrees").resolve():
        raise ValueError(f"{target} is not directly under .claude/worktrees")
    return target


def long_path_remove_command(path: Path) -> list[str]:
    """Deletes a folder tree git cannot (Windows MAX_PATH, deep node_modules).

    The `\\\\?\\` prefix lifts the limit; see docs/agents/worktree-setup.md.
    """
    return ["cmd", "/c", "rmdir", "/s", "/q", "\\\\?\\" + str(path)]


def _remove_worktree_folder(n: int, removed_err: str, *, shell: Shell, root: Path, windows: bool) -> str | None:
    """After a failed `git worktree remove`: deletes the folder if, and only if, git
    failed because the path is too long. Returns None once the worktree is gone,
    else the reason it is not."""
    if not windows or "filename too long" not in removed_err.lower():
        return removed_err.strip()
    target = worktree_folder(root, n)
    shell(long_path_remove_command(target), root)
    # An empty folder left behind is only a locked directory entry (an open session's working
    # directory): git no longer sees a worktree there, so prune and carry on; close() reports it.
    if target.exists() and any(target.iterdir()):
        return f"{target} is still there after the long-path delete (something may be holding it open; close it and retry)."
    pruned = git(shell, root, "worktree", "prune")
    return None if pruned.ok else f"git worktree prune failed: {pruned.err.strip()}"


def _uncommitted_files(n: int, removed_err: str, *, shell: Shell, root: Path) -> list[str] | None:
    """After a failed `git worktree remove`: None unless git refused over modified or
    untracked files (so any other failure keeps its own message), else the
    `git status --short` lines, which may be empty (e.g. a dirty submodule)."""
    if "modified or untracked files" not in removed_err.lower():
        return None
    status = git(shell, worktree_folder(root, n), "status", "--short")
    return status.out.splitlines() if status.ok else []


def close(
    n: int,
    comment_file: Path,
    *,
    shell: Shell,
    root: Path,
    out: Callable[[str], None] = print,
    windows: bool | None = None,
) -> int:
    branch = branch_name(n)
    if not git(shell, root, "merge-base", "--is-ancestor", branch, BASE_BRANCH).ok:
        out(f"{branch} is not merged into {BASE_BRANCH}; run the merge step first. Nothing was closed.")
        return 1
    body = Path(comment_file).read_text(encoding="utf-8")
    if "|---" not in body:
        out("The comment needs a criterion-to-test table (| Criterion | Proven by |); nothing was closed.")
        return 1

    sha = git(shell, root, "rev-parse", "--short", BASE_BRANCH).out.strip()
    comment = f"Merged into {BASE_BRANCH} at {sha} (`--no-ff`); not pushed.\n\n{body.strip()}\n"
    closed = shell(["gh", "issue", "close", str(n), "--comment", comment], root)
    if not closed.ok:
        out(f"gh issue close failed: {closed.err.strip()}")
        return 1
    out(f"Closed #{n}.")

    # Removal failures are handled inline: dirty worktree, long path / other, branch delete.
    # If more paths accumulate here, consider factoring this out, e.g. one function that
    # maps git's stderr to a kind (dirty, too long, other) so the matching lives in one
    # place. The dirty check must stay ahead of the long-path delete, which is recursive
    # and must never touch a worktree with uncommitted files. See #93.
    removed = git(shell, root, "worktree", "remove", worktree_relpath(n))
    uncommitted = None if removed.ok else _uncommitted_files(n, removed.err, shell=shell, root=root)
    if uncommitted is not None:
        listing = "".join(f"\n  {line}" for line in uncommitted) or "\n  (git status listed none; check the worktree by hand)"
        out(
            f"#{n} is closed, but its worktree has modified or untracked files that need a decision, so nothing was removed:"
            f"{listing}\n"
            f"Commit, discard or keep them, then re-run only the removal: `git worktree remove {worktree_relpath(n)}` "
            f"and `git branch -d {branch}`."
        )
        return 1
    failure = None if removed.ok else _remove_worktree_folder(
        n, removed.err, shell=shell, root=root, windows=os.name == "nt" if windows is None else windows
    )
    if failure is not None:
        out(
            f"#{n} is closed, but the worktree was not removed: {failure}\n"
            "See 'Removing a worktree on Windows' in docs/agents/worktree-setup.md, then run "
            f"`git worktree prune` and `git branch -d {branch}`."
        )
        return 1
    deleted = git(shell, root, "branch", "-d", branch)
    if not deleted.ok:
        out(f"Worktree removed, but `git branch -d {branch}` failed: {deleted.err.strip()}")
        return 1
    leftover = worktree_folder(root, n)
    if leftover.exists():
        out(
            f"Deleted {branch} and pruned its worktree, but the empty folder {worktree_relpath(n)} is still on disk: "
            "an open session or terminal is probably sitting in it. Once that is closed, delete it with "
            f'`rmdir "{leftover}"`. Nothing was pushed; ask the owner before any push.'
        )
        return 0
    out(f"Removed {worktree_relpath(n)} and deleted {branch}. Nothing was pushed; ask the owner before any push.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("preflight")
    p.add_argument("ticket", type=int)
    p.add_argument("--allow-status", action="store_true")
    sub.add_parser("baseline").add_argument("ticket", type=int)
    sub.add_parser("merge").add_argument("ticket", type=int)
    c = sub.add_parser("close")
    c.add_argument("ticket", type=int)
    c.add_argument("--comment-file", type=Path, required=True)
    args = parser.parse_args(argv)

    root = Path.cwd()
    if args.command == "preflight":
        reasons = preflight(args.ticket, shell=real_shell, root=root, allow_status=args.allow_status)
        for r in reasons:
            print(f"  - {r}")
        print("Ready to merge." if not reasons else f"STOPPED: ticket #{args.ticket} was not merged.")
        return 1 if reasons else 0
    if args.command == "baseline":
        print(baseline_status(args.ticket, shell=real_shell, root=root)[1])
        return 0
    if args.command == "merge":
        return merge(args.ticket, shell=real_shell, root=root)
    return close(args.ticket, args.comment_file, shell=real_shell, root=root)


if __name__ == "__main__":
    sys.exit(main())
