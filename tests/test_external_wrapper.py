"""Function tests for scripts/external_wrapper.py: the decision logic behind
the platform wrappers, with the test runner and recorder faked."""

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
_spec = importlib.util.spec_from_file_location("external_wrapper", _SCRIPTS / "external_wrapper.py")
ew = importlib.util.module_from_spec(_spec)
sys.modules["external_wrapper"] = ew
_spec.loader.exec_module(ew)

V = ew.external_freshness.Verdict


class Harness:
    def __init__(self, tagged=("a", "b"), exit_code=0):
        self.tagged = set(tagged)
        self.exit_code = exit_code
        self.ran = []
        self.recorded = []
        self.lines = []

    def go(self, verdicts, skip=False):
        return ew.execute_plan(
            verdicts,
            skip=skip,
            has_tests=lambda s: s in self.tagged,
            run_tests=lambda surfaces: (self.ran.append(list(surfaces)) or self.exit_code),
            record=lambda s, o, v: self.recorded.append((s, o, v)),
            out=self.lines.append,
        )


def stale(name, versions=None):
    return V(name, "stale", ["never passed"], versions or {"p": "1.0.0"})


def test_fresh_surfaces_run_no_tests_and_record_nothing():
    h = Harness()
    assert h.go([V("a", "fresh")]) == 0
    assert h.ran == [] and h.recorded == []
    assert any("nothing to run" in line for line in h.lines)


def test_planned_surfaces_never_run():
    h = Harness()
    assert h.go([V("a", "planned")]) == 0
    assert h.ran == [] and h.recorded == []


def test_only_the_stale_surfaces_run():
    h = Harness()
    h.go([V("a", "fresh"), stale("b")])
    assert h.ran == [["b"]]


def test_a_passing_run_records_pass_with_versions():
    h = Harness(exit_code=0)
    assert h.go([stale("a")]) == 0
    assert h.recorded == [("a", "pass", {"p": "1.0.0"})]


def test_a_failing_run_records_fail_and_returns_its_exit_code():
    h = Harness(exit_code=3)
    assert h.go([stale("a"), stale("b")]) == 3
    assert [(s, o) for s, o, _ in h.recorded] == [("a", "fail"), ("b", "fail")]


def test_skip_records_skipped_without_running():
    h = Harness()
    assert h.go([stale("a"), V("b", "fresh")], skip=True) == 0
    assert h.ran == []
    assert [(s, o) for s, o, _ in h.recorded] == [("a", "skipped")]


def test_untagged_surface_is_recorded_as_fail_and_not_run():
    h = Harness(tagged=())
    assert h.go([stale("a")]) == 1
    assert h.ran == []
    assert [(s, o) for s, o, _ in h.recorded] == [("a", "fail")]


def test_mixed_tagged_and_untagged_runs_the_tagged_and_still_fails_overall():
    h = Harness(tagged=("a",), exit_code=0)
    assert h.go([stale("a"), stale("zzz")]) == 1
    assert h.ran == [["a"]]
    assert sorted((s, o) for s, o, _ in h.recorded) == [("a", "pass"), ("zzz", "fail")]


def test_each_surface_verdict_is_reported():
    h = Harness()
    h.go([V("a", "fresh"), stale("b")])
    assert "a - fresh" in h.lines
    assert "b - stale: never passed" in h.lines


def test_tagged_in_finds_bracketed_tags_in_external_test_files(tmp_path):
    (tmp_path / "x.external.test.ts").write_text("describe('[a] thing', () => {})")
    (tmp_path / "ignored.test.ts").write_text("describe('[b] thing', () => {})")
    has = ew.tagged_in(tmp_path)
    assert has("a") is True
    assert has("b") is False


def test_tagged_in_supports_a_custom_glob_and_pytest_marker_tag_style(tmp_path):
    (tmp_path / "test_anthropic_external.py").write_text(
        "pytestmark = [pytest.mark.external, pytest.mark.anthropic]"
    )
    (tmp_path / "test_other.py").write_text("pytestmark = [pytest.mark.external, pytest.mark.supabase]")
    has = ew.tagged_in(tmp_path, "test_*_external.py", ew.TAG_FORMATS["marker"])
    assert has("anthropic") is True
    assert has("supabase") is False


class BudgetHarness(Harness):
    def __init__(self, *, confirm, paid_calls, max_calls, tagged=("a",), exit_code=0):
        super().__init__(tagged=tagged, exit_code=exit_code)
        self.paid_calls = paid_calls
        self.budget = ew.PaidCallBudget(max_calls=max_calls, confirm=confirm, out=self.lines.append)

    def go(self, verdicts, skip=False):
        return ew.execute_plan(
            verdicts,
            skip=skip,
            has_tests=lambda s: s in self.tagged,
            run_tests=lambda surfaces: (self.ran.append(list(surfaces)) or self.exit_code),
            record=lambda s, o, v: self.recorded.append((s, o, v)),
            out=self.lines.append,
            paid_calls=self.paid_calls,
            budget=self.budget,
        )


def test_a_confirmed_paid_surface_runs_and_records_pass():
    h = BudgetHarness(confirm=lambda d, c: True, paid_calls={"a": 3}, max_calls=3)
    assert h.go([stale("a")]) == 0
    assert h.ran == [["a"]]
    assert h.recorded == [("a", "pass", {"p": "1.0.0"})]


def test_a_declined_paid_surface_is_recorded_skipped_and_not_run():
    h = BudgetHarness(confirm=lambda d, c: False, paid_calls={"a": 3}, max_calls=3)
    assert h.go([stale("a")]) == 1
    assert h.ran == []
    assert [(s, o) for s, o, _ in h.recorded] == [("a", "skipped")]


def test_a_paid_surface_exceeding_the_budget_aborts_without_prompting():
    confirmed = []
    h = BudgetHarness(confirm=lambda d, c: confirmed.append((d, c)) or True, paid_calls={"a": 4}, max_calls=3)
    assert h.go([stale("a")]) == 1
    assert confirmed == []
    assert h.ran == []
    assert h.recorded == []
    assert any("Aborting" in line for line in h.lines)


def test_a_free_surface_alongside_a_confirmed_paid_one_both_run_together():
    h = BudgetHarness(confirm=lambda d, c: True, paid_calls={"a": 3}, max_calls=3, tagged=("a", "b"))
    assert h.go([stale("a"), stale("b")]) == 0
    assert h.ran == [["a", "b"]]


def test_paid_calls_for_reads_each_in_scope_surfaces_declared_cost():
    manifest = {"surfaces": {"a": {"max_paid_calls": 3}, "b": {}, "c": {"max_paid_calls": 0}}}
    assert ew.paid_calls_for(manifest, ["a", "b"]) == {"a": 3, "b": 0}


def test_budget_for_is_none_when_nothing_in_scope_is_paid():
    assert ew.budget_for({"a": 0, "b": 0}) is None


def test_budget_for_defaults_the_ceiling_to_the_sum_of_declared_costs():
    budget = ew.budget_for({"a": 3, "b": 2})
    assert budget.max_calls == 5


def test_budget_for_accepts_an_independent_ceiling_override():
    budget = ew.budget_for({"a": 3}, max_calls=1)
    assert budget.max_calls == 1
