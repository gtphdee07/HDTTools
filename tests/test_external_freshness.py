"""Function tests for scripts/external_freshness.py (ADR-0008), with git
history, the status file and registry responses all faked."""

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

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


def test_a_forced_gate_leaves_the_surface_stale_but_shows_the_override():
    # The gate marks a surface it was forced past (scripts/external_gate.py); the surface does not become fresh.
    marked = {"override_reason": "hotfix", "overridden_at": "2026-10-03T00:00:00Z"}
    v = verdict(status_with(marked))
    assert v.state == "stale"
    assert v.override_reason == "hotfix"
    assert v.display_state == "overridden"


def test_a_failed_last_run_is_shown_as_failed_not_just_stale():
    v = verdict(status_with({"result": "fail", "passed": False, "timestamp": PASS_TS, "commit": "abc"}))
    assert v.state == "stale"
    assert v.display_state == "failed"


def test_a_skipped_record_with_no_pass_is_shown_as_skipped_and_stays_blocking():
    v = verdict(status_with({"result": "skipped", "passed": False, "timestamp": PASS_TS, "commit": "abc"}))
    assert v.display_state == "skipped"
    assert v.blocking is True


def test_a_skip_after_a_pass_shows_skipped_only_while_the_surface_is_stale():
    entry = passed(ts="2026-09-01T00:00:00Z", last_skipped_at="2026-10-03T00:00:00Z")
    stale = verdict(status_with(entry), git=FakeGit(changed=["web/src/auth.tsx"]))
    assert (stale.state, stale.display_state) == ("stale", "skipped")
    fresh = verdict(status_with(entry))
    assert (fresh.state, fresh.display_state) == ("fresh", "fresh")


def test_a_pass_after_an_old_skip_does_not_read_as_skipped():
    entry = passed(ts="2026-10-05T00:00:00Z", last_skipped_at="2026-10-03T00:00:00Z")
    v = verdict(status_with(entry), git=FakeGit(changed=["web/src/auth.tsx"]))
    assert v.display_state == "stale"


def test_a_failure_outranks_a_later_skip_and_an_override_outranks_both():
    failed = {"result": "fail", "passed": False, "timestamp": PASS_TS, "commit": "abc",
              "last_skipped_at": "2026-10-03T00:00:00Z"}
    assert verdict(status_with(failed)).display_state == "failed"
    forced = verdict(status_with({**failed, "override_reason": "hotfix"}))
    assert forced.display_state == "overridden"


def test_a_fresh_surface_shows_no_override():
    v = verdict(status_with(passed()))
    assert v.state == "fresh"
    assert v.override_reason is None
    assert v.display_state == "fresh"


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
    assert s["boundary_files"] == [
        "web/src/auth.tsx",
        "android/app/src/main/java/com/rigcheck/app/data/SupabaseAccountBackend.kt",
    ]
    assert s["dependency_pins"] == ["web/package.json", "web/package-lock.json", "android/gradle/libs.versions.toml"]
    assert s["registry_packages"] == [{"ecosystem": "npm", "package": "@supabase/supabase-js"}]
    assert s["max_paid_calls"] == 0
    assert s["platforms"] == ["web", "android"]


@pytest.mark.parametrize(
    "changed",
    [
        "android/app/src/main/java/com/rigcheck/app/data/SupabaseAccountBackend.kt",
        "android/gradle/libs.versions.toml",
    ],
)
def test_changing_the_android_supabase_pieces_makes_supabase_auth_stale(changed):
    real = ef.load_manifest()
    recorded = status_with(passed())
    quiet = FakeRegistry({"@supabase/supabase-js": {"2.0.0": "2026-09-01T00:00:00Z", "created": "2020-01-01T00:00:00Z"}})

    fresh = ef.evaluate(real, recorded, FakeGit(), quiet, only=["supabase-auth"])[0]
    stale = ef.evaluate(real, recorded, FakeGit(changed=[changed]), quiet, only=["supabase-auth"])[0]

    assert fresh.state == "fresh"
    assert stale.state == "stale"
    assert any(changed in r for r in stale.reasons)


def test_supabase_auth_is_in_the_android_release_chain():
    assert "supabase-auth" in ef.surfaces_for_platform(ef.load_manifest(), "android")


