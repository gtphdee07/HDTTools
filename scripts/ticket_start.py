"""Starts a ticket: pre-checks it, claims it, and builds its worktree (#87).

Backs the /ticket-start skill (docs/agents/ticket-skills.md).

Usage: uv run scripts/ticket_start.py <N> [--android | --not-android]

Stops with the reasons, having changed nothing, when the ticket is closed, has
an open blocker or an assignee, already has a `ticket-<N>` branch or worktree,
or (an Android ticket) another assigned open Android ticket holds the single
emulator. Otherwise it assigns the ticket to the owner (`@me`), creates
`.claude/worktrees/ticket-<N>` on a new `ticket-<N>` branch cut from
`MPSkills` (never from whatever is checked out), runs
scripts/worktree_setup.py inside it, writes the session's directions to
`%TEMP%\\hdttools-status\\ticket-<N>.md`, and prints the next command.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ticket_common import (  # noqa: E402
    BASE_BRANCH, Shell, branch_name, gh_issue, main_checkout, real_shell, scratch_path, worktree_relpath,
)


def parse_blocked_by(body: str) -> list[int]:
    """Ticket numbers listed under the body's `## Blocked by` heading."""
    m = re.search(r"^##\s+Blocked by\s*$(.*?)(?=^#{1,6}\s|\Z)", body or "", re.MULTILINE | re.DOTALL)
    return [int(n) for n in re.findall(r"#(\d+)", m.group(1))] if m else []


def is_android_ticket(issue: dict) -> bool:
    """An Android ticket says so in its title or names a path under `android/`."""
    title = issue.get("title") or ""
    body = issue.get("body") or ""
    return bool(re.search(r"\bandroid\b", title, re.IGNORECASE) or re.search(r"(?<![\w/])android/", body, re.IGNORECASE))


def check_start(*, state, assignees, open_blockers, android, android_in_flight, already_exists=()) -> list[str]:
    reasons = []
    if state != "OPEN":
        reasons.append(f"The ticket is {state.lower()}, not open.")
    if open_blockers:
        reasons.append("Blocked by open ticket(s): " + ", ".join(f"#{n}" for n in open_blockers) + ".")
    if assignees:
        reasons.append("Already assigned to " + ", ".join(assignees) + "; an assigned open ticket is in flight.")
    if android and android_in_flight:
        reasons.append(
            "The single Android emulator is in use: "
            + ", ".join(f"#{n}" for n in android_in_flight)
            + " is an assigned open Android ticket. Android tickets run one at a time."
        )
    reasons.extend(already_exists)
    return reasons


HANDOFF_LINE = (
    "Follow docs/agents/session-handoff.md: don't push, don't close the issue, "
    "and finish with a STATUS comment on the ticket."
)


def implement_prompt(n: int) -> str:
    """The text to paste into the implementing session: the command, then the handoff line."""
    return f"/mattpocock-skills:implement #{n}\n\n{HANDOFF_LINE}"


def directions(n: int) -> str:
    return f"""# Directions for ticket #{n}

Run this in the worktree `{worktree_relpath(n)}` (branch `{branch_name(n)}`, cut from `{BASE_BRANCH}`), pasting this as the first message:

```
{implement_prompt(n)}
```

The rules it points to (docs/agents/session-handoff.md):

- Do not push. Do not close the issue.
- Do not commit `dashboard.svg`, `scripts/dashboard_data/external_status.json` or `.env*`.
- The ticket is already assigned to the owner: that is the claim.
- Finish with `/ticket-finish`, which posts the `STATUS:` comment on the ticket and removes this file.
"""


def _open_blockers(shell: Shell, root: Path, n: int, body: str) -> list[int]:
    found: set[int] = set()
    native = shell(["gh", "api", f"repos/{{owner}}/{{repo}}/issues/{n}/dependencies/blocked_by"], root)
    if native.ok and native.out.strip():
        found.update(int(b["number"]) for b in json.loads(native.out) if str(b.get("state", "")).lower() == "open")
    for ref in parse_blocked_by(body):
        issue = gh_issue(shell, root, ref, "number,state")
        # An unreadable blocker is treated as open: starting past it is the costlier mistake.
        if issue is None or issue.get("state") != "CLOSED":
            found.add(ref)
    return sorted(found)


