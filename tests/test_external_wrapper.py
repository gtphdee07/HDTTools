"""Function tests for scripts/external_wrapper.py: the decision logic behind
the platform wrappers, with the test runner and recorder faked."""

import importlib.util
import sys
from pathlib import Path

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