def test_worker_token_verification_is_in_the_real_manifest_active_with_the_worker_chains():
    surface = ef.load_manifest()["surfaces"]["worker-token-verification"]
    assert surface["status"] == "active"
    # Every case in its External suite is free: a refused token stops at the 401.
    assert surface["max_paid_calls"] == 0
    assert surface["boundary_files"] == ["workers/scan-proxy/src/auth.ts", "workers/scan-proxy/src/accountTokenContract.ts"]
    assert {"workers/scan-proxy/package.json", "workers/scan-proxy/package-lock.json"} <= set(surface["dependency_pins"])
    assert {"scan-proxy", "android", "web"} == set(surface["platforms"])


@pytest.mark.parametrize("changed", ["workers/scan-proxy/src/auth.ts", "workers/scan-proxy/src/accountTokenContract.ts"])
def test_changing_the_verifier_or_its_contract_makes_worker_token_verification_stale(changed):
    real = ef.load_manifest()
    recorded = status_with(passed(), name="worker-token-verification")

    fresh = ef.evaluate(real, recorded, FakeGit(), FakeRegistry({}), only=["worker-token-verification"])[0]
    stale = ef.evaluate(real, recorded, FakeGit(changed=[changed]), FakeRegistry({}), only=["worker-token-verification"])[0]

    assert fresh.state == "fresh"
    assert stale.state == "stale"
    assert any(changed in r for r in stale.reasons)


def test_every_active_scan_proxy_surface_has_tagged_external_tests():
    # The wrapper filters on "[surface]" in a test name; an active surface with no such test would
    # run nothing and have nothing to record, so it could never go fresh.
    suite = "\n".join(p.read_text(encoding="utf-8") for p in (ef.REPO_ROOT / "workers/scan-proxy/src/external").glob("*.external.test.ts"))
    for name, surface in ef.load_manifest()["surfaces"].items():
        if surface["status"] == "active" and "scan-proxy" in surface["platforms"]:
            assert f'test("[{name}]' in suite or f"test(`[{name}]" in suite, f"no External test is tagged [{name}]"


def test_the_moved_token_checks_no_longer_live_untagged_in_the_weekly_file():
    weekly = (ef.REPO_ROOT / "workers/scan-proxy/src/weekly/scan.weekly.test.ts").read_text(encoding="utf-8")
    assert "no account token gets 401" not in weekly
    assert "match the shared account-token contract" not in weekly


@pytest.mark.parametrize("name", ["supabase-auth", "worker-token-verification", "scan-proxy-worker"])
def test_the_token_surfaces_boundary_files_and_pins_exist(name):
    # A mistyped path never shows as changed, so the surface would silently stop going stale.
    surface = ef.load_manifest()["surfaces"][name]
    for rel in surface["boundary_files"] + surface["dependency_pins"]:
        assert (ef.REPO_ROOT / rel).is_file(), f"{name}: {rel} does not exist"


_WORKER_PACKAGES = {"wrangler", "workerd", "@cloudflare/workers-types"}
_QUIET_WORKER_REGISTRY = {
    package: {"9.0.0": "2026-09-01T00:00:00Z", "created": "2020-01-01T00:00:00Z"} for package in _WORKER_PACKAGES
}


def test_scan_proxy_worker_is_in_the_real_manifest_active_with_one_paid_scan():
    surface = ef.load_manifest()["surfaces"]["scan-proxy-worker"]
    assert surface["status"] == "active"
    # Its one billed call is the real scan that proves the response shape and the spend.
    assert surface["max_paid_calls"] == 1
    # Android and Web call this Worker, so their release gates wait on it.
    assert {"scan-proxy", "android", "web"} == set(surface["platforms"])
    assert {
        "workers/scan-proxy/src/index.ts",
        "workers/scan-proxy/src/scan.ts",
        "workers/scan-proxy/src/request.ts",
        "workers/scan-proxy/src/http.ts",
        "workers/scan-proxy/src/docTypes.ts",
        "workers/scan-proxy/src/idempotencyKey.ts",
    } <= set(surface["boundary_files"])
    assert {"workers/scan-proxy/wrangler.toml", "workers/scan-proxy/package.json", "workers/scan-proxy/package-lock.json"} <= set(
        surface["dependency_pins"]
    )
    assert {p["package"] for p in surface["registry_packages"]} == _WORKER_PACKAGES


