"""Function and interaction tests for scripts/worktree_setup.py (#83).

The script bootstraps a brand-new git worktree: Python environment, Web and
Scan Proxy `node_modules`, and a report of the gitignored local-only files a
worktree does not inherit. The tests drive its pure planning/reporting logic
and `main()` with a fake runner, so no install or network call happens here.
The end-to-end proof (a real fresh worktree, then the offline suites) is run
by hand and recorded on the ticket.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "worktree_setup.py"
_spec = importlib.util.spec_from_file_location("worktree_setup", _SCRIPT_PATH)
worktree_setup = importlib.util.module_from_spec(_spec)
sys.modules["worktree_setup"] = worktree_setup
_spec.loader.exec_module(worktree_setup)

SECRET = "hunter2-do-not-print"


def _make_root(tmp_path: Path, name: str = "wt") -> Path:
    root = tmp_path / name
    (root / "web").mkdir(parents=True)
    (root / "workers" / "scan-proxy").mkdir(parents=True)
    return root


def test_plan_syncs_python_then_installs_both_node_projects_from_their_lockfiles(tmp_path):
    root = _make_root(tmp_path)

    steps = worktree_setup.plan_steps(root)

    assert [(s.cwd, s.command[:2]) for s in steps] == [
        (root, ["uv", "sync"]),
        (root / "web", ["npm", "ci"]),
        (root / "workers" / "scan-proxy", ["npm", "ci"]),
    ]


def test_local_file_status_names_each_missing_file_without_reading_it(tmp_path):
    root = _make_root(tmp_path)

    status = worktree_setup.local_file_status(root)

    assert [(s.path, s.present) for s in status] == [("web/.env.local", False)]


def test_local_file_status_reports_a_present_file_by_name_only(tmp_path):
    root = _make_root(tmp_path)
    (root / "web" / ".env.local").write_text(f"WEB_EXTERNAL_TEST_PASSWORD={SECRET}\n")

    status = worktree_setup.local_file_status(root)

    assert [(s.path, s.present) for s in status] == [("web/.env.local", True)]
    assert SECRET not in repr(status)


def test_copy_local_files_copies_a_missing_file_from_the_source_checkout(tmp_path):
    src, dst = _make_root(tmp_path, "main"), _make_root(tmp_path, "wt")
    (src / "web" / ".env.local").write_text(f"KEY={SECRET}\n")

    copied = worktree_setup.copy_local_files(src, dst)

    assert copied == ["web/.env.local"]
    assert (dst / "web" / ".env.local").read_text() == f"KEY={SECRET}\n"


def test_copy_local_files_never_overwrites_an_existing_file(tmp_path):
    src, dst = _make_root(tmp_path, "main"), _make_root(tmp_path, "wt")
    (src / "web" / ".env.local").write_text("KEY=from-main\n")
    (dst / "web" / ".env.local").write_text("KEY=already-here\n")

    copied = worktree_setup.copy_local_files(src, dst)

    assert copied == []
    assert (dst / "web" / ".env.local").read_text() == "KEY=already-here\n"


def test_copy_local_files_skips_a_file_the_source_does_not_have(tmp_path):
    src, dst = _make_root(tmp_path, "main"), _make_root(tmp_path, "wt")

    assert worktree_setup.copy_local_files(src, dst) == []
    assert not (dst / "web" / ".env.local").exists()


def test_main_checkout_is_the_parent_of_the_shared_git_dir(tmp_path):
    shared = tmp_path / "HDTTools" / ".git"

    assert worktree_setup.main_checkout_from(shared) == tmp_path / "HDTTools"


def test_run_stops_at_the_first_failing_step_and_reports_it(tmp_path, capsys):
    root = _make_root(tmp_path)
    ran = []

    def fake_runner(step):
        ran.append(step.command[:2])
        return 1 if step.command[:2] == ["npm", "ci"] and step.cwd == root / "web" else 0

    code = worktree_setup.run(root, runner=fake_runner, copy_from=None)

    assert code == 1
    assert ran == [["uv", "sync"], ["npm", "ci"]]
    assert "Web dependencies" in capsys.readouterr().err


def test_run_report_lists_missing_local_files_and_which_suites_need_them(tmp_path, capsys):
    root = _make_root(tmp_path)

    code = worktree_setup.run(root, runner=lambda step: 0, copy_from=None)

    out = capsys.readouterr().out
    assert code == 0
    assert "web/.env.local" in out and "MISSING" in out
    assert "External" in out


def test_run_with_copy_from_copies_then_reports_present_without_printing_contents(tmp_path, capsys):
    src, dst = _make_root(tmp_path, "main"), _make_root(tmp_path, "wt")
    (src / "web" / ".env.local").write_text(f"KEY={SECRET}\n")

    code = worktree_setup.run(dst, runner=lambda step: 0, copy_from=src)

    captured = capsys.readouterr()
    assert code == 0
    assert "copied" in captured.out and "web/.env.local" in captured.out
    assert SECRET not in captured.out + captured.err
