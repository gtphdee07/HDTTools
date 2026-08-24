"""Function tests for scripts/record_external_result.py (roadmap item #7)."""

import importlib.util
import json
import sys
from pathlib import Path

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
