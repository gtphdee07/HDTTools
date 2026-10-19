"""Tests for scripts/generate_dashboard.py's decision logic (#49, #44): which
pytest selection feeds each tier, how the live External cell and the saved
snapshot combine into rows, what each External surface's state is, and that
--from-snapshot never runs a suite. The suite runners themselves are I/O glue
and are not run here."""

import re
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
    rows = gd.build_rows({}, {})
    assert [r.name for r in rows] == ["Core", "Streamlit", "Web", "Android", "Scan Proxy"]


def test_a_context_missing_from_the_snapshot_is_n_a():
    row = gd.build_rows({}, {})[0]
    assert (row.minor, row.major, row.coverage, row.external) == (None, None, None, None)


def test_snapshot_results_and_live_cells_combine_per_platform():
    entries = {"Web": {"minor": ["blue", "5/5"], "major": ["blue", "5/5"], "coverage": [90.0, "yellow"],
                       "coverage_gated": False}}
    rows = {r.name: r for r in gd.build_rows(entries, {"web": ["fresh", "planned"]})}
    assert rows["Web"].minor == ("blue", "5/5")
    assert rows["Web"].external == ("blue", "1/1 (1 planned)")
    assert rows["Core"].external is None


# --- per-surface status (#44), from a fake manifest, status file and git ---

PASS = {"result": "pass", "passed": True, "timestamp": "2026-10-10T00:00:00Z", "commit": "abc", "versions": {}}


def _surface(name, platforms, status="active"):
    return {"name": name, "status": status, "platforms": platforms, "boundary_files": [f"{name}.ts"],
            "dependency_pins": [], "registry_packages": [], "max_paid_calls": 0}


class _Git:
    def __init__(self, changed=()):
        self.changed = set(changed)

    def changed_since(self, _sha, paths):
        return [p for p in paths if p in self.changed]


FAKE_MANIFEST = {"surfaces": {s["name"]: s for s in (
    _surface("ok", ["web", "scan-proxy"]),
    _surface("broken", ["web"]),
    _surface("skipped-one", ["web"]),
    _surface("changed", ["android"]),
    _surface("forced", ["android"]),
    _surface("later", ["web"], status="planned"),
)}}
FAKE_STATUS = {
    "surfaces": {
        "ok": PASS,
        "broken": {**PASS, "result": "fail", "passed": False},
        "skipped-one": {"result": "skipped", "passed": False, "timestamp": "2026-10-11T00:00:00Z",
                        "commit": "abc", "versions": {}, "last_skipped_at": "2026-10-11T00:00:00Z"},
        "changed": PASS,
        "forced": {**PASS, "override_reason": "hotfix"},
    },
    # Old platform+suite entries: history only, never shown as current.
    "scan_proxy": {"weekly": {"passed": True, "timestamp": "2026-10-07T18:52:02Z"}},
    "android": {"weekly": {"passed": True, "timestamp": "2026-09-09T16:06:16Z"}},
}
CHANGED = ["changed.ts", "forced.ts"]


def test_every_surface_state_comes_through_with_its_platforms():
    rows = gd.surface_verdicts(FAKE_MANIFEST, FAKE_STATUS, _Git(changed=CHANGED))
    assert {r.name: r.state for r in rows} == {
        "ok": "fresh", "broken": "failed", "skipped-one": "skipped",
        "changed": "stale", "forced": "overridden", "later": "planned",
    }
    assert {r.name: r.platforms for r in rows}["ok"] == ("web", "scan-proxy")


def test_surface_verdicts_contact_no_registry():
    manifest = {"surfaces": {"x": {**_surface("x", ["web"]),
                                   "registry_packages": [{"ecosystem": "npm", "package": "left-pad"}]}}}
    rows = gd.surface_verdicts(manifest, {"surfaces": {"x": PASS}}, _Git())
    assert [r.state for r in rows] == ["fresh"]  # a real registry lookup here would count as unreachable