def test_the_workers_compatibility_date_lives_in_a_watched_pin_file():
    surface = ef.load_manifest()["surfaces"]["scan-proxy-worker"]
    assert "workers/scan-proxy/wrangler.toml" in surface["dependency_pins"]
    wrangler = (ef.REPO_ROOT / "workers/scan-proxy/wrangler.toml").read_text(encoding="utf-8")
    assert re.search(r'^compatibility_date\s*=\s*"\d{4}-\d{2}-\d{2}"', wrangler, re.MULTILINE)


@pytest.mark.parametrize(
    "changed",
    [
        "workers/scan-proxy/src/index.ts",
        "workers/scan-proxy/src/scan.ts",
        "workers/scan-proxy/src/request.ts",
        "workers/scan-proxy/src/http.ts",
        "workers/scan-proxy/src/docTypes.ts",
        "workers/scan-proxy/src/idempotencyKey.ts",
        "workers/scan-proxy/wrangler.toml",
        "workers/scan-proxy/package.json",
        "workers/scan-proxy/package-lock.json",
    ],
)
def test_changing_the_workers_contract_or_pins_makes_scan_proxy_worker_stale(changed):
    real = ef.load_manifest()
    recorded = status_with(passed(), name="scan-proxy-worker")
    quiet = FakeRegistry(_QUIET_WORKER_REGISTRY)

    fresh = ef.evaluate(real, recorded, FakeGit(), quiet, only=["scan-proxy-worker"])[0]
    stale = ef.evaluate(real, recorded, FakeGit(changed=[changed]), quiet, only=["scan-proxy-worker"])[0]

    assert fresh.state == "fresh"
    assert stale.state == "stale"
    assert any(changed in r for r in stale.reasons)


@pytest.mark.parametrize("package", sorted(_WORKER_PACKAGES))
def test_a_new_stable_release_of_a_watched_cloudflare_package_makes_scan_proxy_worker_stale(package):
    real = ef.load_manifest()
    recorded = status_with(passed(), name="scan-proxy-worker")
    released = {**_QUIET_WORKER_REGISTRY, package: {"9.1.0": "2026-10-10T00:00:00Z", "created": "2020-01-01T00:00:00Z"}}

    stale = ef.evaluate(real, recorded, FakeGit(), FakeRegistry(released), only=["scan-proxy-worker"])[0]

    assert stale.state == "stale"
    assert any(package in r and "9.1.0" in r for r in stale.reasons)


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


def test_pypi_fetcher_returns_the_earliest_upload_time_per_version():
    body = json.dumps({
        "releases": {
            "1.0.0": [
                {"upload_time_iso_8601": "2026-01-01T12:00:00Z"},
                {"upload_time_iso_8601": "2026-01-01T00:00:00Z"},
            ],
            "0.9.0": [],
        }
    }).encode()
    seen = []

    def fake_open(url, timeout):
        seen.append(url)
        return body

    assert ef.fetch_pypi_times("anthropic", opener=fake_open) == {"1.0.0": "2026-01-01T00:00:00Z"}
    assert seen == ["https://pypi.org/pypi/anthropic/json"]


def test_pypi_fetcher_wraps_network_errors():
    def boom(url, timeout):
        raise OSError("no network")

    with pytest.raises(ef.RegistryError):
        ef.fetch_pypi_times("x", opener=boom)


def test_unknown_ecosystem_is_a_registry_error():
    with pytest.raises(ef.RegistryError):
        ef.fetch_publish_times("cobol", "x")


def test_cli_json_output_and_exit_code(tmp_path, capsys):
    status_file = tmp_path / "s.json"
    status_file.write_text(json.dumps(status_with(passed())))
    code = ef.main(
        ["--json", "--surface", "supabase-auth"],
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
        ["--json", "--surface", "supabase-auth"],
        git=FakeGit(),
        registry=FakeRegistry(QUIET_REGISTRY),
        status_file=tmp_path / "missing.json",
    )
    out = json.loads(capsys.readouterr().out)
    assert code == 1
    assert out["stale"] == ["supabase-auth"]


def test_revenuecat_rest_is_in_the_real_manifest_with_android_and_scan_proxy_chains():
    surface = ef.load_manifest()["surfaces"]["revenuecat-rest"]
    assert surface["status"] == "active"
    assert surface["max_paid_calls"] == 0
    assert "workers/scan-proxy/src/revenuecat.ts" in surface["boundary_files"]
    assert {"scan-proxy", "android"} <= set(surface["platforms"])


