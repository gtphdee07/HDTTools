"""Function tests for scripts/record_external_result.py (roadmap item #7)."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "record_external_result.py"
_spec = importlib.util.spec_from_file_location("record_external_result", _SCRIPT_PATH)
record_external_result = importlib.util.module_from_spec(_spec)
sys.modules["record_external_result"] = record_external_result
_spec.loader.exec_module(record_external_result)


def test_record_writes_a_new_entry(tmp_path, monkeypatch):
    status_file = tmp_path / "external_status.json"
    monkeypatch.setattr(record_external_result, "STATUS_FILE", status_file)

    data = record_external_result.record("android", "weekly", 0, now="2026-08-24T00:00:00Z")

    assert data == {"android": {"weekly": {"passed": True, "timestamp": "2026-08-24T00:00:00Z"}}}
    assert json.loads(status_file.read_text()) == data


def test_record_maps_a_nonzero_exit_code_to_failed(tmp_path, monkeypatch):
    status_file = tmp_path / "external_status.json"
    monkeypatch.setattr(record_external_result, "STATUS_FILE", status_file)

    data = record_external_result.record("android", "weekly", 1, now="2026-08-24T00:00:00Z")

    assert data["android"]["weekly"]["passed"] is False


def test_record_preserves_other_platforms_and_suites(tmp_path, monkeypatch):
    status_file = tmp_path / "external_status.json"
    status_file.write_text(
        json.dumps(
            {
                "android": {"weekly": {"passed": True, "timestamp": "2026-08-20T00:00:00Z"}},
                "scan_proxy": {"release": {"passed": True, "timestamp": "2026-08-22T00:00:00Z"}},
            }
        )
    )
    monkeypatch.setattr(record_external_result, "STATUS_FILE", status_file)

    data = record_external_result.record("scan_proxy", "weekly", 0, now="2026-08-24T00:00:00Z")

    assert data["android"]["weekly"]["timestamp"] == "2026-08-20T00:00:00Z"
    assert data["scan_proxy"]["release"]["passed"] is True
    assert data["scan_proxy"]["weekly"] == {"passed": True, "timestamp": "2026-08-24T00:00:00Z"}


def test_record_overwrites_a_stale_entry_for_the_same_platform_and_suite(tmp_path, monkeypatch):
    status_file = tmp_path / "external_status.json"
    status_file.write_text(
        json.dumps({"android": {"weekly": {"passed": False, "timestamp": "2026-08-20T00:00:00Z"}}})
    )
    monkeypatch.setattr(record_external_result, "STATUS_FILE", status_file)

    data = record_external_result.record("android", "weekly", 0, now="2026-08-24T00:00:00Z")

    assert data["android"]["weekly"] == {"passed": True, "timestamp": "2026-08-24T00:00:00Z"}


def _fresh_status(tmp_path, monkeypatch, initial=None):
    status_file = tmp_path / "external_status.json"
    if initial is not None:
        status_file.write_text(json.dumps(initial))
    monkeypatch.setattr(record_external_result, "STATUS_FILE", status_file)
    return status_file


def test_record_surface_stores_pass_shape(tmp_path, monkeypatch):
    status_file = _fresh_status(tmp_path, monkeypatch)

    record_external_result.record_surface(
        "supabase-auth",
        "pass",
        versions={"@supabase/supabase-js": "2.117.2"},
        commit="abc123",
        now="2026-10-03T00:00:00Z",
    )

    assert json.loads(status_file.read_text())["surfaces"]["supabase-auth"] == {
        "result": "pass",
        "passed": True,
        "timestamp": "2026-10-03T00:00:00Z",
        "commit": "abc123",
        "versions": {"@supabase/supabase-js": "2.117.2"},
    }


def test_record_surface_stores_fail(tmp_path, monkeypatch):
    _fresh_status(tmp_path, monkeypatch)

    data = record_external_result.record_surface("s", "fail", commit="abc", now="2026-10-03T00:00:00Z")

    assert data["surfaces"]["s"]["result"] == "fail"
    assert data["surfaces"]["s"]["passed"] is False


def test_record_surface_stores_override_reason(tmp_path, monkeypatch):
    _fresh_status(tmp_path, monkeypatch)

    data = record_external_result.record_surface(
        "s", "fail", commit="abc", override_reason="hotfix", now="2026-10-03T00:00:00Z"
    )

    assert data["surfaces"]["s"]["override_reason"] == "hotfix"


def test_a_later_real_pass_clears_the_override_reason(tmp_path, monkeypatch):
    _fresh_status(
        tmp_path,
        monkeypatch,
        {"surfaces": {"s": {"result": "fail", "passed": False, "timestamp": "t", "commit": "c", "override_reason": "x"}}},
    )

    data = record_external_result.record_surface("s", "pass", commit="abc", now="2026-10-03T00:00:00Z")

    assert "override_reason" not in data["surfaces"]["s"]


def test_skipped_on_a_fresh_surface_records_skipped_not_a_pass(tmp_path, monkeypatch):
    _fresh_status(tmp_path, monkeypatch)

    data = record_external_result.record_surface("s", "skipped", commit="abc", now="2026-10-03T00:00:00Z")

    assert data["surfaces"]["s"]["result"] == "skipped"
    assert data["surfaces"]["s"]["passed"] is False
    assert data["surfaces"]["s"]["last_skipped_at"] == "2026-10-03T00:00:00Z"


def test_skipped_never_advances_an_existing_pass(tmp_path, monkeypatch):
    earlier = {"result": "pass", "passed": True, "timestamp": "2026-09-01T00:00:00Z", "commit": "old", "versions": {"p": "1.0.0"}}
    _fresh_status(tmp_path, monkeypatch, {"surfaces": {"s": earlier}})

    data = record_external_result.record_surface("s", "skipped", commit="new", versions={"p": "2.0.0"}, now="2026-10-03T00:00:00Z")

    entry = data["surfaces"]["s"]
    assert entry["result"] == "pass"
    assert entry["timestamp"] == "2026-09-01T00:00:00Z"
    assert entry["commit"] == "old"
    assert entry["versions"] == {"p": "1.0.0"}
    assert entry["last_skipped_at"] == "2026-10-03T00:00:00Z"


def test_record_surface_keeps_old_platform_suite_entries_as_history(tmp_path, monkeypatch):
    old = {"android": {"weekly": {"passed": True, "timestamp": "2026-09-09T16:06:16Z"}}}
    status_file = _fresh_status(tmp_path, monkeypatch, old)

    record_external_result.record_surface("s", "pass", commit="abc", now="2026-10-03T00:00:00Z")

    on_disk = json.loads(status_file.read_text())
    assert on_disk["android"] == old["android"]
    assert "s" in on_disk["surfaces"]


def test_record_surface_leaves_other_surfaces_alone(tmp_path, monkeypatch):
    other = {"result": "pass", "passed": True, "timestamp": "t", "commit": "c", "versions": {}}
    _fresh_status(tmp_path, monkeypatch, {"surfaces": {"other": other}})

    data = record_external_result.record_surface("s", "pass", commit="abc", now="2026-10-03T00:00:00Z")

    assert data["surfaces"]["other"] == other


def test_record_surface_rejects_unknown_outcome(tmp_path, monkeypatch):
    import pytest

    _fresh_status(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        record_external_result.record_surface("s", "maybe", commit="abc")


def test_cli_surface_mode_records_and_legacy_positional_mode_still_works(tmp_path, monkeypatch):
    status_file = _fresh_status(tmp_path, monkeypatch)

    record_external_result.main(
        ["--surface", "s", "--outcome", "pass", "--commit", "abc", "--versions", '{"p": "1.0.0"}', "--override-reason", "why"]
    )
    record_external_result.main(["android", "weekly", "0"])

    on_disk = json.loads(status_file.read_text())
    assert on_disk["surfaces"]["s"]["versions"] == {"p": "1.0.0"}
    assert on_disk["surfaces"]["s"]["override_reason"] == "why"
    assert on_disk["android"]["weekly"]["passed"] is True


def test_record_override_marks_each_surface_without_changing_its_result(tmp_path, monkeypatch):
    earlier = {"result": "fail", "passed": False, "timestamp": "2026-09-01T00:00:00Z", "commit": "old", "versions": {}}
    _fresh_status(tmp_path, monkeypatch, {"surfaces": {"failed": earlier}})

    data = record_external_result.record_override(["failed", "never-run"], "hotfix", now="2026-10-03T00:00:00Z")

    assert data["surfaces"]["failed"] == {**earlier, "override_reason": "hotfix", "overridden_at": "2026-10-03T00:00:00Z"}
    # A surface with no record yet gets only the override, so it still reads as never passed.
    assert data["surfaces"]["never-run"] == {"override_reason": "hotfix", "overridden_at": "2026-10-03T00:00:00Z"}


def test_a_failed_or_skipped_run_keeps_the_override_but_only_a_pass_clears_it(tmp_path, monkeypatch):
    marked = {"override_reason": "hotfix", "overridden_at": "2026-10-02T00:00:00Z"}
    _fresh_status(tmp_path, monkeypatch, {"surfaces": {"s": marked}})

    failed = record_external_result.record_surface("s", "fail", commit="a", now="2026-10-03T00:00:00Z")
    assert failed["surfaces"]["s"]["override_reason"] == "hotfix"

    skipped = record_external_result.record_surface("s", "skipped", commit="b", now="2026-10-04T00:00:00Z")
    assert skipped["surfaces"]["s"]["override_reason"] == "hotfix"

    passed = record_external_result.record_surface("s", "pass", commit="c", now="2026-10-05T00:00:00Z")
    assert "override_reason" not in passed["surfaces"]["s"]
    assert "overridden_at" not in passed["surfaces"]["s"]
