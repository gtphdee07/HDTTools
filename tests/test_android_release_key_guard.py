"""The Android release build refuses the RevenueCat Test Store key (#166).

A key starting with `test_` makes purchases fake, so a release carrying it would sell nothing and
grant entitlements for free. `verifyRevenueCatReleaseKey` in `android/app/build.gradle.kts` is the
guard; it runs alone here (no release build), so these checks are offline and need no device. The
ones that start Gradle are `slow` (the planner owes them when `android/app/build.gradle.kts`
changes) and share the `gradle` xdist worker with the other Gradle checks.
"""

from __future__ import annotations

import os
import re

import pytest

from tests._test_command_helpers import ANDROID, gradle, gradle_proc, read

pytestmark = [pytest.mark.core]


def gradle_check(test):
    """The checks that start Gradle: `slow`, and on the one xdist worker the other Gradle checks share."""
    return pytest.mark.slow(pytest.mark.xdist_group("gradle")(test))


GUARD = ":app:verifyRevenueCatReleaseKey"
RELEASE_KEY_ENV = "REVENUECAT_RELEASE_API_KEY"
TEST_STORE_KEY = "test_LFhGCYRgSfTFUpYRaWkEakLWOdS"


def _env(key: str | None = None) -> dict[str, str]:
    """This process's environment with the release-key variable removed, or set to `key`."""
    env = {k: v for k, v in os.environ.items() if k != RELEASE_KEY_ENV}
    if key is not None:
        env[RELEASE_KEY_ENV] = key
    return env


def _guard(*args: str, env_key: str | None = None):
    return gradle_proc(GUARD, *args, env=_env(env_key))


@pytest.mark.minor
def test_application_reads_its_key_from_build_config_and_holds_no_literal():
    source = read(ANDROID / "app/src/main/java/com/rigcheck/app/RigCheckApplication.kt")
    assert "BuildConfig.REVENUECAT_PUBLIC_API_KEY" in source
    assert re.findall(r'"(?:test|goog|appl|amzn|rcb|sk)_[A-Za-z0-9]+"', source) == []


@gradle_check
@pytest.mark.parametrize("args, message", [
    pytest.param([], "key is missing", id="no-key"),
    pytest.param(["-PrevenueCatReleaseKey="], "key is missing", id="empty-key"),
    pytest.param(["-PrevenueCatReleaseKey=test_abc123"], "starts with test_", id="test-store-key"),
    pytest.param(["-PrevenueCatReleaseKey=TEST_abc123"], "starts with test_", id="upper-case-test-store-key"),
    pytest.param(["-PrevenueCatReleaseKey=  test_abc123"], "starts with test_", id="padded-test-store-key"),
])
def test_guard_refuses_a_missing_empty_or_test_store_key(args, message):
    proc = _guard(*args)
    assert proc.returncode != 0
    assert "RevenueCat release API key" in proc.stderr and message in proc.stderr


@gradle_check
def test_guard_refuses_a_test_store_key_from_the_environment_too():
    proc = _guard(env_key=TEST_STORE_KEY)
    assert proc.returncode != 0 and "starts with test_" in proc.stderr
    assert TEST_STORE_KEY not in proc.stdout + proc.stderr  # the message names the key, never prints it


@gradle_check
@pytest.mark.parametrize("args, env_key", [
    pytest.param(["-PrevenueCatReleaseKey=goog_abc123"], None, id="gradle-property"),
    pytest.param([], "goog_abc123", id="environment-variable"),
])
def test_guard_accepts_a_production_key(args, env_key):
    proc = _guard(*args, env_key=env_key)
    assert proc.returncode == 0, proc.stderr[-800:]


def _release_task_order(*tasks: str) -> list[str]:
    # A dry run lists tasks in execution order. The release variant's dependencies are only
    # resolvable online, hence no configuration cache (it resolves them while storing the cache).
    out = gradle(*tasks, "--dry-run", "--no-configuration-cache")
    return re.findall(r"^(:\S+) SKIPPED", out, flags=re.MULTILINE)


@gradle_check
@pytest.mark.parametrize("task", ["assembleRelease", "bundleRelease", "packageRelease", "packageReleaseBundle"])
def test_release_artifact_tasks_run_the_guard_first(task):
    order = _release_task_order(task)
    assert order[0] == GUARD, order[:5]


@gradle_check
@pytest.mark.parametrize("tasks", [["assembleDebug"], ["test"]])
def test_debug_builds_and_unit_tests_do_not_need_a_release_key(tasks):
    assert GUARD not in _release_task_order(*tasks)


def _build_config_key(variant: str) -> str:
    path = ANDROID / f"app/build/generated/source/buildConfig/{variant}/com/rigcheck/app/BuildConfig.java"
    return re.search(r'REVENUECAT_PUBLIC_API_KEY = "([^"]*)"', read(path)).group(1)


@gradle_check
def test_debug_uses_the_test_store_key_and_release_takes_its_own_with_no_default():
    gradle("generateDebugBuildConfig", "generateReleaseBuildConfig", "-PrevenueCatReleaseKey=goog_abc123")
    assert _build_config_key("debug") == TEST_STORE_KEY
    assert _build_config_key("release") == "goog_abc123"
    # No key given: release gets an empty one (which the guard then refuses), never the Test Store key.
    proc = gradle_proc("generateReleaseBuildConfig", env=_env())
    assert proc.returncode == 0, proc.stderr[-800:]
    assert _build_config_key("release") == ""
