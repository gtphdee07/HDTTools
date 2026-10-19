"""Function tests for scripts/external_wrapper.py: the decision logic behind
the platform wrappers, with the test runner and recorder faked."""

import importlib.util
import json
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

    def go(self, verdicts, skip=False, owned_elsewhere=None):
        return ew.execute_plan(
            verdicts,
            skip=skip,
            has_tests=lambda s: s in self.tagged,
            run_tests=lambda surfaces: (self.ran.append(list(surfaces)) or self.exit_code),
            record=lambda s, o, v: self.recorded.append((s, o, v)),
            out=self.lines.append,
            owned_elsewhere=owned_elsewhere,
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


def test_untagged_surface_the_wrapper_owns_says_no_external_tests_tagged():
    h = Harness(tagged=())
    h.go([stale("a")], owned_elsewhere={})
    assert "No external tests tagged [a]; recording fail." in h.lines


# --- surfaces another platform's wrapper owns (#142) ---------------------------------------------


def test_a_stale_surface_owned_elsewhere_is_neither_run_nor_recorded_and_the_owning_script_is_named():
    h = Harness(tagged=())  # the Web wrapper has no tests tagged for the Worker's surfaces
    assert h.go([stale("w")], owned_elsewhere={"w": "scan-proxy"}) == 0
    assert h.ran == [] and h.recorded == []
    assert any("w" in line and r"workers\scan-proxy\test-external.ps1" in line for line in h.lines)


def test_surfaces_owned_elsewhere_do_not_stop_the_wrapper_running_and_recording_its_own():
    h = Harness(tagged=("a",))
    assert h.go([stale("a"), stale("w")], owned_elsewhere={"w": "scan-proxy"}) == 0
    assert h.ran == [["a"]]
    assert [(s, o) for s, o, _ in h.recorded] == [("a", "pass")]


def test_an_own_untagged_surface_still_fails_next_to_one_owned_elsewhere():
    h = Harness(tagged=())
    assert h.go([stale("a"), stale("w")], owned_elsewhere={"w": "scan-proxy"}) == 1
    assert [(s, o) for s, o, _ in h.recorded] == [("a", "fail")]


def test_skip_records_skipped_only_for_the_surfaces_the_wrapper_owns():
    h = Harness()
    assert h.go([stale("a"), stale("w")], skip=True, owned_elsewhere={"w": "scan-proxy"}) == 0
    assert [(s, o) for s, o, _ in h.recorded] == [("a", "skipped")]


def test_a_fresh_surface_owned_elsewhere_adds_no_note():
    h = Harness()
    h.go([V("w", "fresh"), stale("a")], owned_elsewhere={"w": "scan-proxy"})
    assert not any("owned by" in line for line in h.lines)


def test_the_note_names_a_fallback_for_an_owner_without_a_known_script():
    h = Harness()
    h.go([stale("w")], owned_elsewhere={"w": "android"})
    assert any("android" in line and "not run or recorded here" in line for line in h.lines)


MANIFEST = {
    "surfaces": {
        "site": {"name": "site", "platforms": ["web"], "owner": "web"},
        "auth": {"name": "auth", "platforms": ["web", "android"], "owner": "web"},
        "worker": {"name": "worker", "platforms": ["scan-proxy", "web", "android"], "owner": "scan-proxy"},
    }
}


def test_foreign_owners_lists_chain_surfaces_another_platform_owns():
    assert ew.foreign_owners(MANIFEST, "web") == {"worker": "scan-proxy"}
    assert ew.foreign_owners(MANIFEST, "scan-proxy") == {}


class Run:
    """One wrapper invocation against a fake manifest, status and runner."""

    def __init__(self, platform, manifest=MANIFEST, tagged=(), status=None):
        self.ran, self.recorded, self.lines = [], [], []
        self.code = ew.main(
            ["--platform", platform, "--tests-dir", "unused", "--cwd", "unused", "--", "cmd"],
            manifest=manifest,
            status=status or {},
            git=ew.external_freshness.GitHistory(),
            registry=lambda ecosystem, package: {},
            has_tests=lambda s: s in tagged,
            run_tests=lambda surfaces: self.ran.append(list(surfaces)) or 0,
            record=lambda s, o, v: self.recorded.append((s, o)),
            out=self.lines.append,
        )


def test_the_web_wrapper_records_nothing_for_the_workers_surfaces_and_names_the_worker_script():
    r = Run("web", tagged=("site", "auth"))
    assert r.code == 0
    assert r.ran == [["site", "auth"]]
    assert sorted(r.recorded) == [("auth", "pass"), ("site", "pass")]
    assert any("worker" in line and r"workers\scan-proxy\test-external.ps1" in line for line in r.lines)


def test_the_worker_wrapper_still_runs_and_records_its_surfaces():
    r = Run("scan-proxy", tagged=("worker",))
    assert r.code == 0
    assert r.ran == [["worker"]]
    assert r.recorded == [("worker", "pass")]


def test_a_surface_a_wrapper_owns_with_no_tagged_tests_is_still_recorded_fail():
    r = Run("web", tagged=("site",))
    assert r.code == 1
    assert ("auth", "fail") in r.recorded
    assert "No external tests tagged [auth]; recording fail." in r.lines


def test_a_manifest_with_an_ownerless_surface_stops_the_wrapper_before_anything_runs():
    manifest = {"surfaces": {**MANIFEST["surfaces"], "new": {"name": "new", "platforms": ["web"]}}}
    r = Run("web", manifest=manifest, tagged=("site", "auth", "new"))
    assert r.code == 1
    assert r.ran == [] and r.recorded == []
    assert any("new" in line and "no owner" in line for line in r.lines)


def test_a_surface_two_wrappers_claim_stops_the_wrapper_before_anything_runs():
    manifest = {"surfaces": {**MANIFEST["surfaces"], "two": {"name": "two", "platforms": ["web", "scan-proxy"], "owner": ["web", "scan-proxy"]}}}
    r = Run("scan-proxy", manifest=manifest, tagged=("worker", "two"))
    assert r.code == 1
    assert r.ran == [] and r.recorded == []
    assert any("two" in line and "several" in line for line in r.lines)


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


# --- per-surface results from the run's own per-test data (#89) ---------------------------------


def counts(passed=0, failed=0, skipped=0):
    return ew.Counts(passed=passed, failed=failed, skipped=skipped)


class ResultsHarness(Harness):
    """A run whose per-test data (what the runner's JUnit file says) is faked."""

    def __init__(self, results, tagged=("a", "b"), exit_code=0):
        super().__init__(tagged=tagged, exit_code=exit_code)
        self.results = results

    def go(self, verdicts, skip=False):
        return ew.execute_plan(
            verdicts,
            skip=skip,
            has_tests=lambda s: s in self.tagged,
            run_tests=lambda surfaces: (self.ran.append(list(surfaces)) or self.exit_code),
            record=lambda s, o, v: self.recorded.append((s, o, v)),
            out=self.lines.append,
            read_results=lambda surfaces: self.results,
        )

    def outcomes(self):
        return {s: o for s, o, _ in self.recorded}


def test_one_surfaces_failure_does_not_fail_another_that_passed_in_the_same_run():
    h = ResultsHarness({"a": counts(passed=3), "b": counts(passed=1, failed=1)}, exit_code=1)
    assert h.go([stale("a"), stale("b")]) == 1
    assert h.outcomes() == {"a": "pass", "b": "fail"}


def test_a_surface_with_no_tests_run_is_not_a_pass_even_when_the_run_exited_zero():
    h = ResultsHarness({"a": counts(passed=2)}, exit_code=0)
    assert h.go([stale("a"), stale("b")]) == 1
    assert h.outcomes() == {"a": "pass", "b": "fail"}


def test_a_surface_whose_tests_were_all_skipped_is_not_a_pass():
    h = ResultsHarness({"a": counts(skipped=2)}, exit_code=0)
    assert h.go([stale("a")]) == 1
    assert h.outcomes() == {"a": "fail"}


def test_a_surface_with_passed_and_skipped_tests_and_no_failures_passes():
    h = ResultsHarness({"a": counts(passed=1, skipped=1)}, exit_code=0)
    assert h.go([stale("a")]) == 0
    assert h.outcomes() == {"a": "pass"}


def test_a_failing_exit_code_nobody_can_be_blamed_for_fails_every_run_surface():
    h = ResultsHarness({"a": counts(passed=2), "b": counts(passed=1)}, exit_code=1)
    assert h.go([stale("a"), stale("b")]) == 1
    assert h.outcomes() == {"a": "fail", "b": "fail"}


def test_without_per_test_data_the_exit_code_decides_every_surface():
    h = ResultsHarness(None, exit_code=1)
    assert h.go([stale("a"), stale("b")]) == 1
    assert h.outcomes() == {"a": "fail", "b": "fail"}
    h = ResultsHarness(None, exit_code=0)
    assert h.go([stale("a"), stale("b")]) == 0
    assert h.outcomes() == {"a": "pass", "b": "pass"}


def test_the_run_exit_code_is_kept_when_a_surface_fails():
    h = ResultsHarness({"a": counts(failed=1)}, exit_code=3)
    assert h.go([stale("a")]) == 3


def test_a_passing_surface_advances_its_freshness_and_a_failing_one_does_not_erase_it(tmp_path, monkeypatch):
    import record_external_result as rec

    status_file = tmp_path / "external_status.json"
    monkeypatch.setattr(rec, "STATUS_FILE", status_file)
    rec.record_surface("auth", "pass", commit="c1", now="2026-10-01T00:00:00Z")
    rec.record_surface("site", "pass", commit="c1", now="2026-10-01T00:00:00Z")
    ew.execute_plan(
        [stale("auth"), stale("site")],
        skip=False,
        has_tests=lambda s: True,
        run_tests=lambda surfaces: 1,
        record=lambda s, o, v: rec.record_surface(s, o, versions=v, commit="c2", now="2026-10-10T00:00:00Z"),
        out=lambda line: None,
        read_results=lambda surfaces: {"auth": counts(passed=2), "site": counts(failed=1)},
    )
    surfaces = json.loads(status_file.read_text())["surfaces"]
    assert surfaces["auth"]["result"] == "pass" and surfaces["auth"]["timestamp"] == "2026-10-10T00:00:00Z"
    assert surfaces["site"]["result"] == "fail"


JUNIT = """<?xml version="1.0"?>
<testsuites>
  <testsuite name="src/external/supabaseAuth.external.test.ts">
    <testcase classname="src/external/supabaseAuth.external.test.ts" name="[supabase-auth] live contract &gt; signs in"/>
    <testcase classname="src/external/supabaseAuth.external.test.ts" name="[supabase-auth] live contract &gt; refreshes"/>
  </testsuite>
  <testsuite name="src/external/pagesSite.external.test.ts">
    <testcase classname="x" name="[pages-site] live contract &gt; runs the bundle"><failure message="boom"/></testcase>
    <testcase classname="x" name="[pages-site] live contract &gt; skipped one"><skipped/></testcase>
  </testsuite>
</testsuites>
"""

# The shape `node --test --test-reporter=junit` really writes: top-level tests are bare testcases
# under <testsuites>, a describe() is a <testsuite> named for it, and tests the name pattern
# filtered out are absent.
NODE_JUNIT = """<?xml version="1.0"?>
<testsuites>
  <testcase name="[anthropic] good one" classname="test"/>
  <testcase name="[anthropic] bad one" classname="test" failure="x"><failure message="x"/></testcase>
  <testsuite name="[revenuecat-rest] group" tests="1">
    <testcase name="inner" classname="test"/>
  </testsuite>
</testsuites>
"""

PYTEST_JUNIT = """<testsuites><testsuite>
  <testcase classname="tests.test_x" name="test_a"><properties><property name="surface" value="anthropic"/></properties></testcase>
  <testcase classname="tests.test_x" name="test_b"><properties><property name="surface" value="anthropic"/></properties><failure/></testcase>
</testsuite></testsuites>"""


def test_surface_results_counts_each_tagged_testcase_by_its_own_outcome():
    got = ew.surface_results(JUNIT, ["supabase-auth", "pages-site", "other"], ew.TAG_FORMATS["bracket"])
    assert got == {"supabase-auth": counts(passed=2), "pages-site": counts(failed=1, skipped=1)}


def test_surface_results_reads_a_tag_from_an_enclosing_suite_name():
    got = ew.surface_results(NODE_JUNIT, ["anthropic", "revenuecat-rest"], ew.TAG_FORMATS["bracket"])
    assert got == {"anthropic": counts(passed=1, failed=1), "revenuecat-rest": counts(passed=1)}


def test_a_test_tagged_with_two_surfaces_counts_for_both():
    xml = '<testsuites><testcase name="[a] [b] shared"><failure/></testcase></testsuites>'
    got = ew.surface_results(xml, ["a", "b"], ew.TAG_FORMATS["bracket"])
    assert got == {"a": counts(failed=1), "b": counts(failed=1)}


def test_surface_results_reads_a_pytest_surface_property_for_the_marker_style():
    got = ew.surface_results(PYTEST_JUNIT, ["anthropic", "supabase"], ew.TAG_FORMATS["marker"])
    assert got == {"anthropic": counts(passed=1, failed=1)}


@pytest.mark.parametrize("text", ["", "not xml", "<testsuites/>", "<testsuites><testsuite/></testsuites>"])
def test_surface_results_is_none_when_there_is_no_usable_per_test_data(text):
    assert ew.surface_results(text, ["a"], ew.TAG_FORMATS["bracket"]) is None


def test_read_results_file_is_none_when_the_runner_wrote_nothing(tmp_path):
    assert ew.read_results_file(tmp_path / "missing.xml", ["a"], ew.TAG_FORMATS["bracket"]) is None
    f = tmp_path / "r.xml"
    f.write_text(JUNIT, encoding="utf-8")
    assert ew.read_results_file(f, ["pages-site"], ew.TAG_FORMATS["bracket"]) == {
        "pages-site": counts(failed=1, skipped=1)
    }
