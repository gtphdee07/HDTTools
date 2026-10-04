"""Function tests for scripts/external_freshness.py (ADR-0008), with git
history, the status file and registry responses all faked."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "external_freshness.py"
_spec = importlib.util.spec_from_file_location("external_freshness", _SCRIPT_PATH)
ef = importlib.util.module_from_spec(_spec)
sys.modules["external_freshness"] = ef
_spec.loader.exec_module(ef)

PASS_TS = "2026-10-01T12:00:00Z"
PKG = "@supabase/supabase-js"


def surface(**overrides):
    base = {
        "name": "supabase-auth",
        "status": "active",
        "platforms": ["web"],
        "boundary_files": ["web/src/auth.tsx"],
        "dependency_pins": ["web/package.json", "web/package-lock.json"],
        "registry_packages": [{"ecosystem": "npm", "package": PKG}],
        "max_paid_calls": 0,
    }
    base.update(overrides)
    return base


def manifest(*surfaces):
    return {"surfaces": {s["name"]: s for s in (surfaces or (surface(),))}}


def passed(ts=PASS_TS, sha="abc123", **extra):
    return {"result": "pass", "passed": True, "timestamp": ts, "commit": sha, "versions": {}, **extra}


def status_with(entry, name="supabase-auth"):
    return {"surfaces": {name: entry}}


class FakeGit:
    def __init__(self, changed=(), unknown_sha=False):
        self.changed = list(changed)
        self.unknown_sha = unknown_sha
        self.calls = []

    def changed_since(self, sha, paths):
        self.calls.append((sha, list(paths)))
        if self.unknown_sha:
            raise ef.GitError(f"unknown revision {sha}")
        return [p for p in self.changed if p in paths]


class FakeRegistry:
    def __init__(self, times=None, down=False):
        self.times = times or {}
        self.down = down

    def __call__(self, ecosystem, package):
        if self.down:
            raise ef.RegistryError("unreachable")
        return self.times[package]


QUIET_REGISTRY = {PKG: {"2.100.0": "2026-09-01T00:00:00Z", "created": "2020-01-01T00:00:00Z"}}


def verdict(status, git=None, registry=None, m=None):
    result = ef.evaluate(m or manifest(), status, git or FakeGit(), registry or FakeRegistry(QUIET_REGISTRY))
    return result[0]


def test_fresh_when_nothing_changed_and_no_newer_release():
    v = verdict(status_with(passed()))
    assert v.state == "fresh"
    assert v.reasons == []
    assert v.blocking is False


def test_stale_when_never_passed():
    v = verdict({})
    assert v.state == "stale"
    assert any("never passed" in r for r in v.reasons)
    assert v.blocking is True


def test_stale_when_a_boundary_file_changed_since_last_pass():
    v = verdict(status_with(passed()), git=FakeGit(changed=["web/src/auth.tsx"]))
    assert v.state == "stale"
    assert any("web/src/auth.tsx" in r for r in v.reasons)


@pytest.mark.parametrize("pin", ["web/package.json", "web/package-lock.json"])
def test_stale_when_a_dependency_pin_changed_since_last_pass(pin):
    v = verdict(status_with(passed()), git=FakeGit(changed=[pin]))
    assert v.state == "stale"
    assert any(pin in r for r in v.reasons)


def test_unrelated_changed_files_do_not_make_it_stale():
    v = verdict(status_with(passed()), git=FakeGit(changed=["README.md"]))
    assert v.state == "fresh"


def test_git_is_asked_about_the_recorded_commit():
    git = FakeGit()
    verdict(status_with(passed(sha="deadbeef")), git=git)
    assert git.calls[0][0] == "deadbeef"


def test_stale_when_recorded_commit_is_unknown_to_git():
    v = verdict(status_with(passed()), git=FakeGit(unknown_sha=True))
    assert v.state == "stale"
    assert any("commit" in r for r in v.reasons)


def test_a_pass_with_no_recorded_commit_is_stale_not_a_crash():
    entry = {"result": "pass", "passed": True, "timestamp": PASS_TS}
    v = verdict(status_with(entry))
    assert v.state == "stale"
    assert any("commit" in r for r in v.reasons)


def test_stale_when_newer_stable_release_published_after_last_pass():
    times = {PKG: {"2.100.0": "2026-09-01T00:00:00Z", "2.101.0": "2026-10-02T00:00:00Z"}}
    v = verdict(status_with(passed()), registry=FakeRegistry(times))
    assert v.state == "stale"
    assert any("2.101.0" in r for r in v.reasons)


def test_patch_release_counts():
    times = {PKG: {"2.100.1": "2026-10-02T00:00:00Z"}}
    v = verdict(status_with(passed()), registry=FakeRegistry(times))
    assert v.state == "stale"


def test_release_published_before_last_pass_does_not_count_even_if_not_upgraded():
    times = {PKG: {"2.100.0": "2026-09-30T00:00:00Z"}}
    v = verdict(status_with(passed()), registry=FakeRegistry(times))
    assert v.state == "fresh"


@pytest.mark.parametrize("version", ["3.0.0-rc.1", "3.0.0-beta.2", "3.0.0-canary.4", "3.0.0+build5"])
def test_pre_release_versions_are_excluded(version):
    times = {PKG: {version: "2026-10-02T00:00:00Z"}}
    v = verdict(status_with(passed()), registry=FakeRegistry(times))
    assert v.state == "fresh"


def test_registry_metadata_keys_that_are_not_versions_are_ignored():
    times = {PKG: {"created": "2026-10-02T00:00:00Z", "modified": "2026-10-02T00:00:00Z"}}
    v = verdict(status_with(passed()), registry=FakeRegistry(times))
    assert v.state == "fresh"


def test_unreachable_registry_is_stale():
    v = verdict(status_with(passed()), registry=FakeRegistry(down=True))
    assert v.state == "stale"
    assert any("registry" in r for r in v.reasons)


def test_never_passed_still_reports_registry_unreachable_without_crashing():
    v = verdict({}, registry=FakeRegistry(down=True))
    assert v.state == "stale"


def test_a_failed_last_run_is_stale():
    v = verdict(status_with({"result": "fail", "passed": False, "timestamp": PASS_TS, "commit": "abc"}))
    assert v.state == "stale"
    assert any("failed" in r for r in v.reasons)


def test_skipped_record_alone_never_counts_as_a_pass():
    v = verdict(status_with({"result": "skipped", "passed": False, "timestamp": PASS_TS, "commit": "abc"}))
    assert v.state == "stale"
    assert any("never passed" in r for r in v.reasons)


def test_skip_after_a_pass_does_not_advance_freshness():
    entry = passed(ts="2026-09-01T00:00:00Z", last_skipped_at="2026-10-03T00:00:00Z")
    times = {PKG: {"2.101.0": "2026-09-15T00:00:00Z"}}
    v = verdict(status_with(entry), registry=FakeRegistry(times))
    assert v.state == "stale"


def test_planned_surface_is_shown_but_non_blocking_and_skips_all_checks():
    m = manifest(surface(status="planned"))
    git = FakeGit()
    v = verdict({}, git=git, registry=FakeRegistry(down=True), m=m)
    assert v.state == "planned"
    assert v.blocking is False
    assert git.calls == []


def test_old_platform_suite_entries_are_ignored():
    old = {"android": {"weekly": {"passed": True, "timestamp": "2026-10-02T00:00:00Z"}}}
    v = verdict(old)
    assert v.state == "stale"
    assert any("never passed" in r for r in v.reasons)


def test_old_entry_named_like_the_surface_does_not_count_as_a_pass():
    old = {"supabase-auth": {"weekly": {"passed": True, "timestamp": PASS_TS}}}
    assert verdict(old).state == "stale"


def test_versions_seen_reports_latest_stable_per_package():
    times = {PKG: {"2.100.0": "2026-09-01T00:00:00Z", "2.99.0": "2026-08-01T00:00:00Z", "3.0.0-rc.1": "2026-09-02T00:00:00Z"}}
    v = verdict(status_with(passed()), registry=FakeRegistry(times))
    assert v.versions == {PKG: "2.100.0"}


def test_only_filter_limits_surfaces():
    m = manifest(surface(), surface(name="other"))
    result = ef.evaluate(m, {}, FakeGit(), FakeRegistry(QUIET_REGISTRY), only=["other"])
    assert [v.surface for v in result] == ["other"]


def test_surfaces_for_platform_derives_the_dependency_chain():
    m = manifest(surface(), surface(name="worker-x", platforms=["worker", "android"]))
    assert ef.surfaces_for_platform(m, "web") == ["supabase-auth"]
    assert ef.surfaces_for_platform(m, "android") == ["worker-x"]


def test_load_manifest_merges_one_file_per_surface(tmp_path):
    (tmp_path / "surfaces").mkdir()
    (tmp_path / "surfaces" / "a.json").write_text(json.dumps(surface(name="a")))
    (tmp_path / "surfaces" / "b.json").write_text(json.dumps(surface(name="b", status="planned")))
    m = ef.load_manifest(tmp_path)
    assert sorted(m["surfaces"]) == ["a", "b"]


def test_load_manifest_rejects_name_not_matching_filename(tmp_path):
    (tmp_path / "surfaces").mkdir()
    (tmp_path / "surfaces" / "a.json").write_text(json.dumps(surface(name="zzz")))
    with pytest.raises(ValueError):
        ef.load_manifest(tmp_path)


def test_the_real_manifest_declares_supabase_auth():
    m = ef.load_manifest()
    s = m["surfaces"]["supabase-auth"]
    assert s["status"] == "active"
    assert s["boundary_files"] == ["web/src/auth.tsx"]
    assert s["dependency_pins"] == ["web/package.json", "web/package-lock.json"]
    assert s["registry_packages"] == [{"ecosystem": "npm", "package": "@supabase/supabase-js"}]
    assert s["max_paid_calls"] == 0
    assert "web" in s["platforms"]


def test_npm_fetcher_returns_the_registry_time_map():
    body = json.dumps({"time": {"1.0.0": "2026-01-01T00:00:00Z"}}).encode()
    seen = []

    def fake_open(url, timeout):
        seen.append(url)
        return body

    assert ef.fetch_npm_times("@supabase/supabase-js", opener=fake_open) == {"1.0.0": "2026-01-01T00:00:00Z"}
    assert seen == ["https://registry.npmjs.org/@supabase%2Fsupabase-js"]


def test_npm_fetcher_wraps_network_errors():
    def boom(url, timeout):
        raise OSError("no network")

    with pytest.raises(ef.RegistryError):
        ef.fetch_npm_times("x", opener=boom)


def test_unknown_ecosystem_is_a_registry_error():
    with pytest.raises(ef.RegistryError):
        ef.fetch_publish_times("cobol", "x")


def test_cli_json_output_and_exit_code(tmp_path, capsys):
    status_file = tmp_path / "s.json"
    status_file.write_text(json.dumps(status_with(passed())))
    code = ef.main(
        ["--json"],
        git=FakeGit(),
        registry=FakeRegistry(QUIET_REGISTRY),
        status_file=status_file,
    )
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["surfaces"]["supabase-auth"]["state"] == "fresh"
    assert out["stale"] == []


def test_cli_exits_1_and_lists_stale_surfaces(tmp_path, capsys):
    code = ef.main(
        ["--json"],
        git=FakeGit(),
        registry=FakeRegistry(QUIET_REGISTRY),
        status_file=tmp_path / "missing.json",
    )
    out = json.loads(capsys.readouterr().out)
    assert code == 1
    assert out["stale"] == ["supabase-auth"]
