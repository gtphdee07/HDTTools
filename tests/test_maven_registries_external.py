"""Opt-in live guard for the Maven fetchers in scripts/external_freshness.py (#54).

The fake-response tests in test_external_freshness.py prove the logic, but only against the
response shapes we assumed. This file asks the real registries, so a registry that stops
telling the truth (the first design read Maven Central's search API, which had no release after
June 2025 and stalled on many requests) fails here instead of silently marking a surface fresh.

Free and read-only (plain GETs and HEADs, no key, no billed call), but it needs the network and
reaches third-party servers, so it carries `external` and a default run deselects it:

    uv run pytest -m external tests/test_maven_registries_external.py

Run it with the bundled External round or when the Maven fetchers change. A registry that cannot
be reached fails the run rather than skipping, as ADR-0008 requires of every External test.
"""

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# No `core` marker on purpose: `-m core` replaces the default `-m "not external"`, so it would reach the network.
pytestmark = [pytest.mark.external]

_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "external_freshness.py"
_spec = importlib.util.spec_from_file_location("external_freshness_live", _SCRIPT_PATH)
ef = importlib.util.module_from_spec(_spec)
sys.modules["external_freshness_live"] = ef
_spec.loader.exec_module(ef)

CENTRAL_PKG = "com.revenuecat.purchases:purchases"
GOOGLE_PKG = "com.android.billingclient:billing"
# RevenueCat ships roughly monthly. A source that stopped listing new releases (the search API was
# 16 months behind) is far outside this window; a year of silence from the vendor is worth a look too.
MAX_AGE_OF_NEWEST_RELEASE = timedelta(days=365)


class NoChanges:
    def changed_since(self, sha, paths):
        return []


def _newest(times):
    stable = ef._stable_versions(times)
    return max(stable, key=ef._semver_key)


def test_maven_central_lists_a_recent_release_with_a_real_publish_time():
    times = ef.fetch_maven_times(CENTRAL_PKG)

    assert times, "Maven Central returned no stable versions of purchases"
    assert all(t is not None for t in times.values())
    newest = _newest(times)
    published = ef._parse(times[newest])
    now = datetime.now(timezone.utc)
    assert published <= now + timedelta(days=1), f"{newest} is dated in the future: {published}"
    assert now - published <= MAX_AGE_OF_NEWEST_RELEASE, (
        f"newest stable purchases release {newest} is dated {published:%Y-%m-%d}: "
        "either the vendor stopped publishing or the source stopped listing new releases"
    )


def test_google_maven_lists_billing_versions_with_no_dates_so_the_fallback_applies():
    times = ef.fetch_google_maven_times(GOOGLE_PKG)

    stable = ef._stable_versions(times)
    assert stable, "Google Maven returned no stable versions of billing"
    assert all(t is None for t in times.values()), "Google Maven now dates versions: the fallback may be removable"
    assert ef._semver_key(max(stable, key=ef._semver_key)) >= (7, 0, 0), "the billing version list looks truncated"


def test_an_artifact_that_is_only_on_google_maven_is_not_found_on_maven_central():
    with pytest.raises(ef.RegistryError):
        ef.fetch_maven_times(GOOGLE_PKG)


def _surface(package_entry):
    return {
        "name": "live-guard",
        "status": "active",
        "platforms": ["android"],
        "boundary_files": [],
        "dependency_pins": [],
        "registry_packages": [package_entry],
        "max_paid_calls": 0,
    }


def _passed(timestamp, versions=None):
    return {"surfaces": {"live-guard": {
        "result": "pass", "passed": True, "timestamp": timestamp, "commit": "abc123", "versions": versions or {},
    }}}


def _evaluate(package_entry, status):
    manifest = {"surfaces": {"live-guard": _surface(package_entry)}}
    return ef.evaluate(manifest, status, NoChanges(), ef.fetch_publish_times)[0]


def test_a_pass_older_than_the_latest_central_release_makes_a_surface_stale_and_a_newer_one_does_not():
    entry = {"ecosystem": "maven", "package": CENTRAL_PKG}

    old = _evaluate(entry, _passed("2020-01-01T00:00:00Z"))
    new = _evaluate(entry, _passed("2999-01-01T00:00:00Z"))

    assert old.state == "stale" and any(CENTRAL_PKG in r for r in old.reasons)
    assert new.state == "fresh" and CENTRAL_PKG in new.versions


def test_google_maven_surface_is_stale_on_a_version_change_and_fresh_on_the_recorded_version():
    entry = {"ecosystem": "google-maven", "package": GOOGLE_PKG}
    latest = _evaluate(entry, {}).versions[GOOGLE_PKG]

    changed = _evaluate(entry, _passed("2026-01-01T00:00:00Z", {GOOGLE_PKG: "0.0.1"}))
    same = _evaluate(entry, _passed("2026-01-01T00:00:00Z", {GOOGLE_PKG: latest}))

    assert changed.state == "stale" and any("no per-version release dates" in r for r in changed.reasons)
    assert same.state == "fresh"
