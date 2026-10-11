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
