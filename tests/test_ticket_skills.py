"""Structure tests for the /ticket-start, /ticket-finish, /ticket-merge skills (#87).

The skills are committed under `.claude/skills/` (the rest of that directory is
gitignored), are user-invoked only, stay short, and point at scripts and docs
that exist. The behaviour lives in the scripts and is tested in
test_ticket_start/finish/merge.py.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

ROOT = Path(__file__).resolve().parent.parent
SKILLS = {
    "ticket-start": "ticket_start.py",
    "ticket-finish": "ticket_finish.py",
    "ticket-merge": "ticket_merge.py",
}


def _frontmatter(text: str) -> dict[str, str]:
    block = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL).group(1)
    return dict(line.split(": ", 1) for line in block.splitlines())


@pytest.mark.parametrize("name", SKILLS)
def test_skill_is_user_invoked_only_with_a_matching_name(name):
    meta = _frontmatter((ROOT / ".claude" / "skills" / name / "SKILL.md").read_text(encoding="utf-8"))

    assert meta["name"] == name
    assert meta["disable-model-invocation"] == "true"
    assert meta["description"].strip()


@pytest.mark.parametrize("name", SKILLS)
def test_skill_stays_short(name):
    lines = (ROOT / ".claude" / "skills" / name / "SKILL.md").read_text(encoding="utf-8").splitlines()

    assert len(lines) <= 80


@pytest.mark.parametrize("name, script", SKILLS.items())
def test_skill_runs_its_own_script_and_every_path_it_names_exists(name, script):
    text = (ROOT / ".claude" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")

    assert f"scripts/{script}" in text
    for path in set(re.findall(r"`((?:docs|scripts)/[\w./-]+)`", text)):
        assert (ROOT / path).exists(), path


@pytest.mark.parametrize("name", SKILLS)
def test_skill_files_are_not_gitignored(name):
    result = subprocess.run(
        ["git", "check-ignore", "-q", f".claude/skills/{name}/SKILL.md"], cwd=ROOT, capture_output=True
    )

    assert result.returncode == 1  # 1 = not ignored


def test_other_local_skill_payloads_stay_ignored():
    result = subprocess.run(
        ["git", "check-ignore", "-q", ".claude/skills/security-audit/SKILL.md"], cwd=ROOT, capture_output=True
    )

    assert result.returncode == 0


def test_the_skills_never_tell_the_agent_to_push_or_close_without_the_owner():
    for name in SKILLS:
        text = (ROOT / ".claude" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert "git push" not in text


def test_the_finish_skill_and_the_ticket_skills_doc_say_criteria_come_from_the_agent_brief_comment():
    skill = (ROOT / ".claude" / "skills" / "ticket-finish" / "SKILL.md").read_text(encoding="utf-8")
    doc = (ROOT / "docs" / "agents" / "ticket-skills.md").read_text(encoding="utf-8")

    for text in (skill, doc):
        assert "## Agent Brief" in text and "comment" in text
        assert "issue body" in text


def test_ticket_merge_skill_skips_the_merged_tree_run_unless_the_baseline_moved():
    text = (ROOT / ".claude" / "skills" / "ticket-merge" / "SKILL.md").read_text(encoding="utf-8")

    assert "scripts/ticket_merge.py baseline" in text
    assert "--level issue" in text  # the narrowed run on the merged tree when the baseline moved
    assert "BASELINE UNCHANGED" in text


def _skill(name: str) -> str:
    return (ROOT / ".claude" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def test_the_finish_skill_runs_the_session_level_only_through_the_ledger_and_not_the_issue_level_too():
    text = _skill("ticket-finish")

    assert "session level only" in text
    assert "scripts/ticket_finish.py suites" in text
    assert "tree hash" in text
    assert "--level issue" not in text  # the session level contains the issue-level tests
    assert "--level session" not in text  # the script plans it; copying commands by hand skips the ledger
    assert "re-runs only the suites whose files changed" in text


def test_the_finish_skill_asks_before_moving_the_shell_out_of_the_worktree_and_only_after_a_successful_post():
    text = _skill("ticket-finish")
    last = text.split("## 7.")[1]

    assert "AskUserQuestion" in last
    assert "git worktree list --porcelain" in last
    assert "post` succeeded" in last  # never leave the worktree after a failed post
    assert "do not check out, merge, pull or edit" in last


def test_the_merge_skill_drops_the_blanket_rerun_but_keeps_the_diff_read_criterion_trace_and_mutation_check():
    text = _skill("ticket-merge")
    step_two = text.split("## 2.")[1].split("## 3.")[0]

    assert "scripts/ticket_merge.py verdicts" in step_two
    assert "`skip`" in step_two and "`rerun`" in step_two
    assert "--level issue" not in step_two  # the old blanket re-run of the planner's list
    assert "git diff MPSkills...ticket-<N>" in step_two
    assert "Trace every criterion" in step_two
    assert "Spot-check by mutation" in step_two


def test_the_ticket_skills_doc_explains_the_tree_hash_ledger_for_every_step():
    text = (ROOT / "docs" / "agents" / "ticket-skills.md").read_text(encoding="utf-8")

    for needle in ("tree hash", "ticket_finish.py suites", "ticket_merge.py verdicts", "session level only",
                   "single test files and typechecks", "`rerun` for any suite without a recorded pass"):
        assert needle in text, needle


def test_every_script_command_the_skills_and_doc_name_exists_in_its_script():
    for command, script in (("suites", "ticket_finish.py"), ("verdicts", "ticket_merge.py")):
        source = (ROOT / "scripts" / script).read_text(encoding="utf-8")
        assert f'add_parser("{command}")' in source, command


def test_every_place_a_session_reads_tells_it_to_ask_decisions_directly_and_record_them():
    """The owner is asked with AskUserQuestion and the answers go on the ticket as a DECISIONS comment."""
    paths = [
        ROOT / "docs" / "agents" / "session-handoff.md",
        ROOT / "docs" / "agents" / "issue-tracker.md",
        ROOT / "docs" / "agents" / "ticket-skills.md",
        ROOT / ".claude" / "skills" / "ticket-start" / "SKILL.md",
        ROOT / ".claude" / "skills" / "ticket-finish" / "SKILL.md",
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "## Decisions" in text or "Decisions section" in text, path.name
        assert "DECISIONS" in text, path.name
    # The two places that tell the session how to ask name the tool.
    for path in (paths[0], paths[3]):
        assert "AskUserQuestion" in path.read_text(encoding="utf-8"), path.name


def test_the_docs_and_the_skills_that_read_comments_state_who_is_trusted():
    """#167: only the owner, members and collaborators steer the ticket skills; the rule is written where it is read."""
    for rel in (
        "docs/agents/session-handoff.md",
        "docs/agents/ticket-skills.md",
        "docs/agents/issue-tracker.md",
    ):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "authorAssociation" in text or "`OWNER`" in text, rel
        assert "COLLABORATOR" in text, rel
    for name in ("ticket-merge", "ticket-finish"):
        text = (ROOT / ".claude" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert "collaborator" in text, name
