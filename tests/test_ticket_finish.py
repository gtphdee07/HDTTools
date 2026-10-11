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


def test_no_acceptance_section_means_no_criteria():
    assert finish.parse_criteria("## What\n\n- [ ] a\n") == []


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
    def __init__(self, body=BODY):
        self.body = body
        self.comments: list[str] = []
        self.calls: list[list[str]] = []

    def __call__(self, cmd, cwd=None):
        cmd = list(cmd)
        if cmd[0] == "git":
            return common.real_shell(cmd, cwd)
        self.calls.append(cmd)
        if cmd[:3] == ["gh", "issue", "view"]:
            return Result(0, json.dumps({"number": 9, "title": "T", "body": self.body}))
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