def test_anthropic_is_in_the_real_manifest_active_with_both_consumer_chains():
    surface = ef.load_manifest()["surfaces"]["anthropic"]
    assert surface["status"] == "active"
    assert surface["max_paid_calls"] == 3
    assert "workers/scan-proxy/src/claude.ts" in surface["boundary_files"]
    assert "src/hdttools/vision_client.py" in surface["boundary_files"]
    assert {"scan-proxy", "core"} <= set(surface["platforms"])
    assert {"npm", "pypi"} == {p["ecosystem"] for p in surface["registry_packages"]}


def test_pages_site_is_in_the_real_manifest_active_with_the_web_chain():
    surface = ef.load_manifest()["surfaces"]["pages-site"]
    assert surface["status"] == "active"
    assert surface["max_paid_calls"] == 0
    assert surface["platforms"] == ["web"]
    # The deploy config, the production env file the Supabase vars are baked from, and the shell it builds.
    assert {"web/wrangler.toml", "web/.env.production", "web/index.html"} <= set(surface["boundary_files"])
    assert {"web/package.json", "web/package-lock.json"} <= set(surface["dependency_pins"])
    assert {"ecosystem": "npm", "package": "wrangler"} in surface["registry_packages"]
    assert "pages-site" in ef.surfaces_for_platform(ef.load_manifest(), "web")


def test_supabase_tables_is_in_the_real_manifest_active_with_the_web_chain():
    surface = ef.load_manifest()["surfaces"]["supabase-tables"]
    assert surface["status"] == "active"
    assert surface["max_paid_calls"] == 0
    assert surface["platforms"] == ["web"]
    # The adapter that calls the table, and the migration that defines it: a change to either is a change to the surface.
    assert {"web/src/supabaseGarage.ts", "supabase/migrations/20261010000000_garage_rigs.sql"} <= set(surface["boundary_files"])
    assert {"ecosystem": "npm", "package": "@supabase/supabase-js"} in surface["registry_packages"]
    assert "supabase-tables" in ef.surfaces_for_platform(ef.load_manifest(), "web")


def test_revenuecat_web_billing_is_in_the_real_manifest_active_with_the_web_chain():
    surface = ef.load_manifest()["surfaces"]["revenuecat-web-billing"]
    assert surface["status"] == "active"
    # No real purchase: a sandbox purchase stays the human checklist in #11.
    assert surface["max_paid_calls"] == 0
    assert surface["platforms"] == ["web"]
    # The adapter over the SDK. billing.tsx (the React provider) is deliberately not a boundary file:
    # the live test does not exercise it, and provider edits would otherwise force a re-run.
    assert surface["boundary_files"] == ["web/src/revenueCatBilling.ts"]
    assert {"web/package.json", "web/package-lock.json"} <= set(surface["dependency_pins"])
    assert {"ecosystem": "npm", "package": "@revenuecat/purchases-js"} in surface["registry_packages"]
    assert "revenuecat-web-billing" in ef.surfaces_for_platform(ef.load_manifest(), "web")


@pytest.mark.parametrize("changed", ["web/src/revenueCatBilling.ts", "web/package.json", "web/package-lock.json"])
def test_changing_the_billing_adapter_or_the_sdk_pin_makes_revenuecat_web_billing_stale(changed):
    real = ef.load_manifest()
    recorded = status_with(passed(), name="revenuecat-web-billing")
    quiet = FakeRegistry({"@revenuecat/purchases-js": {"1.70.0": "2026-09-01T00:00:00Z", "created": "2020-01-01T00:00:00Z"}})

    fresh = ef.evaluate(real, recorded, FakeGit(), quiet, only=["revenuecat-web-billing"])[0]
    stale = ef.evaluate(real, recorded, FakeGit(changed=[changed]), quiet, only=["revenuecat-web-billing"])[0]

    assert fresh.state == "fresh"
    assert stale.state == "stale"
    assert any(changed in r for r in stale.reasons)


_REQUIRED_PROVIDER_SURFACES = {
    "scan-proxy-worker",
    "pages-site",
    "revenuecat-android-sdk",
    "google-play-billing",
    "revenuecat-web-billing",
    "supabase-tables",
    "worker-token-verification",
}


