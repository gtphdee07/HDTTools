"""Function tests for scripts/static_checks.py (#150): each context's static checks as one command.

The runners are fakes, so nothing here starts ruff, vulture, Node or pytest. What these pin is the part that
decides pass or fail: which steps a context runs and in what order, that every step runs even after one fails
and the first failure's code is returned, and how oxlint's warnings are judged against the checked-in
allow-list (an error always fails; a warning fails unless listed; a listed warning that is gone fails).
Whether the real tools exit 0 on the real tree is `tests/test_static_checks_real.py`.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(_SCRIPTS))

_spec = importlib.util.spec_from_file_location("static_checks", _SCRIPTS / "static_checks.py")
sc = importlib.util.module_from_spec(_spec)
sys.modules["static_checks"] = sc
_spec.loader.exec_module(sc)


class FakeRunner:
    """Records each step's command; `codes` maps a command's first distinguishing word to its exit code."""

    def __init__(self, codes=None):
        self.codes = codes or {}
        self.calls: list[list[str]] = []

    def __call__(self, command, cwd=None):
        self.calls.append(list(command))
        text = " ".join(command)
        code = next((c for word, c in self.codes.items() if word in text), 0)
        return SimpleNamespace(returncode=code)


def oxlint_output(*diagnostics):
    return json.dumps({"diagnostics": [
        {"code": rule, "severity": severity, "filename": file, "labels": [{"span": {"line": line}}]}
        for file, rule, severity, line in diagnostics
    ]})


def capture_returning(text, code=0):
    return lambda command, cwd=None: SimpleNamespace(stdout=text, stderr="", returncode=code)


def run(argv, runner=None, capture=None):
    lines: list[str] = []
    code = sc.run(argv, run_command=runner or FakeRunner(), capture=capture or capture_returning(oxlint_output()),
                  out=lines.append)
    return code, lines


# --- which steps each context runs ------------------------------------------


def names(context, **kw):
    return [step.name for step in sc.steps_for(context, **kw)]


def test_core_runs_ruff_then_vulture_on_the_code_then_vulture_on_the_tests():
    assert names("core") == ["ruff", "vulture (dead code)", "vulture (dead code in tests)"]


def test_the_python_coverage_floor_is_added_only_when_asked_for():
    assert names("core", coverage=True)[-1] == "coverage floor"
    assert names("streamlit", coverage=True)[-1] == "coverage floor"
    assert "coverage floor" not in names("core")


def test_web_runs_the_typecheck_then_lint_then_dead_code_and_has_no_coverage_floor():
    assert names("web") == ["typecheck (tsc -b)", "oxlint", "knip (dead code)"]


def test_scan_proxy_runs_typecheck_lint_dead_code_and_the_coverage_floor():
    assert names("scan-proxy") == ["typecheck (tsc --noEmit)", "oxlint", "knip (dead code)", "coverage floor"]


def test_vulture_scans_the_code_and_the_tests_in_separate_passes_so_a_function_only_its_test_calls_still_shows_up():
    code, tests = [s.command for s in sc.steps_for("core") if s.name.startswith("vulture")]
    assert code[3:] == ["src/hdttools", "streamlit_app", "scripts", "vulture_whitelist.py"]
    assert tests[3:] == ["tests", "vulture_whitelist_tests.py"]


def test_ruff_is_pinned_in_the_command_not_in_pyproject_so_the_anthropic_python_surface_stays_fresh():
    ruff = sc.steps_for("core")[0].command
    assert ruff[:3] == ["uv", "tool", "run"] and ruff[3].startswith("ruff@")
    assert "ruff" not in (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_scan_proxy_lint_uses_the_oxlint_installed_for_web_not_a_new_dependency_of_its_own():
    lint = next(s for s in sc.steps_for("scan-proxy") if s.name == "oxlint")
    assert lint.command[0] == sc.OXLINT and sc.OXLINT.endswith("oxlint") and "web" in sc.OXLINT
    assert "oxlint" not in (ROOT / "workers" / "scan-proxy" / "package.json").read_text(encoding="utf-8")


def test_a_context_with_no_static_checks_is_refused():
    with pytest.raises(KeyError):
        sc.steps_for("android")


# --- running a context --------------------------------------------------------


def test_every_step_runs_and_the_pass_is_reported_when_all_exit_0(monkeypatch):
    monkeypatch.setattr(sc, "load_allowlist", lambda context, path=sc.ALLOWLIST: [])
    runner = FakeRunner()

    code, lines = run(["web"], runner)

    assert code == 0 and len(runner.calls) == 2  # tsc and knip; oxlint goes through the capture runner
    assert lines[-1].startswith("Static checks (web) passed:")


def test_a_failing_step_does_not_stop_the_later_steps_and_the_first_failures_code_is_returned():
    runner = FakeRunner({"vulture": 3, "ruff": 7})

    code, lines = run(["core"], runner)

    assert len(runner.calls) == 3, "ruff and both vulture passes all ran"
    assert code == 7
    assert any("ruff FAILED (exit 7)" in line for line in lines)
    assert lines[-1] == "Static checks (core) FAILED: ruff, vulture (dead code), vulture (dead code in tests)"


def test_core_with_coverage_runs_the_floor_through_coverage_gate_for_python_only():
    runner = FakeRunner()

    run(["core", "--coverage"], runner)

    floor = runner.calls[-1]
    assert floor[1].endswith("coverage_gate.py") and floor[2:] == ["--only", "python", "--refresh"]


def test_coverage_is_refused_for_a_context_with_no_python_floor():
    with pytest.raises(SystemExit):
        sc.run(["web", "--coverage"], run_command=FakeRunner(), capture=capture_returning(""), out=lambda _: None)


def test_an_unknown_context_is_refused():
    with pytest.raises(SystemExit):
        sc.run(["android"], run_command=FakeRunner(), capture=capture_returning(""), out=lambda _: None)


# --- oxlint warnings against the allow-list ----------------------------------

WARN = "react(only-export-components)"


def allow(file, rule, count, context="web"):
    return {"context": context, "file": file, "rule": rule, "count": count, "reason": "r"}


def test_a_warning_the_list_allows_passes():
    findings = sc.parse_oxlint(oxlint_output(("src/a.tsx", WARN, "warning", 3)))

    assert sc.judge_lint(findings, [allow("src/a.tsx", WARN, 1)]) == []


def test_a_new_warning_fails():
    findings = sc.parse_oxlint(oxlint_output(("src/b.tsx", WARN, "warning", 3)))

    assert sc.judge_lint(findings, [allow("src/a.tsx", WARN, 1)]) == [
        "new warning src/b.tsx react(only-export-components): 1 found, 0 allowed",
        "stale allow-list entry src/a.tsx react(only-export-components): lists 1, 0 found",
    ]


def test_one_more_warning_than_the_list_allows_fails_even_in_a_listed_file():
    findings = sc.parse_oxlint(oxlint_output(("src/a.tsx", WARN, "warning", 3), ("src/a.tsx", WARN, "warning", 9)))

    assert sc.judge_lint(findings, [allow("src/a.tsx", WARN, 1)]) == [
        "new warning src/a.tsx react(only-export-components): 2 found, 1 allowed"]


def test_an_allow_list_entry_for_a_warning_that_no_longer_occurs_fails():
    assert sc.judge_lint([], [allow("src/gone.tsx", WARN, 2)]) == [
        "stale allow-list entry src/gone.tsx react(only-export-components): lists 2, 0 found"]


def test_an_error_fails_even_when_the_same_rule_is_allowed_as_a_warning():
    findings = sc.parse_oxlint(oxlint_output(("src/a.tsx", "react(rules-of-hooks)", "error", 12)))

    assert sc.judge_lint(findings, [allow("src/a.tsx", "react(rules-of-hooks)", 1)])[0] == "error src/a.tsx:12 react(rules-of-hooks)"


def test_oxlint_paths_with_backslashes_match_the_lists_forward_slashes():
    findings = sc.parse_oxlint(oxlint_output(("src\\components\\RigDelete.tsx", WARN, "warning", 19)))

    assert findings[0]["file"] == "src/components/RigDelete.tsx"


def test_the_lint_step_fails_on_a_new_warning_and_prints_it(monkeypatch):
    monkeypatch.setattr(sc, "load_allowlist", lambda context, path=sc.ALLOWLIST: [])
    capture = capture_returning(oxlint_output(("src/a.tsx", WARN, "warning", 3)))

    code, lines = run(["web"], FakeRunner(), capture)

    assert code == 1
    assert any("new warning src/a.tsx" in line for line in lines)
    assert any("1 finding(s), 0 allowed" in line for line in lines)


def test_the_lint_step_fails_when_oxlint_prints_no_diagnostics_at_all():
    code, lines = run(["web"], FakeRunner(), capture_returning("not json", code=2))

    assert code == 2
    assert any("did not produce JSON diagnostics" in line for line in lines)


# --- the checked-in allow-list ------------------------------------------------


def entries():
    return json.loads((ROOT / "scripts" / "static_allowlists" / "oxlint.json").read_text(encoding="utf-8"))["entries"]


def test_every_allow_list_entry_names_a_context_a_positive_count_and_a_reason():
    for entry in entries():
        assert entry["context"] in ("web", "scan-proxy")
        assert isinstance(entry["count"], int) and entry["count"] >= 1
        assert entry["reason"].strip(), f"{entry['file']} {entry['rule']} has no reason"


def test_the_allow_list_names_each_file_and_rule_once_per_context():
    keys = [(e["context"], e["file"], e["rule"]) for e in entries()]
    assert len(keys) == len(set(keys))


def test_the_allow_list_files_exist():
    roots = {"web": ROOT / "web", "scan-proxy": ROOT / "workers" / "scan-proxy"}
    missing = [e["file"] for e in entries() if not (roots[e["context"]] / e["file"]).is_file()]
    assert not missing, f"allow-list entries for files that no longer exist: {missing}"
