"""Finishes a ticket: checks the worktree and posts the STATUS comment (#87).

Backs the /ticket-finish skill (docs/agents/ticket-skills.md). Run it inside
the ticket's worktree, after `/implement`.

Usage:
    uv run scripts/ticket_finish.py preflight
    uv run scripts/ticket_finish.py suites [--json FILE]
    uv run scripts/ticket_finish.py criteria
    uv run scripts/ticket_finish.py post REPORT.json [--dry-run]

`preflight` exits 1 when the tree is dirty, the branch has no commits ahead of
MPSkills, or a commit carries a file a feature branch must not (dashboard.svg,
external_status.json, `.env*`). `criteria` prints the issue's acceptance
criteria so the report covers every one; they come from the latest `## Agent
Brief` comment, else the issue body. `post` reads the report the skill wrote,
recomputes the git facts itself, and posts the comment from
docs/agents/session-handoff.md, then deletes the ticket's scratch file. It
refuses `STATUS: READY TO MERGE` unless the tree is clean, every suite in the
report passed, each acceptance criterion names a test, and, when the ticket
lists owner decisions under `## Decisions`, a comment starting `DECISIONS`
records them. `PARTIAL` and `BLOCKED` are never refused for those reasons, but
must say what is not done.

`suites` (#128) plans the session level for the branch's diff against its
merge-base with MPSkills and runs only the free suites the verification ledger
does not show as passed at the current tree, recording each pass. After a review
fix a suite whose last pass was at an earlier tree is skipped when no file it
depends on differs between the two trees (a Python suite counts any change), and
its pass is carried forward. Stale External surfaces, device tests and paid
suites are listed, never run here. It prints each suite as `skip` or `run` and
can write the report's `suites` entries (`--json`); `post` refuses a suite
reported as skipped that the ledger does not show as passed at the tree.

REPORT.json: {"status", "criteria": [{"criterion", "proven_by"}],
"suites": [{"command", "passed", "summary"}], "review", "not_done",
"owner_actions", "followups"}.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_planner as planner  # noqa: E402
from ticket_common import (  # noqa: E402
    BASE_BRANCH, Shell, gh_issue, git_out, real_shell, runs_here, scratch_path, ticket_from_branch,
)

STATUSES = ("READY TO MERGE", "PARTIAL", "BLOCKED")


@dataclass(frozen=True)
class SuiteResult:
    command: str
    passed: bool
    summary: str = ""
    skipped: bool = False  # not run here: the ledger shows it already passed at this tree (#128)


@dataclass(frozen=True)
class Decision:
    action: str  # "skip" (passed at this tree) | "carry" (earlier pass still holds) | "run"
    reason: str
    carried_from: str | None = None


def _ledger():
    """The verification ledger (#65, #128); imported late because it pulls in the release tooling."""
    import verification_ledger

    return verification_ledger


def session_files(shell: Shell, root: Path) -> list[str]:
    """What the branch changes against the commit it was cut from (merge-base, so a moved MPSkills
    does not change the plan between /ticket-finish and /ticket-merge)."""
    return [f for f in git_out(shell, root, "diff", "--name-only", f"{BASE_BRANCH}...HEAD").splitlines() if f]


def decide_suite(selection, revision, *, shell: Shell, root: Path, config: dict, ledger, git_state) -> Decision:
    """Skip a suite that passed at this tree. After a review fix, also skip one whose last recorded pass
    was at another tree when no file it depends on differs between the two trees; anything unsure runs."""
    verdict = ledger.suite_verdict(selection.command, revision, git=git_state)
    if verdict.skip:
        return Decision("skip", verdict.reason)
    previous = ledger.last_suite_pass_tree(selection.command, git=git_state)
    if previous and previous != revision.tree:
        diff = shell(["git", "diff", "--name-only", "--no-renames", previous, revision.tree], root)  # a rename lists both paths
        if diff.ok:
            changed = [f for f in diff.out.splitlines() if f]
            if not planner.suite_affected(selection, changed, config):
                return Decision("carry", f"no file it depends on changed since its pass at tree {previous[:8]}", previous)
            return Decision("run", f"files it depends on changed since its pass at tree {previous[:8]}")
    return Decision("run", verdict.reason)


def run_suites(
    *,
    shell: Shell,
    root: Path,
    config: dict,
    markers: set[str],
    ledger,
    git_state,
    run_command,
    out: Callable[[str], None] = print,
) -> list[dict]:
    """Runs the session-level plan for the branch, running only suites the ledger cannot vouch for
    at the current tree and recording each pass. Returns the report's `suites` entries."""
    files = session_files(shell, root)
    plan = planner.plan(files, config, markers, level="session")
    revision = ledger.current_revision(git_state)
    results: list[dict] = []
    for sel in plan.selections:
        if not runs_here(sel):
            out(f"not run here: {sel.command}    # {sel.reason}")
            continue
        decision = decide_suite(sel, revision, shell=shell, root=root, config=config, ledger=ledger, git_state=git_state)
        if decision.action != "run":
            if decision.action == "carry":
                ledger.record_suite(sel.command, "pass", revision=revision, carried_from=decision.carried_from, git=git_state)
            out(f"skip: {sel.command}    # {decision.reason}")
            results.append({"command": sel.command, "passed": True, "skipped": True, "summary": decision.reason})
            continue
        out(f"run: {sel.command}    # {decision.reason}")
        try:
            code = ledger.run_suite_and_record(shlex.split(sel.command), git=git_state, run_command=run_command, out=out,
                                               key=sel.command)
        except (ledger.LedgerError, ledger.GitError) as exc:  # an unreadable ledger means run it, just unrecorded
            out(f"{exc}; running {sel.command} without recording it.")
            code = run_command(shlex.split(sel.command), cwd=root).returncode
        recorded = ledger.suite_verdict(sel.command, revision, git=git_state).skip
        results.append({
            "command": sel.command, "passed": code == 0, "skipped": False,
            "summary": ("passed, recorded at this tree" if recorded else "passed, NOT recorded (see above)") if code == 0 else f"exit {code}",
        })
    if not plan.selections:
        out("the session-level plan lists no suite for this branch")
    return results


def parse_criteria(body: str) -> list[str]:
    # Either a `## Acceptance criteria` heading, or the `**Acceptance criteria:**` label an Agent Brief uses
    # (which ends at the next bold label or heading).
    m = re.search(
        r"^(?:##\s+Acceptance criteria|\*\*Acceptance criteria:?\*\*:?)\s*$(.*?)(?=^##\s|^\*\*[^*\n]+\*\*:?\s*$|\Z)",
        body or "",
        re.MULTILINE | re.DOTALL,
    )
    if not m:
        return []
    return [c.strip() for c in re.findall(r"^\s*-\s*\[[ xX]\]\s*(.+?)\s*$", m.group(1), re.MULTILINE)]


def issue_criteria(issue: dict) -> list[str]:
    """The ticket's acceptance criteria: from its latest `## Agent Brief` comment, else from the body.

    `/triage` calls the brief the authoritative specification, so when one exists it wins even if the
    body also has a checklist (or none under a heading `parse_criteria` knows). `gh` lists comments
    oldest first, so the last brief is the most recent.
    """
    bodies = [c.get("body") or "" for c in issue.get("comments") or []]
    briefs = [b for b in bodies if re.search(r"^##\s+Agent Brief", b, re.MULTILINE)]
    return parse_criteria(briefs[-1] if briefs else issue.get("body") or "")


# A ticket that needs decisions from the owner lists them under `## Decisions` (in the body or its Agent
# Brief). The session asks them with AskUserQuestion, then posts the questions and the answers as a comment
# that starts with DECISIONS (docs/agents/session-handoff.md), so nobody writes answers into the ticket or
# has an agent re-read them. A session that could not ask posts the defaults it assumed under the same word.
DECISIONS_HEADING = re.compile(r"^##\s+Decisions\s*$", re.MULTILINE)


def has_decisions_section(issue: dict) -> bool:
    texts = [issue.get("body") or ""]
    briefs = [c.get("body") or "" for c in issue.get("comments") or []]
    briefs = [b for b in briefs if re.search(r"^##\s+Agent Brief", b, re.MULTILINE)]
    if briefs:
        texts.append(briefs[-1])
    return any(DECISIONS_HEADING.search(t) for t in texts)


def decisions_recorded(issue: dict) -> bool:
    return any(
        (c.get("body") or "").lstrip("﻿ \t\r\n").startswith("DECISIONS") for c in issue.get("comments") or []
    )


# The one env file that is committed on purpose: public client config (VITE_* values that ship in the
# browser bundle). Every other `.env*` file may hold credentials and stays out of a feature branch.
TRACKED_ENV_FILES = ("web/.env.production",)


def forbidden_paths(paths) -> list[str]:
    bad = []
    for p in paths:
        posix = p.replace("\\", "/")
        name = PurePosixPath(posix).name
        if posix in TRACKED_ENV_FILES:
            continue
        if name in ("dashboard.svg", "external_status.json") or name.startswith(".env"):
            bad.append(p)
    return bad


def _proven(rows) -> dict[str, str]:
    return {r["criterion"].strip(): r.get("proven_by", "").strip() for r in rows}


def refusals(
    status, *, tree_clean, suites, rows, criteria, not_done="", branch_problems=(), decisions_missing=False
) -> list[str]:
    if status not in STATUSES:
        return [f"Unknown status {status!r}; use one of: {', '.join(STATUSES)}."]
    if status != "READY TO MERGE":
        return [] if not_done.strip() else [f"{status} must say what is not done and why (not_done)."]

    reasons = list(branch_problems)
    if not tree_clean:
        reasons.append("The working tree is dirty (uncommitted changes); commit or discard them first.")
    if not suites:
        reasons.append("No suite results were recorded; run the required suites.")
    reasons.extend(f"Required suite failed: `{s.command}`" + (f" ({s.summary})" if s.summary else "") for s in suites if not s.passed)
    if not criteria:
        reasons.append("The ticket lists no acceptance criteria, so nothing can be proven.")
    proven = _proven(rows)
    reasons.extend(f"No test named for criterion: {c}" for c in criteria if not proven.get(c.strip()))
    if decisions_missing:
        reasons.append(
            "The ticket has a Decisions section but no DECISIONS comment: ask the owner with AskUserQuestion "
            "and post the questions and answers (docs/agents/session-handoff.md)."
        )
    return reasons


def _cell(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def render_comment(*, status, branch, sha, worktree, pushed, criteria, rows, suites, review, not_done, owner_actions, followups) -> str:
    proven = _proven(rows)
    table = [f"| {_cell(c)} | {_cell(proven.get(c.strip()) or 'NOT PROVEN')} |" for c in criteria]
    ran = "; ".join(
        f"`{s.command}`: {'SKIPPED (already passed at this tree)' if s.skipped else 'PASS' if s.passed else 'FAIL'}"
        + (f" - {s.summary}" if s.summary else "")
        for s in suites
    ) or "none"
    return "\n".join(
        [
            f"STATUS: {status}",
            "",
            f"Branch: `{branch}` at `{sha}` (worktree: `{worktree}`; pushed: {'yes' if pushed else 'no'})",
            "",
            "| Criterion | Proven by (test file and name) |",
            "|---|---|",
            *table,
            "",
            f"Commands run and results: {ran}",
            f"Code review: {review.strip() or 'none'}",
            "",
            f"Not done, and why: {not_done.strip() or 'nothing'}",
            f"Owner actions needed: {owner_actions.strip() or 'none'}",
            f"Follow-up tickets filed: {followups.strip() or 'none'}",
            "",
        ]
    )


def is_pushed(shell: Shell, root: Path) -> bool:
    branch = git_out(shell, root, "branch", "--show-current")
    remote = f"refs/remotes/origin/{branch}"
    if not branch or not shell(["git", "rev-parse", "--verify", "--quiet", remote], root).ok:
        return False
    return shell(["git", "merge-base", "--is-ancestor", "HEAD", remote], root).ok


def preflight(shell: Shell, root: Path) -> tuple[list[str], dict]:
    branch = git_out(shell, root, "branch", "--show-current")
    ahead_text = git_out(shell, root, "rev-list", "--count", f"{BASE_BRANCH}..HEAD")
    ahead = int(ahead_text) if ahead_text.isdigit() else 0
    info = {"branch": branch, "ahead": ahead, "sha": git_out(shell, root, "rev-parse", "--short", "HEAD")}

    reasons = []
    if ticket_from_branch(branch) is None:
        reasons.append(f"Branch {branch!r} is not a ticket-<N> branch; run this inside the ticket's worktree.")
    if git_out(shell, root, "status", "--porcelain"):
        reasons.append("The working tree has uncommitted changes (git status is not clean).")
    if ahead == 0:
        reasons.append(f"The branch has no commits ahead of {BASE_BRANCH}; /implement committed nothing.")
    changed = git_out(shell, root, "diff", "--name-only", f"{BASE_BRANCH}...HEAD").splitlines()
    reasons.extend(f"Committed file a feature branch must not carry: {p}" for p in forbidden_paths(changed))
    return reasons, info


def post(
    report_path: Path,
    *,
    shell: Shell,
    root: Path,
    temp: Path | None = None,
    out: Callable[[str], None] = print,
    dry_run: bool = False,
    ledger_shows_pass: Callable[[str], bool] | None = None,
) -> int:
    branch = git_out(shell, root, "branch", "--show-current")
    n = ticket_from_branch(branch)
    if n is None:
        out(f"Branch {branch!r} is not a ticket-<N> branch; run this inside the ticket's worktree.")
        return 1
    issue = gh_issue(shell, root, n, "number,title,body,comments")
    if issue is None:
        out(f"Could not read ticket #{n} with gh.")
        return 1

    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    status = report.get("status", "")
    criteria = issue_criteria(issue)
    rows = report.get("criteria", [])
    raw_suites = report.get("suites", [])
    unclear = [s.get("command", "?") for s in raw_suites if not isinstance(s.get("passed"), bool)]
    if unclear:
        out(f"REFUSED: `passed` must be true or false (not text) for: {', '.join(unclear)}. Nothing was posted.")
        return 1
    unclear = [s["command"] for s in raw_suites if "skipped" in s and not isinstance(s["skipped"], bool)]
    if unclear:
        out(f"REFUSED: `skipped` must be true or false for: {', '.join(unclear)}. Nothing was posted.")
        return 1
    suites = [SuiteResult(s["command"], s["passed"], s.get("summary", ""), s.get("skipped", False)) for s in raw_suites]
    tree_clean = not git_out(shell, root, "status", "--porcelain")
    skipped = [s.command for s in suites if s.skipped]
    if skipped:
        shows_pass = ledger_shows_pass or _ledger_shows_pass(root)
        unbacked = [c for c in skipped if not (tree_clean and shows_pass(c))]
        if unbacked:
            out("REFUSED: reported as skipped, but the ledger shows no pass at the current tree for: "
                + ", ".join(f"`{c}`" for c in unbacked) + ". Nothing was posted. Run them (`ticket_finish.py suites`).")
            return 1

    # The tree check is refusals' own; the rest of preflight (commits, forbidden files) guards READY too.
    branch_problems = [r for r in preflight(shell, root)[0] if "uncommitted" not in r]
    problems = refusals(
        status, tree_clean=tree_clean, suites=suites, rows=rows, criteria=criteria,
        not_done=report.get("not_done", ""), branch_problems=branch_problems,
        decisions_missing=has_decisions_section(issue) and not decisions_recorded(issue),
    )
    if problems:
        out(f"REFUSED to post STATUS: {status}. Nothing was posted.")
        for p in problems:
            out(f"  - {p}")
        out("Fix these, or post PARTIAL or BLOCKED with what is not done.")
        return 1

    comment = render_comment(
        status=status,
        branch=branch,
        sha=git_out(shell, root, "rev-parse", "--short", "HEAD"),
        worktree=git_out(shell, root, "rev-parse", "--show-toplevel"),
        pushed=is_pushed(shell, root),
        criteria=criteria,
        rows=rows,
        suites=suites,
        review=report.get("review", ""),
        not_done=report.get("not_done", ""),
        owner_actions=report.get("owner_actions", ""),
        followups=report.get("followups", ""),
    )
    if dry_run:
        out(comment)
        return 0

    notes = scratch_path(n, temp)
    body_file = notes.with_name(f"ticket-{n}.comment.md")
    body_file.parent.mkdir(parents=True, exist_ok=True)
    body_file.write_text(comment, encoding="utf-8")
    try:
        posted = shell(["gh", "issue", "comment", str(n), "--body-file", str(body_file)], root)
    finally:
        body_file.unlink(missing_ok=True)
    if not posted.ok:
        out(f"gh issue comment failed: {posted.err.strip()}")
        return 1
    notes.unlink(missing_ok=True)
    out(f"Posted STATUS: {status} on #{n}. The worktree stays in place for the merge.")
    return 0


def _ledger_shows_pass(root: Path) -> Callable[[str], bool]:
    ledger = _ledger()
    git_state = ledger.RealGit(root)
    revision = ledger.current_revision(git_state)
    return lambda command: ledger.suite_verdict(command, revision, git=git_state).skip


def suites_command(root: Path, json_path: Path | None, out: Callable[[str], None] = print) -> int:
    """`suites`: runs what the session-level plan lists and the ledger cannot vouch for, recording passes."""
    from release_steps import default_run_command

    if git_out(real_shell, root, "status", "--porcelain"):
        out("The working tree has uncommitted changes; commit first so a pass can be recorded against the tree.")
        return 1
    ledger = _ledger()
    results = run_suites(
        shell=real_shell, root=root, config=planner.load_config(), markers=planner.load_markers(),
        ledger=ledger, git_state=ledger.RealGit(root), run_command=default_run_command, out=out,
    )
    if json_path is not None:
        json_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        out(f"Wrote the report's `suites` entries to {json_path}.")
    return 1 if any(not r["passed"] for r in results) else 0


def print_criteria(shell: Shell, root: Path, out: Callable[[str], None] = print) -> int:
    n = ticket_from_branch(git_out(shell, root, "branch", "--show-current"))
    issue = gh_issue(shell, root, n, "number,body,comments") if n else None
    if issue is None:
        print("Run this inside a ticket-<N> worktree with gh available.", file=sys.stderr)
        return 1
    for i, c in enumerate(issue_criteria(issue), 1):
        out(f"{i}. {c}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight")
    sub.add_parser("criteria")
    sub.add_parser("suites").add_argument("--json", type=Path, help="write the report's `suites` entries here")
    p = sub.add_parser("post")
    p.add_argument("report", type=Path)
    p.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    root = Path.cwd()
    if args.command == "preflight":
        reasons, info = preflight(real_shell, root)
        print(f"{info['branch']} at {info['sha']}: {info['ahead']} commit(s) ahead of {BASE_BRANCH}")
        for r in reasons:
            print(f"  - {r}")
        return 1 if reasons else 0
    if args.command == "criteria":
        return print_criteria(real_shell, root)
    if args.command == "suites":
        return suites_command(root, args.json)
    return post(args.report, shell=real_shell, root=root, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
