"""Function and interaction tests for scripts/ticket_finish.py (#87).

`/ticket-finish` runs in the ticket's worktree after `/implement`. The script
refuses `STATUS: READY TO MERGE` unless the tree is clean, every required suite
passed and every acceptance criterion names a test, then posts the comment in
the template from docs/agents/session-handoff.md. Pure decisions are tested
directly; `post()` and `preflight()` run against a real throwaway git repo with
a fake `gh`.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests._suite_ledger_helpers import LedgerAt as _LedgerAt, Runner, suite_config

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


common = _load("ticket_common")
finish = _load("ticket_finish")
Result = common.Result

BODY = """## What to build

- [ ] not a criterion, this is above the section

## Acceptance criteria

- [ ] First thing works
- [x] Second thing works, with `code` and a | pipe

## Blocked by

- #83
"""


# --- pure decisions ---------------------------------------------------------


def test_acceptance_criteria_are_read_from_their_section_only():
    assert finish.parse_criteria(BODY) == ["First thing works", "Second thing works, with `code` and a | pipe"]


def test_acceptance_criteria_are_read_from_a_bold_label_inside_an_agent_brief():
    body = (
        "## Agent Brief\n\n"
        "**Current behavior:**\n- [ ] not a criterion\n\n"
        "**Acceptance criteria:**\n- [ ] First thing works\n- [x] Second thing works\n\n"
        "**Out of scope:**\n- [ ] not a criterion either\n"
    )
    assert finish.parse_criteria(body) == ["First thing works", "Second thing works"]


def test_no_acceptance_section_means_no_criteria():
    assert finish.parse_criteria("## What\n\n- [ ] a\n") == []


def _brief(*criteria):
    items = "\n".join(f"- [ ] {c}" for c in criteria)
    return f"## Agent Brief\n\n**Category:** enhancement\n\n**Acceptance criteria:**\n{items}\n\n**Out of scope:**\n- nothing\n"


BODY_WITHOUT_CRITERIA = "## What to build\n\nA thing.\n\n## Acceptance\n\n- [ ] not under the matched heading\n"


def test_a_brief_comment_supplies_the_criteria_when_the_body_has_none():
    issue = {"body": BODY_WITHOUT_CRITERIA, "comments": [{"body": "triage notes"}, {"body": _brief("Brief one", "Brief two")}]}

    assert finish.issue_criteria(issue) == ["Brief one", "Brief two"]


def test_the_brief_wins_over_a_body_checklist():
    issue = {"body": BODY, "comments": [{"body": _brief("Brief one")}]}

    assert finish.issue_criteria(issue) == ["Brief one"]


def test_the_most_recent_brief_comment_wins():
    issue = {
        "body": BODY,
        "comments": [{"body": _brief("Old one")}, {"body": "chatter"}, {"body": _brief("New one")}, {"body": "more chatter"}],
    }

    assert finish.issue_criteria(issue) == ["New one"]


def test_a_ticket_with_no_brief_comment_reads_its_body_as_before():
    issue = {"body": BODY, "comments": [{"body": "just a comment with - [ ] a checkbox"}]}

    assert finish.issue_criteria(issue) == finish.parse_criteria(BODY)
    assert finish.issue_criteria({"body": BODY}) == finish.parse_criteria(BODY)


def test_a_brief_with_no_criteria_list_does_not_fall_back_to_the_body():
    # The brief is the authoritative spec; a brief that lists none means the ticket has none to prove.
    issue = {"body": BODY, "comments": [{"body": "## Agent Brief\n\n**Summary:** no list here\n"}]}

    assert finish.issue_criteria(issue) == []


def _rows(*pairs):
    return [{"criterion": c, "proven_by": p} for c, p in pairs]


CRITERIA = ["A works", "B works"]
GOOD_ROWS = _rows(("A works", "tests/test_a.py::test_a"), ("B works", "tests/test_b.py::test_b"))
PASSING = [finish.SuiteResult("uv run pytest", True, "10 passed")]


def test_ready_needs_a_clean_tree_passing_suites_and_a_test_per_criterion():
    assert finish.refusals("READY TO MERGE", tree_clean=True, suites=PASSING, rows=GOOD_ROWS, criteria=CRITERIA) == []


def test_ready_is_refused_when_the_tree_is_dirty():
    reasons = finish.refusals("READY TO MERGE", tree_clean=False, suites=PASSING, rows=GOOD_ROWS, criteria=CRITERIA)

    assert any("dirty" in r.lower() or "uncommitted" in r.lower() for r in reasons)


def test_ready_is_refused_when_any_required_suite_fails():
    suites = PASSING + [finish.SuiteResult("npm --prefix web test", False, "2 failed")]

    reasons = finish.refusals("READY TO MERGE", tree_clean=True, suites=suites, rows=GOOD_ROWS, criteria=CRITERIA)

    assert any("npm --prefix web test" in r for r in reasons)


def test_ready_is_refused_when_no_suite_was_run():
    reasons = finish.refusals("READY TO MERGE", tree_clean=True, suites=[], rows=GOOD_ROWS, criteria=CRITERIA)

    assert reasons


def test_ready_is_refused_when_a_criterion_has_no_test():
    rows = _rows(("A works", "tests/test_a.py::test_a"), ("B works", "  "))

    reasons = finish.refusals("READY TO MERGE", tree_clean=True, suites=PASSING, rows=rows, criteria=CRITERIA)

    assert any("B works" in r for r in reasons)


def test_ready_is_refused_when_a_criterion_is_missing_from_the_table():
    reasons = finish.refusals(
        "READY TO MERGE", tree_clean=True, suites=PASSING, rows=GOOD_ROWS[:1], criteria=CRITERIA
    )

    assert any("B works" in r for r in reasons)


def test_ready_is_refused_when_the_ticket_has_no_criteria_to_prove():
    assert finish.refusals("READY TO MERGE", tree_clean=True, suites=PASSING, rows=[], criteria=[])


def test_partial_and_blocked_are_not_gated_on_the_suites_but_must_say_what_is_not_done():
    for status in ("PARTIAL", "BLOCKED"):
        assert finish.refusals(status, tree_clean=False, suites=[], rows=[], criteria=CRITERIA, not_done="B: no emulator") == []
        assert finish.refusals(status, tree_clean=True, suites=PASSING, rows=GOOD_ROWS, criteria=CRITERIA, not_done=" ")


def test_an_unknown_status_is_refused():
    assert finish.refusals("DONE", tree_clean=True, suites=PASSING, rows=GOOD_ROWS, criteria=CRITERIA)


def test_comment_follows_the_handoff_template():
    text = finish.render_comment(
        status="READY TO MERGE",
        branch="ticket-9",
        sha="abc1234",
        worktree="G:/wt/ticket-9",
        pushed=False,
        criteria=["A works", "B | with pipe"],
        rows=_rows(("A works", "tests/test_a.py::test_a"), ("B | with pipe", "tests/test_b.py::test_b")),
        suites=[finish.SuiteResult("uv run pytest", True, "10 passed"), finish.SuiteResult("npm test", True, "5 passed")],
        review="No findings.",
        not_done="",
        owner_actions="",
        followups="",
    )

    lines = text.splitlines()
    assert lines[0] == "STATUS: READY TO MERGE"
    assert "Branch: `ticket-9` at `abc1234` (worktree: `G:/wt/ticket-9`; pushed: no)" in lines
    assert "| Criterion | Proven by (test file and name) |" in lines
    assert "|---|---|" in lines
    assert "| A works | tests/test_a.py::test_a |" in lines
    assert "| B \\| with pipe | tests/test_b.py::test_b |" in lines
    assert any(l.startswith("Commands run and results:") and "`uv run pytest`" in l and "10 passed" in l for l in lines)
    assert "Code review: No findings." in lines
    assert "Not done, and why: nothing" in lines
    assert "Owner actions needed: none" in lines
    assert "Follow-up tickets filed: none" in lines


def test_comment_marks_an_unproven_criterion_and_a_failed_suite():
    text = finish.render_comment(
        status="PARTIAL", branch="ticket-9", sha="abc", worktree="w", pushed=True,
        criteria=["A works", "B works"], rows=_rows(("A works", "t")),
        suites=[finish.SuiteResult("npm test", False, "2 failed")],
        review="r", not_done="B: blocked", owner_actions="", followups="",
    )

    assert "| B works | NOT PROVEN |" in text
    assert "`npm test`: FAIL" in text
    assert "pushed: yes" in text
    assert "Not done, and why: B: blocked" in text


@pytest.mark.parametrize(
    "path, bad",
    [
        ("dashboard.svg", True),
        ("scripts/dashboard_data/external_status.json", True),
        ("web/.env.local", True),
        (".env", True),
        ("web/.env.production.local", True),
        ("android/.env.production", True),
        # the one tracked env file: public VITE_* values only, committed by design (docs/BUILD_AND_DEPLOY.md)
        ("web/.env.production", False),
        ("web\.env.production", False),
        ("scripts/ticket_start.py", False),
        ("docs/environment.md", False),
    ],
)
def test_files_a_feature_branch_must_not_commit_are_flagged(path, bad):
    assert bool(finish.forbidden_paths([path])) is bad


# --- git + gh interaction ---------------------------------------------------


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def worktree(tmp_path):
    """A repo on branch ticket-9 with one commit ahead of MPSkills and a clean tree."""
    root = tmp_path / "wt"
    root.mkdir()
    _git(root, "init", "-q", "-b", "MPSkills")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "a.txt").write_text("base\n")
    _git(root, "add", "a.txt")
    _git(root, "commit", "-q", "-m", "base")
    _git(root, "checkout", "-q", "-b", "ticket-9")
    (root / "feature.txt").write_text("feature\n")
    _git(root, "add", "feature.txt")
    _git(root, "commit", "-q", "-m", "feature")
    return root


class Gh:
    def __init__(self, body=BODY, comments=None):
        self.body = body
        self.issue_comments = comments or []
        self.comments: list[str] = []
        self.calls: list[list[str]] = []

    def __call__(self, cmd, cwd=None):
        cmd = list(cmd)
        if cmd[0] == "git":
            return common.real_shell(cmd, cwd)
        self.calls.append(cmd)
        if cmd[:3] == ["gh", "issue", "view"]:
            fields = cmd[cmd.index("--json") + 1].split(",")
            issue = {"number": 9, "title": "T", "body": self.body, "comments": [{"body": c} for c in self.issue_comments]}
            return Result(0, json.dumps({k: v for k, v in issue.items() if k in fields}))
        if cmd[:3] == ["gh", "issue", "comment"]:
            self.comments.append(Path(cmd[cmd.index("--body-file") + 1]).read_text(encoding="utf-8"))
            return Result(0)
        raise AssertionError(f"unexpected command {cmd}")


CRIT = ["First thing works", "Second thing works, with `code` and a | pipe"]


def _report(tmp_path, **over):
    report = {
        "status": "READY TO MERGE",
        "criteria": _rows((CRIT[0], "tests/t.py::one"), (CRIT[1], "tests/t.py::two")),
        "suites": [{"command": "uv run pytest", "passed": True, "summary": "3 passed"}],
        "review": "No findings.",
        "not_done": "",
        "owner_actions": "",
        "followups": "",
    }
    report.update(over)
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def _post(worktree, gh, report, tmp_path, **kw):
    lines = []
    code = finish.post(report, shell=gh, root=worktree, temp=tmp_path / "tmp", out=lines.append, **kw)
    return code, "\n".join(lines)


def test_preflight_passes_on_a_clean_tree_with_commits(worktree):
    reasons, info = finish.preflight(common.real_shell, worktree)

    assert reasons == []
    assert info["ahead"] == 1 and info["branch"] == "ticket-9"


def test_preflight_reports_a_dirty_tree(worktree):
    (worktree / "scratch.txt").write_text("x")

    reasons, _ = finish.preflight(common.real_shell, worktree)

    assert any("uncommitted" in r.lower() for r in reasons)


def test_preflight_reports_no_commits(worktree):
    _git(worktree, "reset", "-q", "--hard", "MPSkills")

    reasons, _ = finish.preflight(common.real_shell, worktree)

    assert any("no commits" in r.lower() for r in reasons)


def test_preflight_flags_a_committed_dashboard_svg(worktree):
    (worktree / "dashboard.svg").write_text("<svg/>")
    _git(worktree, "add", "dashboard.svg")
    _git(worktree, "commit", "-q", "-m", "oops")

    reasons, _ = finish.preflight(common.real_shell, worktree)

    assert any("dashboard.svg" in r for r in reasons)


def test_post_ready_posts_the_template_and_deletes_the_scratch_file(worktree, tmp_path):
    gh = Gh()
    notes = common.scratch_path(9, tmp_path / "tmp")
    notes.parent.mkdir(parents=True)
    notes.write_text("live notes")

    code, _ = _post(worktree, gh, _report(tmp_path), tmp_path)

    assert code == 0
    assert len(gh.comments) == 1
    comment = gh.comments[0]
    assert comment.startswith("STATUS: READY TO MERGE")
    assert f"at `{_git(worktree, 'rev-parse', '--short', 'HEAD')}`" in comment
    assert "pushed: no" in comment
    assert not notes.exists()


def test_post_ready_is_refused_on_a_dirty_tree_and_posts_nothing(worktree, tmp_path):
    (worktree / "feature.txt").write_text("edited after the commit\n")
    gh = Gh()
    notes = common.scratch_path(9, tmp_path / "tmp")
    notes.parent.mkdir(parents=True)
    notes.write_text("live notes")

    code, out = _post(worktree, gh, _report(tmp_path), tmp_path)

    assert code == 1 and "READY TO MERGE" in out
    assert gh.comments == []
    assert notes.exists()


def test_post_ready_is_refused_when_a_required_suite_failed(worktree, tmp_path):
    report = _report(tmp_path, suites=[{"command": "npm --prefix web test", "passed": False, "summary": "1 failed"}])
    gh = Gh()

    code, out = _post(worktree, gh, report, tmp_path)

    assert code == 1 and "npm --prefix web test" in out
    assert gh.comments == []


def test_post_ready_is_refused_when_a_criterion_has_no_test(worktree, tmp_path):
    report = _report(tmp_path, criteria=_rows((CRIT[0], "tests/t.py::one")))
    gh = Gh()

    code, out = _post(worktree, gh, report, tmp_path)

    assert code == 1 and "Second thing works" in out
    assert gh.comments == []


def test_post_partial_is_allowed_on_a_dirty_tree_and_says_so(worktree, tmp_path):
    (worktree / "wip.txt").write_text("x")
    report = _report(tmp_path, status="PARTIAL", not_done="Second: needs the emulator", criteria=_rows((CRIT[0], "t")))
    gh = Gh()

    code, _ = _post(worktree, gh, report, tmp_path)

    assert code == 0
    assert gh.comments[0].startswith("STATUS: PARTIAL")
    assert "| Second thing works, with `code` and a \\| pipe | NOT PROVEN |" in gh.comments[0]


def test_dry_run_prints_the_comment_and_changes_nothing(worktree, tmp_path):
    gh = Gh()
    notes = common.scratch_path(9, tmp_path / "tmp")
    notes.parent.mkdir(parents=True)
    notes.write_text("live notes")

    code, out = _post(worktree, gh, _report(tmp_path), tmp_path, dry_run=True)

    assert code == 0 and "STATUS: READY TO MERGE" in out
    assert gh.comments == [] and notes.exists()


def test_post_outside_a_ticket_branch_is_an_error(worktree, tmp_path):
    _git(worktree, "checkout", "-q", "-b", "scratch")

    code, out = _post(worktree, Gh(), _report(tmp_path), tmp_path)

    assert code == 1 and "ticket-" in out


def test_post_ready_requires_a_test_for_each_criterion_of_the_latest_brief_comment(worktree, tmp_path):
    gh = Gh(body=BODY_WITHOUT_CRITERIA, comments=[_brief("Old"), _brief("Brief one", "Brief two")])
    report = _report(tmp_path, criteria=_rows(("Brief one", "tests/t.py::one")))

    code, out = _post(worktree, gh, report, tmp_path)

    assert code == 1 and gh.comments == []
    assert "No test named for criterion: Brief two" in out
    assert "Old" not in out


def test_post_ready_with_a_brief_comment_lists_its_criteria_in_the_table(worktree, tmp_path):
    gh = Gh(body=BODY_WITHOUT_CRITERIA, comments=[_brief("Brief one", "Brief two")])
    report = _report(tmp_path, criteria=_rows(("Brief one", "tests/t.py::one"), ("Brief two", "tests/t.py::two")))

    code, _ = _post(worktree, gh, report, tmp_path)

    assert code == 0
    assert "| Brief one | tests/t.py::one |" in gh.comments[0]
    assert "| Brief two | tests/t.py::two |" in gh.comments[0]


def test_criteria_prints_the_latest_brief_comments_criteria(worktree):
    gh = Gh(body=BODY_WITHOUT_CRITERIA, comments=[_brief("Old"), _brief("Brief one", "Brief two")])
    lines = []

    code = finish.print_criteria(gh, worktree, out=lines.append)

    assert code == 0 and lines == ["1. Brief one", "2. Brief two"]


def test_criteria_for_a_body_only_ticket_prints_the_body_criteria(worktree):
    lines = []

    code = finish.print_criteria(Gh(), worktree, out=lines.append)

    assert code == 0 and lines == [f"1. {CRIT[0]}", f"2. {CRIT[1]}"]


# --- owner decisions (asked once, recorded on the ticket) ---------------------------------------------

DECISIONS_SECTION = "\n## Decisions\n\n1. Which wording? Options: A (recommended) or B.\n"
BODY_WITH_DECISIONS = BODY + DECISIONS_SECTION
ANSWERS = "DECISIONS (owner, 2026-10-15)\n\n1. Which wording? Answer: A (the recommended default).\n"


def test_a_decisions_heading_in_the_body_is_found():
    assert finish.has_decisions_section({"body": BODY_WITH_DECISIONS, "comments": []}) is True


def test_a_ticket_without_a_decisions_heading_has_none():
    assert finish.has_decisions_section({"body": BODY, "comments": []}) is False


def test_a_decisions_so_far_heading_is_not_a_decisions_section():
    # The wayfinder maps keep a "Decisions so far" index; that is not a list of questions to ask.
    assert finish.has_decisions_section({"body": "## Decisions so far\n\n- one\n", "comments": []}) is False


def test_a_decisions_heading_in_the_latest_brief_comment_is_found():
    brief = _brief("X works") + DECISIONS_SECTION
    assert finish.has_decisions_section({"body": BODY_WITHOUT_CRITERIA, "comments": [{"body": brief}]}) is True


def test_a_decisions_heading_in_a_plain_comment_is_not_a_decisions_section():
    assert finish.has_decisions_section({"body": BODY, "comments": [{"body": DECISIONS_SECTION}]}) is False


def test_decisions_are_recorded_by_a_comment_that_starts_with_decisions():
    assert finish.decisions_recorded({"comments": [{"body": "STATUS: PARTIAL"}, {"body": ANSWERS}]}) is True


def test_a_byte_order_mark_or_leading_blank_lines_do_not_hide_a_decisions_comment():
    assert finish.decisions_recorded({"comments": [{"body": "﻿\n  " + ANSWERS}]}) is True


def test_a_comment_that_only_mentions_decisions_is_not_a_record():
    mention = {"body": "The DECISIONS are still open."}
    assert finish.decisions_recorded({"comments": [mention, {"body": "Decisions: later"}]}) is False
    assert finish.decisions_recorded({"comments": []}) is False


def test_ready_is_refused_while_decisions_are_unrecorded_but_partial_and_blocked_are_not():
    kw = dict(tree_clean=True, suites=PASSING, rows=GOOD_ROWS, criteria=CRITERIA, decisions_missing=True)

    reasons = finish.refusals("READY TO MERGE", **kw)
    assert any("DECISIONS comment" in r and "AskUserQuestion" in r for r in reasons)
    assert finish.refusals("PARTIAL", not_done="Waiting on the owner.", **kw) == []
    assert finish.refusals("BLOCKED", not_done="Waiting on the owner.", **kw) == []


def test_post_ready_is_refused_when_the_ticket_lists_decisions_and_none_were_recorded(worktree, tmp_path):
    gh = Gh(body=BODY_WITH_DECISIONS)

    code, out = _post(worktree, gh, _report(tmp_path), tmp_path)

    assert code == 1 and gh.comments == []
    assert "DECISIONS comment" in out


def test_post_ready_goes_through_once_the_decisions_comment_exists(worktree, tmp_path):
    gh = Gh(body=BODY_WITH_DECISIONS, comments=[ANSWERS])

    code, _ = _post(worktree, gh, _report(tmp_path), tmp_path)

    assert code == 0 and gh.comments[0].startswith("STATUS: READY TO MERGE")


def test_post_partial_is_allowed_with_decisions_unrecorded(worktree, tmp_path):
    gh = Gh(body=BODY_WITH_DECISIONS)
    report = _report(tmp_path, status="PARTIAL", not_done="Decisions not asked: the session could not reach the owner.")

    code, _ = _post(worktree, gh, report, tmp_path)

    assert code == 0 and gh.comments[0].startswith("STATUS: PARTIAL")


def test_pushed_is_yes_only_when_the_remote_branch_holds_head(worktree, tmp_path):
    assert finish.is_pushed(common.real_shell, worktree) is False
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "-q", "--bare", str(remote))
    _git(worktree, "remote", "add", "origin", str(remote))
    _git(worktree, "push", "-q", "origin", "ticket-9")
    assert finish.is_pushed(common.real_shell, worktree) is True
    (worktree / "more.txt").write_text("m")
    _git(worktree, "add", "more.txt")
    _git(worktree, "commit", "-q", "-m", "more")
    assert finish.is_pushed(common.real_shell, worktree) is False


def test_post_ready_is_refused_when_the_branch_has_no_commits(worktree, tmp_path):
    _git(worktree, "reset", "-q", "--hard", "MPSkills")
    gh = Gh()

    code, out = _post(worktree, gh, _report(tmp_path), tmp_path)

    assert code == 1 and "no commits" in out.lower()
    assert gh.comments == []


def test_post_ready_is_refused_when_a_forbidden_file_is_committed(worktree, tmp_path):
    (worktree / "dashboard.svg").write_text("<svg/>")
    _git(worktree, "add", "dashboard.svg")
    _git(worktree, "commit", "-q", "-m", "oops")
    gh = Gh()

    code, out = _post(worktree, gh, _report(tmp_path), tmp_path)

    assert code == 1 and "dashboard.svg" in out
    assert gh.comments == []


def test_a_suite_result_written_as_text_is_refused_not_read_as_true(worktree, tmp_path):
    report = _report(tmp_path, suites=[{"command": "uv run pytest", "passed": "false", "summary": "3 failed"}])
    gh = Gh()

    code, out = _post(worktree, gh, report, tmp_path)

    assert code == 1 and "uv run pytest" in out and "true or false" in out
    assert gh.comments == []


# --- Each suite runs once per tree (#128): `suites` and the skipped-suite check in `post` ---

vl = _load("verification_ledger")
planner = _load("test_planner")

SUITE_CONFIG = suite_config()
ALL_SUITES = ["core-suite", "web-suite", "proxy-suite"]


def LedgerAt(path):  # noqa: N802 - reads like the class it builds
    return _LedgerAt(vl, path)


@pytest.fixture
def suite_repo(worktree):
    """The ticket branch now also changes a web, a scan-proxy and a Python file: three contexts, three suites."""
    for rel in ("web/src/a.ts", "workers/scan-proxy/src/b.ts", "src/hdttools/c.py"):
        (worktree / rel).parent.mkdir(parents=True, exist_ok=True)
        (worktree / rel).write_text("one\n")
    _git(worktree, "add", ".")
    _git(worktree, "commit", "-q", "-m", "three contexts")
    return worktree


def _suites(repo, tmp_path, runner, ledger=None):
    lines: list[str] = []
    ledger = ledger or LedgerAt(tmp_path / "ledger.json")
    results = finish.run_suites(shell=common.real_shell, root=repo, config=SUITE_CONFIG, markers={"core", "minor"},
                                ledger=ledger, git_state=vl.RealGit(repo), run_command=runner, out=lines.append)
    return {r["command"]: r for r in results}, lines


def _commit(repo, rel, text="two\n", message="review fix"):
    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
    (repo / rel).write_text(text)
    _git(repo, "add", rel)
    _git(repo, "commit", "-q", "-m", message)


def test_the_first_run_runs_every_suite_and_records_each_pass_against_the_tree(suite_repo, tmp_path):
    runner = Runner()

    results, _ = _suites(suite_repo, tmp_path, runner)

    assert sorted(runner.calls) == sorted(ALL_SUITES)
    assert all(r["passed"] and not r["skipped"] for r in results.values())
    ledger = LedgerAt(tmp_path / "ledger.json")
    revision = vl.current_revision(vl.RealGit(suite_repo))
    assert all(ledger.suite_verdict(c, revision).skip for c in ALL_SUITES)


def test_a_second_run_on_the_same_tree_runs_nothing_and_lists_every_suite_as_skipped(suite_repo, tmp_path):
    _suites(suite_repo, tmp_path, Runner())
    runner = Runner()

    results, lines = _suites(suite_repo, tmp_path, runner)

    assert runner.calls == []
    assert all(r["skipped"] and r["passed"] for r in results.values())
    assert any(line.startswith("skip: core-suite") for line in lines)


def test_an_amend_that_changes_no_content_still_skips_every_suite(suite_repo, tmp_path):
    _suites(suite_repo, tmp_path, Runner())
    _git(suite_repo, "commit", "-q", "--amend", "-m", "reworded")
    runner = Runner()

    results, _ = _suites(suite_repo, tmp_path, runner)

    assert runner.calls == []
    assert all(r["skipped"] for r in results.values())


def test_a_failing_suite_is_reported_not_recorded_and_runs_again_while_the_others_stay_skipped(suite_repo, tmp_path):
    results, _ = _suites(suite_repo, tmp_path, Runner(failing={"web-suite"}))
    assert results["web-suite"]["passed"] is False and results["web-suite"]["summary"] == "exit 1"

    runner = Runner()
    results, _ = _suites(suite_repo, tmp_path, runner)

    assert runner.calls == ["web-suite"]
    assert results["core-suite"]["skipped"] and results["proxy-suite"]["skipped"]
    assert results["web-suite"]["passed"] and not results["web-suite"]["skipped"]


def test_after_a_review_fix_only_the_suites_whose_files_changed_run_again(suite_repo, tmp_path):
    _suites(suite_repo, tmp_path, Runner())
    _commit(suite_repo, "web/src/a.ts")
    runner = Runner()

    results, lines = _suites(suite_repo, tmp_path, runner)

    # The Python suite reruns too (its tests read web sources); the scan-proxy suite cannot depend on web/.
    assert sorted(runner.calls) == ["core-suite", "web-suite"]
    assert results["proxy-suite"]["skipped"]
    assert any(line.startswith("run: web-suite") and "changed since" in line for line in lines)


def test_a_file_moved_from_one_context_to_another_reruns_both_contexts_suites(suite_repo, tmp_path):
    _suites(suite_repo, tmp_path, Runner())
    _git(suite_repo, "mv", "web/src/a.ts", "workers/scan-proxy/src/moved.ts")
    _git(suite_repo, "commit", "-q", "-m", "move it")
    runner = Runner()

    _suites(suite_repo, tmp_path, runner)

    assert {"web-suite", "proxy-suite"} <= set(runner.calls)


def test_a_docs_only_review_fix_reruns_the_python_suite_and_leaves_the_others_alone(suite_repo, tmp_path):
    _suites(suite_repo, tmp_path, Runner())
    _commit(suite_repo, "docs/note.md")
    runner = Runner()

    _suites(suite_repo, tmp_path, runner)

    assert runner.calls == ["core-suite"]


def test_a_changed_file_nobody_owns_reruns_every_suite(suite_repo, tmp_path):
    _suites(suite_repo, tmp_path, Runner())
    _commit(suite_repo, "Makefile")
    runner = Runner()

    _suites(suite_repo, tmp_path, runner)

    assert sorted(runner.calls) == sorted(ALL_SUITES)


def test_a_carried_pass_is_found_again_at_the_new_tree_so_the_next_step_can_skip_it(suite_repo, tmp_path):
    _suites(suite_repo, tmp_path, Runner())
    _commit(suite_repo, "web/src/a.ts")
    _suites(suite_repo, tmp_path, Runner())
    runner = Runner()

    results, _ = _suites(suite_repo, tmp_path, runner)

    assert runner.calls == [] and all(r["skipped"] for r in results.values())


def test_a_review_fix_after_a_carried_pass_is_judged_against_the_newest_pass(suite_repo, tmp_path):
    _suites(suite_repo, tmp_path, Runner())
    _commit(suite_repo, "docs/note.md", message="docs fix")
    _suites(suite_repo, tmp_path, Runner())
    _commit(suite_repo, "web/src/a.ts", message="web fix")
    runner = Runner()

    _suites(suite_repo, tmp_path, runner)

    assert sorted(runner.calls) == ["core-suite", "web-suite"]  # proxy carried across both fixes


def test_an_unreadable_ledger_runs_every_suite_and_says_it_was_not_recorded(suite_repo, tmp_path):
    (tmp_path / "ledger.json").write_text("{not json", encoding="utf-8")
    runner = Runner()

    results, lines = _suites(suite_repo, tmp_path, runner)

    assert sorted(runner.calls) == sorted(ALL_SUITES)
    assert all(r["passed"] and "NOT recorded" in r["summary"] for r in results.values())
    assert (tmp_path / "ledger.json").read_text(encoding="utf-8") == "{not json"
    assert any("without recording" in line for line in lines)


def test_a_pass_at_a_tree_git_does_not_know_cannot_be_compared_so_the_suite_runs(suite_repo, tmp_path):
    ledger = LedgerAt(tmp_path / "ledger.json")
    vl.record_suite("web-suite", "pass", revision=vl.Revision("a" * 40, "b" * 40), path=ledger.path)
    runner = Runner()

    _suites(suite_repo, tmp_path, runner, ledger=ledger)

    assert "web-suite" in runner.calls


def test_device_and_surface_suites_are_listed_never_run_here(suite_repo, tmp_path):
    config = {**SUITE_CONFIG, "contexts": {**SUITE_CONFIG["contexts"], "web": {
        **SUITE_CONFIG["contexts"]["web"], "device": "web-device", "device_covered": ["web/src/*"]}}}
    runner = Runner()
    lines: list[str] = []

    finish.run_suites(shell=common.real_shell, root=suite_repo, config=config, markers={"core", "minor"},
                      ledger=LedgerAt(tmp_path / "ledger.json"), git_state=vl.RealGit(suite_repo),
                      run_command=runner, out=lines.append)

    assert "web-device" not in runner.calls
    assert any(line.startswith("not run here: web-device") for line in lines)


def test_post_ready_lists_a_skipped_suite_when_the_ledger_shows_its_pass(worktree, tmp_path):
    suites = [{"command": "uv run pytest", "passed": True, "skipped": True, "summary": "already passed"}]
    gh = Gh()

    code, _ = _post(worktree, gh, _report(tmp_path, suites=suites), tmp_path, ledger_shows_pass=lambda c: True)

    assert code == 0
    assert "`uv run pytest`: SKIPPED (already passed at this tree)" in gh.comments[0]


def test_post_refuses_a_skipped_suite_the_ledger_does_not_show_as_passed(worktree, tmp_path):
    suites = [{"command": "uv run pytest", "passed": True, "skipped": True, "summary": "already passed"}]
    gh = Gh()

    code, out = _post(worktree, gh, _report(tmp_path, suites=suites), tmp_path, ledger_shows_pass=lambda c: False)

    assert code == 1 and "`uv run pytest`" in out and "no pass at the current tree" in out
    assert gh.comments == []


def test_post_refuses_a_skipped_suite_even_for_partial_and_on_a_dirty_tree(worktree, tmp_path):
    suites = [{"command": "uv run pytest", "passed": True, "skipped": True}]
    (worktree / "feature.txt").write_text("edited after the commit\n")

    code, out = _post(worktree, Gh(), _report(tmp_path, suites=suites, status="PARTIAL", not_done="x"), tmp_path,
                      ledger_shows_pass=lambda c: True)

    assert code == 1 and "no pass at the current tree" in out


def test_post_asks_the_real_ledger_when_no_check_is_injected(worktree, tmp_path, monkeypatch):
    monkeypatch.setattr(finish, "_ledger_shows_pass", lambda root: (lambda command: command == "uv run pytest"))
    suites = [{"command": "uv run pytest", "passed": True, "skipped": True},
              {"command": "npm test", "passed": True, "skipped": True}]

    code, out = _post(worktree, Gh(), _report(tmp_path, suites=suites), tmp_path)

    assert code == 1 and "`npm test`" in out and "`uv run pytest`" not in out