# Surfaces from the list above that have since gained a tagged External test and flipped to active.
_SURFACES_NOW_ACTIVE = {
    "pages-site",
    "supabase-tables",
    "revenuecat-web-billing",
    "worker-token-verification",
    "scan-proxy-worker",
}


def test_every_required_provider_surface_is_registered_in_the_real_manifest():
    surfaces = ef.load_manifest()["surfaces"]
    missing = _REQUIRED_PROVIDER_SURFACES - set(surfaces)
    assert not missing, f"missing manifest entries: {sorted(missing)}"


def test_surfaces_with_no_tagged_test_yet_are_planned_and_never_block():
    surfaces = ef.load_manifest()["surfaces"]
    for name in _REQUIRED_PROVIDER_SURFACES - _SURFACES_NOW_ACTIVE:
        assert surfaces[name]["status"] == "planned", f"{name} should be planned until it has a tagged test"


def test_every_real_manifest_entry_is_well_formed():
    manifest = ef.load_manifest()
    for name, surface in manifest["surfaces"].items():
        assert surface["name"] == name
        assert surface["status"] in {"active", "planned"}, f"{name}: unknown status {surface['status']!r}"

        platforms = surface.get("platforms")
        assert isinstance(platforms, list) and platforms, f"{name}: platforms must be a non-empty list"
        assert all(isinstance(p, str) and p for p in platforms), f"{name}: platform names must be non-empty strings"

        assert isinstance(surface.get("boundary_files"), list), f"{name}: boundary_files must be a list"
        assert isinstance(surface.get("dependency_pins"), list), f"{name}: dependency_pins must be a list"

        max_paid_calls = surface.get("max_paid_calls")
        assert isinstance(max_paid_calls, int) and max_paid_calls >= 0, f"{name}: max_paid_calls must be a non-negative int"

        for pkg in surface.get("registry_packages", []):
            assert set(pkg) == {"ecosystem", "package"}, f"{name}: registry_packages entries need exactly ecosystem and package"
            assert isinstance(pkg["ecosystem"], str) and pkg["ecosystem"], f"{name}: ecosystem must be a non-empty string"
            assert isinstance(pkg["package"], str) and pkg["package"], f"{name}: package must be a non-empty string"


# --- Maven fetchers (#54) ---------------------------------------------------

MAVEN_PKG = "com.revenuecat.purchases:purchases"
GOOGLE_PKG = "com.android.billingclient:billing"
CENTRAL_BASE = "https://repo1.maven.org/maven2/com/revenuecat/purchases/purchases"


def central_metadata(*versions):
    items = "".join(f"<version>{v}</version>" for v in versions)
    return f"<metadata><versioning><versions>{items}</versions></versioning></metadata>".encode()


class FakeCentral:
    """repo1.maven.org: the version list from maven-metadata.xml, publish times from each .pom's Last-Modified.

    Live finding (#54): Central's search API (search.maven.org) stops indexing releases and stalls on a
    share of requests, so it is not used; the repository files are the source of truth.
    """

    def __init__(self, released, listed=None):
        self.released = released  # version -> ISO time of its .pom
        self.listed = list(released) if listed is None else listed
        self.dated = []  # versions whose .pom time was asked for

    def open(self, url, timeout):
        assert url == f"{CENTRAL_BASE}/maven-metadata.xml", url
        return central_metadata(*self.listed)

    def last_modified(self, url, timeout):
        version = url.rsplit("/", 2)[1]
        assert url == f"{CENTRAL_BASE}/{version}/purchases-{version}.pom", url
        self.dated.append(version)
        return self.released[version]


def fetch_central(central, **kwargs):
    return ef.fetch_maven_times(MAVEN_PKG, opener=central.open, last_modified=central.last_modified, **kwargs)


def test_maven_fetcher_returns_the_publish_time_of_each_version():
    central = FakeCentral({"8.1.0": "2026-10-02T00:00:00+00:00", "8.0.0": "2026-10-01T00:00:00+00:00"})
    assert fetch_central(central) == {"8.1.0": "2026-10-02T00:00:00+00:00", "8.0.0": "2026-10-01T00:00:00+00:00"}