def test_states_are_grouped_by_platform_for_the_external_cell():
    rows = gd.surface_verdicts(FAKE_MANIFEST, FAKE_STATUS, _Git(changed=CHANGED))
    assert gd.states_by_platform(rows) == {
        "web": ["fresh", "failed", "skipped", "planned"],
        "scan-proxy": ["fresh"],
        "android": ["stale", "overridden"],
    }


def _generate(tmp_path, monkeypatch):
    import external_freshness as ef

    snapshot = tmp_path / "results.json"
    snapshot.write_text('{"timestamp": "2026-10-04T00:00:00Z", "commit": "abc1234", "platforms": {}}',
                        encoding="utf-8")
    svg = tmp_path / "dashboard.svg"
    monkeypatch.setattr(gd, "SNAPSHOT_FILE", snapshot)
    monkeypatch.setattr(gd, "DASHBOARD_SVG", svg)
    monkeypatch.setattr(ef, "load_manifest", lambda: FAKE_MANIFEST)
    monkeypatch.setattr(ef, "load_status", lambda: FAKE_STATUS)
    monkeypatch.setattr(ef, "GitHistory", lambda: _Git(changed=CHANGED))
    assert gd.main(["--from-snapshot"]) == 0
    return svg.read_text(encoding="utf-8")


def test_the_graphic_lists_every_surface_state_from_the_status_file(tmp_path, monkeypatch):
    text = _generate(tmp_path, monkeypatch)
    assert "External surfaces" in text
    for state in ("fresh", "failed", "skipped", "stale", "overridden", "planned - not covered"):
        assert f">{state}</text>" in text, state


def test_old_platform_suite_entries_are_not_shown_as_current(tmp_path, monkeypatch):
    text = _generate(tmp_path, monkeypatch)
    # The old cells read "1/1 (<age>d)"; the fake status file still holds both old entries.
    assert not re.search(r"\(\d+d\)", text)
    assert "weekly" not in text


def test_from_snapshot_runs_no_suite_and_writes_the_graphic(tmp_path, monkeypatch, capsys):
    snapshot = tmp_path / "results.json"
    snapshot.write_text('{"timestamp": "2026-10-04T00:00:00Z", "commit": "abc1234", "platforms": '
                        '{"Core": {"minor": ["green", "9/10"], "major": null, "coverage": null, '
                        '"coverage_gated": false}}}', encoding="utf-8")
    svg = tmp_path / "dashboard.svg"
    monkeypatch.setattr(gd, "SNAPSHOT_FILE", snapshot)
    monkeypatch.setattr(gd, "DASHBOARD_SVG", svg)
    monkeypatch.setattr(gd, "surface_verdicts", lambda: [])

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

    def broken():
        raise RuntimeError("manifest unreadable")

    monkeypatch.setattr(gd, "surface_verdicts", broken)
    assert gd.main(["--from-snapshot"]) == 0
    assert "Surface freshness unavailable" in capsys.readouterr().out
    text = (tmp_path / "dashboard.svg").read_text(encoding="utf-8")
    assert "no results recorded" in text
    assert "External surfaces" not in text


def test_surface_verdicts_never_ask_the_registry_even_when_it_would_answer(monkeypatch):
    # The dashboard and the commit hook must stay offline and fast: a registry lookup that happens to
    # succeed would still be a network call, so make any lookup fail the test.
    import external_freshness as ef

    def refuse(ecosystem, package):
        raise AssertionError(f"registry asked for {ecosystem}/{package}")

    monkeypatch.setattr(ef, "fetch_publish_times", refuse)
    manifest = {"surfaces": {"x": {**_surface("x", ["web"]),
                                   "registry_packages": [{"ecosystem": "npm", "package": "left-pad"}]}}}

    rows = gd.surface_verdicts(manifest, {"surfaces": {"x": PASS}}, _Git())

    assert [r.state for r in rows] == ["fresh"]
