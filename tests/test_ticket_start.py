"""Function and interaction tests for scripts/ticket_start.py (#87).

`/ticket-start <N>` pre-checks a ticket, claims it, and builds its worktree
from `MPSkills`. The decision logic (blockers, assignee, Android emulator) is
tested as pure functions; `start()` is driven with a fake `gh`/`uv` and a real
`git` in a throwaway repository, so the worktree-base proof is a real one.
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
ticket_start = _load("ticket_start")
Result = common.Result


# --- pure decisions ---------------------------------------------------------


def test_blocked_by_section_lists_every_referenced_ticket():
    body = "## What\n\nSee #5.\n\n## Blocked by\n\n- #83\n- #84 (part)\n\n## Notes\n\n- #99\n"

    assert ticket_start.parse_blocked_by(body) == [83, 84]


def test_blocked_by_none_means_no_blockers():
    assert ticket_start.parse_blocked_by("## Blocked by\n\nNone - can start immediately\n") == []
    assert ticket_start.parse_blocked_by("no such section") == []


@pytest.mark.parametrize(
    "title, body, expected",
    [
        ("Android: scan screen crashes on rotate", "x", True),
        ("Fix the scan screen", "Touches `android/app/src/Foo.kt`.", True),
        ("Skills to start a ticket", "for an Android ticket, the emulator is free", False),
        ("Web only", "web/src", False),
    ],
)
def test_android_ticket_is_recognised_by_title_or_android_path(title, body, expected):
    assert ticket_start.is_android_ticket({"title": title, "body": body}) is expected


def test_nothing_in_the_way_gives_no_reasons():
    assert ticket_start.check_start(state="OPEN", assignees=[], open_blockers=[], android=False, android_in_flight=[]) == []


def test_each_obstacle_gives_its_own_clear_reason():
    reasons = ticket_start.check_start(
        state="OPEN", assignees=["gtphdee07"], open_blockers=[83], android=True, android_in_flight=[61]
    )

    text = "\n".join(reasons)
    assert "#83" in text and "blocked" in text.lower()
    assert "gtphdee07" in text and "assigned" in text.lower()
    assert "#61" in text and "emulator" in text.lower()


def test_a_closed_ticket_is_not_started():
    reasons = ticket_start.check_start(state="CLOSED", assignees=[], open_blockers=[], android=False, android_in_flight=[])

    assert any("closed" in r.lower() for r in reasons)


def test_android_emulator_is_only_a_concern_for_android_tickets():
    reasons = ticket_start.check_start(state="OPEN", assignees=[], open_blockers=[], android=False, android_in_flight=[61])

    assert reasons == []


def test_directions_carry_the_handoff_rules_and_the_next_command():
    text = ticket_start.directions(87)

    for needle in (
        "/mattpocock-skills:implement #87",
        "Do not push",
        "do not close",
        "dashboard.svg",
        "external_status.json",
        ".env",
        "docs/agents/session-handoff.md",
        "STATUS:",
    ):
        assert needle.lower() in text.lower(), needle


# --- start(): orchestration -------------------------------------------------


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A repo whose checked-out branch is NOT MPSkills, so a wrong base is visible."""
    root = tmp_path / "main"
    root.mkdir()
    _git(root, "init", "-q", "-b", "MPSkills")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "a.txt").write_text("base\n")
    _git(root, "add", "a.txt")
    _git(root, "commit", "-q", "-m", "base")
    _git(root, "checkout", "-q", "-b", "stale-default")
    (root / "b.txt").write_text("stale\n")
    _git(root, "add", "b.txt")
    _git(root, "commit", "-q", "-m", "stale work")
    return root