def test_maven_fetcher_dates_only_the_newest_stable_versions_and_skips_pre_releases():
    released = {f"8.{n}.0": f"2026-09-{n:02d}T00:00:00+00:00" for n in range(1, 16)}
    central = FakeCentral(released, listed=[*released, "9.0.0-beta01"])

    times = fetch_central(central)

    newest = [f"8.{n}.0" for n in range(6, 16)]
    assert sorted(times, key=ef._semver_key) == newest
    assert sorted(central.dated, key=ef._semver_key) == newest  # one request per dated version, none for the rest


def test_maven_fetcher_with_only_pre_releases_has_no_stable_versions():
    central = FakeCentral({}, listed=["1.0.0-beta01"])
    assert fetch_central(central) == {}


def test_maven_fetcher_wraps_network_errors():
    def boom(url, timeout):
        raise OSError("no network")

    with pytest.raises(ef.RegistryError):
        ef.fetch_maven_times(MAVEN_PKG, opener=boom)


def test_maven_fetcher_treats_an_unparseable_body_as_a_registry_error():
    with pytest.raises(ef.RegistryError):
        ef.fetch_maven_times(MAVEN_PKG, opener=lambda url, timeout: b"<html>rate limited</html>")


def test_maven_fetcher_treats_an_artifact_with_no_versions_as_a_registry_error_not_an_empty_release_list():
    # An artifact Central does not host (it may live on Google Maven) must not read as "no releases, fresh".
    with pytest.raises(ef.RegistryError):
        fetch_central(FakeCentral({}, listed=[]))


def test_maven_fetcher_treats_a_pom_it_cannot_date_as_a_registry_error():
    central = FakeCentral({"8.0.0": "2026-10-01T00:00:00+00:00"})

    def no_pom(url, timeout):
        raise OSError("404")

    with pytest.raises(ef.RegistryError):
        ef.fetch_maven_times(MAVEN_PKG, opener=central.open, last_modified=no_pom)


def test_default_last_modified_reads_the_header_of_a_head_request(monkeypatch):
    sent = []

    class FakeResponse:
        headers = {"Last-Modified": "Fri, 20 Jun 2025 08:47:08 GMT"}

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(request, timeout):
        sent.append(request)
        return FakeResponse()

    monkeypatch.setattr(ef.urllib.request, "urlopen", fake_urlopen)

    assert ef._default_last_modified("https://example.test/x.pom", 5) == "2025-06-20T08:47:08+00:00"
    assert sent[0].get_method() == "HEAD"


def test_default_last_modified_without_the_header_is_an_error(monkeypatch):
    class NoHeader:
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(ef.urllib.request, "urlopen", lambda request, timeout: NoHeader())

    with pytest.raises(ValueError):
        ef._default_last_modified("https://example.test/x.pom", 5)


@pytest.mark.parametrize("package", ["purchases", "a:b:c", ":purchases", "com.x:"])
def test_maven_fetchers_reject_a_package_that_is_not_group_colon_artifact(package):
    def never(url, timeout):
        raise AssertionError("no request should be made")

    with pytest.raises(ef.RegistryError):
        ef.fetch_maven_times(package, opener=never)
    with pytest.raises(ef.RegistryError):
        ef.fetch_google_maven_times(package, opener=never)


GOOGLE_METADATA = b"""<?xml version='1.0' encoding='UTF-8'?>
<metadata>
  <groupId>com.android.billingclient</groupId>
  <artifactId>billing</artifactId>
  <versioning>
    <latest>7.1.1</latest>
    <versions>
      <version>7.0.0</version>
      <version>7.1.0</version>
      <version>7.1.1</version>
      <version>8.0.0-rc01</version>
    </versions>
  </versioning>
</metadata>"""


def test_google_maven_fetcher_lists_versions_with_no_release_time():
    seen = []

    def fake_open(url, timeout):
        seen.append(url)
        return GOOGLE_METADATA

    assert ef.fetch_google_maven_times(GOOGLE_PKG, opener=fake_open) == {
        "7.0.0": None, "7.1.0": None, "7.1.1": None, "8.0.0-rc01": None,
    }
    assert seen == ["https://dl.google.com/dl/android/maven2/com/android/billingclient/billing/maven-metadata.xml"]


def test_google_maven_fetcher_wraps_network_errors():
    def boom(url, timeout):
        raise OSError("no network")

    with pytest.raises(ef.RegistryError):
        ef.fetch_google_maven_times(GOOGLE_PKG, opener=boom)


