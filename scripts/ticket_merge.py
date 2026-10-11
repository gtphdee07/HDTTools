"""Merges a finished ticket into MPSkills (#87).

Backs the /ticket-merge skill (docs/agents/ticket-skills.md). Run it from the
main checkout, after the skill has re-verified the work independently.

Usage:
    uv run scripts/ticket_merge.py preflight <N> [--allow-status]
    uv run scripts/ticket_merge.py merge <N>
    uv run scripts/ticket_merge.py close <N> --comment-file FILE

`preflight` exits 1 unless this is the main checkout, MPSkills is checked out
and clean, `ticket-<N>` has commits, and the ticket's latest `STATUS:` comment
is READY TO MERGE (`--allow-status` accepts PARTIAL/BLOCKED when the owner has
decided to merge anyway). `merge` makes a `--no-ff` merge commit on MPSkills,
aborting cleanly on a conflict. `close` posts FILE (a criterion-to-test table)
with the merge sha, closes the issue, removes the worktree and deletes the
branch. Nothing here pushes: that stays the owner's call.
"""

from __future__ import annotations

import argparse
import json
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


def close(n: int, comment_file: Path, *, shell: Shell, root: Path, out: Callable[[str], None] = print) -> int:
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

    removed = git(shell, root, "worktree", "remove", worktree_relpath(n))
    if not removed.ok:
        out(
            f"#{n} is closed, but the worktree was not removed: {removed.err.strip()}\n"
            "See 'Removing a worktree on Windows' in docs/agents/worktree-setup.md, then run "
            f"`git worktree prune` and `git branch -d {branch}`."
        )
        return 1
    deleted = git(shell, root, "branch", "-d", branch)
    if not deleted.ok:
        out(f"Worktree removed, but `git branch -d {branch}` failed: {deleted.err.strip()}")
        return 1
    out(f"Removed {worktree_relpath(n)} and deleted {branch}. Nothing was pushed; ask the owner before any push.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("preflight")
    p.add_argument("ticket", type=int)
    p.add_argument("--allow-status", action="store_true")
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
    if args.command == "merge":
        return merge(args.ticket, shell=real_shell, root=root)
    return close(args.ticket, args.comment_file, shell=real_shell, root=root)


if __name__ == "__main__":
    sys.exit(main())