class Gh:
    """Scripted gh + uv; git goes through to the real binary."""

    def __init__(self, issue, *, native_blockers=(), states=None, others=()):
        self.issue = issue
        self.native_blockers = list(native_blockers)
        self.states = states or {}
        self.others = list(others)
        self.calls: list[list[str]] = []

    def __call__(self, cmd, cwd=None):
        cmd = list(cmd)
        if cmd[0] == "git":
            return common.real_shell(cmd, cwd)
        self.calls.append(cmd)
        if cmd[:3] == ["gh", "issue", "view"]:
            n = int(cmd[3])
            if n == self.issue["number"]:
                return Result(0, json.dumps(self.issue))
            return Result(0, json.dumps({"number": n, "state": self.states.get(n, "CLOSED")}))
        if cmd[:2] == ["gh", "api"]:
            return Result(0, json.dumps(self.native_blockers))
        if cmd[:3] == ["gh", "issue", "list"]:
            return Result(0, json.dumps(self.others))
        if cmd[:3] == ["gh", "issue", "edit"]:
            return Result(0)
        raise AssertionError(f"unexpected command {cmd}")

    def wrote(self):
        return [c for c in self.calls if c[:3] == ["gh", "issue", "edit"]]


def _issue(**kw):
    base = {"number": 90, "title": "Fix the thing", "state": "OPEN", "assignees": [], "labels": [], "body": "## Blocked by\n\nNone\n"}
    base.update(kw)
    return base


def _start(root, gh, tmp_path, setup=None, **kw):
    lines = []
    setups = []
    code = ticket_start.start(
        90, shell=gh, root=root, temp=tmp_path / "tmp", out=lines.append,
        setup=setup or (lambda wt: setups.append(wt) or 0), **kw,
    )
    return code, "\n".join(lines), setups


def test_open_blocker_stops_with_a_reason_and_changes_nothing(repo, tmp_path):
    gh = Gh(_issue(body="## Blocked by\n\n- #83\n"), states={83: "OPEN"})

    code, out, setups = _start(repo, gh, tmp_path)

    assert code == 1 and "#83" in out
    assert gh.wrote() == [] and setups == []
    assert not (repo / ".claude" / "worktrees" / "ticket-90").exists()
    assert "ticket-90" not in _git(repo, "branch", "--list")
    assert not common.scratch_path(90, tmp_path / "tmp").exists()


def test_native_dependency_blocker_also_stops(repo, tmp_path):
    gh = Gh(_issue(), native_blockers=[{"number": 12, "state": "open"}])

    code, out, _ = _start(repo, gh, tmp_path)

    assert code == 1 and "#12" in out and gh.wrote() == []


def test_assignee_stops_and_changes_nothing(repo, tmp_path):
    gh = Gh(_issue(assignees=[{"login": "someone"}]))

    code, out, setups = _start(repo, gh, tmp_path)

    assert code == 1 and "someone" in out
    assert gh.wrote() == [] and setups == []
    assert "ticket-90" not in _git(repo, "branch", "--list")


def test_busy_android_emulator_stops_an_android_ticket(repo, tmp_path):
    other = {"number": 61, "title": "Android: camera", "body": "", "assignees": [{"login": "x"}]}
    gh = Gh(_issue(title="Android: fix scan"), others=[other])

    code, out, _ = _start(repo, gh, tmp_path)

    assert code == 1 and "#61" in out and "emulator" in out.lower()
    assert gh.wrote() == []


def test_an_unassigned_android_ticket_does_not_occupy_the_emulator(repo, tmp_path):
    other = {"number": 61, "title": "Android: camera", "body": "", "assignees": []}
    gh = Gh(_issue(title="Android: fix scan"), others=[other])

    code, _, _ = _start(repo, gh, tmp_path)

    assert code == 0


def test_start_builds_the_worktree_from_mpskills_not_the_checked_out_branch(repo, tmp_path):
    assert _git(repo, "branch", "--show-current") == "stale-default"
    gh = Gh(_issue())

    code, out, setups = _start(repo, gh, tmp_path)

    assert code == 0
    worktree = repo / ".claude" / "worktrees" / "ticket-90"
    assert worktree.is_dir()
    assert _git(repo, "rev-parse", "ticket-90") == _git(repo, "rev-parse", "MPSkills")
    assert _git(repo, "rev-parse", "ticket-90") != _git(repo, "rev-parse", "stale-default")
    assert not (worktree / "b.txt").exists()
    assert setups == [worktree]