def _android_in_flight(shell: Shell, root: Path, n: int) -> list[int]:
    r = shell(["gh", "issue", "list", "--state", "open", "--limit", "200", "--json", "number,title,body,assignees"], root)
    others = json.loads(r.out) if r.ok and r.out.strip() else []
    return sorted(o["number"] for o in others if o["number"] != n and o.get("assignees") and is_android_ticket(o))


def _already_exists(shell: Shell, root: Path, n: int) -> list[str]:
    reasons = []
    if shell(["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch_name(n)}"], root).ok:
        reasons.append(f"Branch {branch_name(n)} already exists; a previous run left it behind.")
    if (root / worktree_relpath(n)).exists():
        reasons.append(f"{worktree_relpath(n)} already exists.")
    if not shell(["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{BASE_BRANCH}"], root).ok:
        reasons.append(f"Base branch {BASE_BRANCH} does not exist in this repository.")
    return reasons


def _run_setup(worktree: Path) -> int:
    # Streams its output (npm ci takes minutes), so it bypasses the capturing Shell.
    return subprocess.run([shutil.which("uv") or "uv", "run", "scripts/worktree_setup.py"], cwd=worktree).returncode


def start(
    n: int,
    *,
    shell: Shell,
    root: Path,
    temp: Path | None = None,
    out: Callable[[str], None] = print,
    setup: Callable[[Path], int] = _run_setup,
    android: bool | None = None,
) -> int:
    issue = gh_issue(shell, root, n)
    if issue is None:
        out(f"Could not read ticket #{n} with gh.")
        return 1

    is_android = is_android_ticket(issue) if android is None else android
    reasons = check_start(
        state=issue["state"],
        assignees=[a["login"] for a in issue.get("assignees", [])],
        open_blockers=_open_blockers(shell, root, n, issue.get("body") or ""),
        android=is_android,
        android_in_flight=_android_in_flight(shell, root, n) if is_android else [],
        already_exists=_already_exists(shell, root, n),
    )
    if reasons:
        out(f"STOPPED: ticket #{n} was not started and nothing was changed.")
        for r in reasons:
            out(f"  - {r}")
        return 1

    claim = shell(["gh", "issue", "edit", str(n), "--add-assignee", "@me"], root)
    if not claim.ok:
        out(f"Could not assign #{n}: {claim.err.strip()}")
        return 1
    out(f"Assigned #{n} to the owner.")

    rel = worktree_relpath(n)
    added = shell(["git", "worktree", "add", rel, "-b", branch_name(n), BASE_BRANCH], root)
    if not added.ok:
        shell(["gh", "issue", "edit", str(n), "--remove-assignee", "@me"], root)
        out(f"git worktree add failed: {added.err.strip()}\nThe assignment on #{n} was rolled back.")
        return 1
    worktree = root / rel
    out(f"Created {rel} on {branch_name(n)} from {BASE_BRANCH}.")

    code = setup(worktree)
    if code != 0:
        out(f"scripts/worktree_setup.py failed (exit {code}). Fix it and re-run it inside {rel}; the worktree and the assignment are in place.")
        return 1

    notes = scratch_path(n, temp)
    notes.parent.mkdir(parents=True, exist_ok=True)
    notes.write_text(directions(n), encoding="utf-8")
    out(f"Directions written to {notes}")
    out(f"\nNext: open a session inside {worktree} and paste this as your first message:\n\n{implement_prompt(n)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ticket", type=int)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--android", dest="android", action="store_const", const=True, help="treat as an Android ticket")
    group.add_argument("--not-android", dest="android", action="store_const", const=False, help="treat as not Android")
    args = parser.parse_args(argv)

    root = main_checkout(real_shell, Path.cwd())
    if root is None:
        print("Not inside a git repository.", file=sys.stderr)
        return 1
    return start(args.ticket, shell=real_shell, root=root, android=args.android)


if __name__ == "__main__":
    sys.exit(main())
