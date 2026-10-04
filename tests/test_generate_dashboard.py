"""Tests for scripts/generate_dashboard.py's decision logic (#49): which
pytest selection feeds each tier, how live External cells and the saved
snapshot combine into rows, and that --from-snapshot never runs a suite.
The suite runners themselves are I/O glue and are not run here."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import generate_dashboard as gd  # noqa: E402

pytestmark = [pytest.mark.core, pytest.mark.minor]


def test_python_minor_and_major_use_the_context_markers():
    assert gd.python_selection("core", "minor") == "minor and core"
    assert gd.python_selection("streamlit", "major") == "streamlit"


def test_rows_cover_every_context_in_order():
    rows = gd.build_rows({}, {}, {})
    assert [r.name for r in rows] == ["Core", "Streamlit", "Web", "Android", "Scan Proxy"]


def test_a_context_missing_from_the_snapshot_is_n_a():
    row = gd.build_rows({}, {}, {})[0]
    assert (row.minor, row.major, row.coverage) == (None, None, None)


def test_snapshot_results_and_live_cells_combine_per_platform():
    entries = {"Web": {"minor": ["blue", "5/5"], "major": ["blue", "5/5"], "coverage": [90.0, "yellow"],
                       "coverage_gated": False}}
    rows = {r.name: r for r in gd.build_rows(entries, {}, {"web": ["fresh", "planned"]})}
    assert rows["Web"].minor == ("blue", "5/5")
    assert rows["Web"].surfaces == ("blue", "1/1 (1 planned)")
    assert rows["Core"].surfaces is None


def test_legacy_external_cells_come_only_from_android_and_scan_proxy():
    status = {
        "android": {"weekly": {"passed": True, "timestamp": "2026-09-09T16:06:16Z"}},
        "scan_proxy": {"weekly": {"passed": True, "timestamp": "2026-08-24T18:29:35Z"}},
    }
    assert gd.legacy_external_cell("Android", status) is not None
    assert gd.legacy_external_cell("Scan Proxy", status) is not None
    assert gd.legacy_external_cell("Web", status) is None
    assert gd.legacy_external_cell("Core", status) is None


def test_from_snapshot_runs_no_suite_and_writes_the_graphic(tmp_path, monkeypatch, capsys):
    snapshot = tmp_path / "results.json"
    snapshot.write_text('{"timestamp": "2026-10-04T00:00:00Z", "commit": "abc1234", "platforms": '
                        '{"Core": {"minor": ["green", "9/10"], "major": null, "coverage": null, '
                        '"coverage_gated": false}}}', encoding="utf-8")
    svg = tmp_path / "dashboard.svg"
    monkeypatch.setattr(gd, "SNAPSHOT_FILE", snapshot)
    monkeypatch.setattr(gd, "DASHBOARD_SVG", svg)
    monkeypatch.setattr(gd, "EXTERNAL_STATUS_FILE", tmp_path / "none.json")
    monkeypatch.setattr(gd, "surface_states", lambda: {})

    def boom(*_a, **_k):
        raise AssertionError("a suite was run")

    monkeypatch.setattr(gd, "measure", boom)
    monkeypatch.setattr(gd, "_run", boom)
    assert gd.main(["--from-snapshot"]) == 0
    text = svg.read_text(encoding="utf-8")
    assert "9/10" in text and "tests run: 2026-10-04 @ abc1234" in text
    assert snapshot.read_text(encoding="utf-8").count("9/10") == 1  # snapshot untouched


def test_from_snapshot_survives_unreadable_surface_data(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(gd, "SNAPSHOT_FILE", tmp_path / "missing.json")
    monkeypatch.setattr(gd, "DASHBOARD_SVG", tmp_path / "dashboard.svg")
    monkeypatch.setattr(gd, "EXTERNAL_STATUS_FILE", tmp_path / "none.json")

    def broken():
        raise RuntimeError("manifest unreadable")

    monkeypatch.setattr(gd, "surface_states", broken)
    assert gd.main(["--from-snapshot"]) == 0
    assert "Surface freshness unavailable" in capsys.readouterr().out
    assert "no results recorded" in (tmp_path / "dashboard.svg").read_text(encoding="utf-8")