def test_implement_prompt_is_the_command_then_a_blank_line_then_the_handoff_line():
    assert ticket_start.implement_prompt(87) == (
        "/mattpocock-skills:implement #87\n"
        "\n"
        "Follow docs/agents/session-handoff.md: don't push, don't close the issue, "
        "and finish with a STATUS comment on the ticket. "
        "Run a live External suite only if an acceptance criterion names one, and only after the owner approves that run; the merge step covers the rest. "
        "If the ticket has a `## Decisions` section, or needs a decision only the owner can make, ask the owner directly with AskUserQuestion "
        "(up to 4 questions per call) before building on it, then post the questions and answers as a ticket comment starting `DECISIONS`; "
        "if you cannot ask, use the recommended defaults, post them as `DECISIONS (assumed)` and list them under Owner actions."
    )


def test_setup_copies_the_local_only_env_file_into_the_new_worktree():
    # web/.env.local is gitignored, so a worktree never has it; the live External suites need it.
    assert "--copy-env" in ticket_start.SETUP_ARGS


def test_directions_include_the_paste_ready_prompt():
    assert ticket_start.implement_prompt(87) in ticket_start.directions(87)


def test_start_prints_the_whole_paste_ready_prompt_with_the_handoff_line(repo, tmp_path):
    gh = Gh(_issue())

    code, out, _ = _start(repo, gh, tmp_path)

    assert code == 0
    assert ticket_start.implement_prompt(90) in out
    assert "session-handoff.md" in out


def test_start_assigns_the_ticket_prints_the_implement_line_and_writes_directions(repo, tmp_path):
    gh = Gh(_issue())

    code, out, _ = _start(repo, gh, tmp_path)

    assert code == 0
    assert ["gh", "issue", "edit", "90", "--add-assignee", "@me"] in gh.calls
    assert "/mattpocock-skills:implement #90" in out
    notes = common.scratch_path(90, tmp_path / "tmp").read_text(encoding="utf-8")
    assert "/mattpocock-skills:implement #90" in notes


def test_claim_happens_only_after_every_check_passed(repo, tmp_path):
    gh = Gh(_issue())

    _start(repo, gh, tmp_path)

    kinds = [c[:3] for c in gh.calls]
    assert kinds.index(["gh", "issue", "edit"]) > max(i for i, k in enumerate(kinds) if k == ["gh", "issue", "view"])


def test_existing_worktree_or_branch_stops_without_touching_it(repo, tmp_path):
    _git(repo, "branch", "ticket-90", "MPSkills")
    gh = Gh(_issue())

    code, out, setups = _start(repo, gh, tmp_path)

    assert code == 1 and "ticket-90" in out
    assert gh.wrote() == [] and setups == []


def test_a_failing_setup_is_reported_with_the_ticket_already_claimed(repo, tmp_path):
    gh = Gh(_issue())

    code, out, _ = _start(repo, gh, tmp_path, setup=lambda wt: 3)

    assert code == 1 and "worktree_setup" in out
    assert "/mattpocock-skills:implement" not in out


def test_unknown_ticket_is_a_clear_error(repo, tmp_path):
    def gh(cmd, cwd=None):
        return Result(1, "", "not found") if cmd[0] == "gh" else common.real_shell(cmd, cwd)

    lines = []
    code = ticket_start.start(90, shell=gh, root=repo, temp=tmp_path, out=lines.append, setup=lambda wt: 0)

    assert code == 1 and "#90" in "\n".join(lines)


def test_a_failed_worktree_add_rolls_the_claim_back(repo, tmp_path):
    gh = Gh(_issue())

    def shell(cmd, cwd=None):
        if list(cmd)[:3] == ["git", "worktree", "add"]:
            return Result(128, "", "fatal: boom")
        return gh(cmd, cwd)

    lines = []
    code = ticket_start.start(90, shell=shell, root=repo, temp=tmp_path, out=lines.append, setup=lambda wt: 0)

    assert code == 1 and "rolled back" in "\n".join(lines)
    assert ["gh", "issue", "edit", "90", "--add-assignee", "@me"] in gh.calls
    assert ["gh", "issue", "edit", "90", "--remove-assignee", "@me"] in gh.calls