def test_google_maven_fetcher_treats_an_unparseable_body_as_a_registry_error():
    with pytest.raises(ef.RegistryError):
        ef.fetch_google_maven_times(GOOGLE_PKG, opener=lambda url, timeout: b"<html>not metadata")


def test_the_maven_ecosystems_are_registered_with_the_dispatcher():
    assert ef._FETCHERS["maven"] is ef.fetch_maven_times
    assert ef._FETCHERS["google-maven"] is ef.fetch_google_maven_times


def maven_surface(ecosystem="maven", package=MAVEN_PKG):
    return surface(name="android-lib", platforms=["android"], registry_packages=[{"ecosystem": ecosystem, "package": package}])


def test_a_maven_release_published_after_the_last_pass_makes_the_surface_stale():
    times = {MAVEN_PKG: {"8.0.0": "2026-09-01T00:00:00+00:00", "8.1.0": "2026-10-02T00:00:00+00:00"}}
    v = verdict(status_with(passed(), name="android-lib"), registry=FakeRegistry(times), m=manifest(maven_surface()))
    assert v.state == "stale"
    assert any("8.1.0" in r for r in v.reasons)
    assert v.versions == {MAVEN_PKG: "8.1.0"}


def test_a_maven_pre_release_published_after_the_last_pass_is_ignored():
    times = {MAVEN_PKG: {"8.0.0": "2026-09-01T00:00:00+00:00", "9.0.0-beta01": "2026-10-02T00:00:00+00:00"}}
    v = verdict(status_with(passed(), name="android-lib"), registry=FakeRegistry(times), m=manifest(maven_surface()))
    assert v.state == "fresh"


def undated_verdict(listed, status_entry):
    registry = FakeRegistry({GOOGLE_PKG: {v: None for v in listed}})
    m = manifest(maven_surface("google-maven", GOOGLE_PKG))
    return verdict(status_with(status_entry, name="android-lib"), registry=registry, m=m)


def test_undated_registry_is_fresh_while_the_latest_stable_version_is_the_one_recorded_at_the_pass():
    v = undated_verdict(["7.0.0", "7.1.1"], passed(versions={GOOGLE_PKG: "7.1.1"}))
    assert v.state == "fresh"
    assert v.versions == {GOOGLE_PKG: "7.1.1"}


def test_undated_registry_is_stale_on_any_change_of_the_latest_stable_version_and_says_why():
    v = undated_verdict(["7.1.1", "7.1.2"], passed(versions={GOOGLE_PKG: "7.1.1"}))
    assert v.state == "stale"
    reason = next(r for r in v.reasons if GOOGLE_PKG in r)
    assert "no per-version release dates" in reason
    assert "7.1.1" in reason and "7.1.2" in reason


def test_undated_registry_is_stale_when_the_pass_recorded_no_version_for_the_package():
    v = undated_verdict(["7.1.1"], passed())
    assert v.state == "stale"
    assert any("no per-version release dates" in r for r in v.reasons)


def test_undated_registry_ignores_pre_release_versions():
    v = undated_verdict(["7.1.1", "8.0.0-rc01"], passed(versions={GOOGLE_PKG: "7.1.1"}))
    assert v.state == "fresh"


def test_undated_registry_does_not_make_a_never_passed_surface_any_less_stale():
    v = undated_verdict(["7.1.1"], {})
    assert v.state == "stale"
    assert any("never passed" in r for r in v.reasons)
    assert v.versions == {GOOGLE_PKG: "7.1.1"}


def test_an_unreachable_undated_registry_is_stale():
    v = verdict(
        status_with(passed(versions={GOOGLE_PKG: "7.1.1"}), name="android-lib"),
        registry=FakeRegistry(down=True),
        m=manifest(maven_surface("google-maven", GOOGLE_PKG)),
    )
    assert v.state == "stale"
    assert any("registry" in r for r in v.reasons)


def test_the_real_manifest_names_the_registry_that_hosts_each_android_library():
    packages = {
        (p["ecosystem"], p["package"])
        for name in ("google-play-billing", "revenuecat-android-sdk")
        for p in ef.load_manifest()["surfaces"][name]["registry_packages"]
    }
    # Billing is published on Google Maven only; RevenueCat's SDK is on Maven Central.
    assert packages == {("google-maven", GOOGLE_PKG), ("maven", MAVEN_PKG)}
