"""The Android beta build type (#174): signed with the owner's upload key, allowed the Test Store key.

`beta` sits between `debug` and `release` in `android/app/build.gradle.kts`: same package name, not
debuggable, signed from three settings that live outside the repo, and the only non-debug type that
may carry the RevenueCat Test Store key. `verifyBetaSigning` is the guard for the settings; like the
release guard (#166) it runs alone here, so most checks are offline and need no device. One check
packages a real beta APK with a throwaway keystore (never the owner's). The Gradle checks are `slow`
(the planner owes them when `android/app/build.gradle.kts` changes) and share the `gradle` xdist worker.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
from pathlib import Path

import pytest

from tests._test_command_helpers import ANDROID, ROOT, gradle, gradle_proc, read

pytestmark = [pytest.mark.core]


def gradle_check(test):
    """The checks that start Gradle: `slow`, and on the one xdist worker the other Gradle checks share."""
    return pytest.mark.slow(pytest.mark.xdist_group("gradle")(test))


GUARD = ":app:verifyBetaSigning"
SETTINGS = {  # Gradle property -> environment variable
    "betaKeystoreFile": "BETA_KEYSTORE_FILE",
    "betaKeyAlias": "BETA_KEY_ALIAS",
    "betaKeystorePassword": "BETA_KEYSTORE_PASSWORD",
}
TEST_STORE_KEY = "test_LFhGCYRgSfTFUpYRaWkEakLWOdS"
BETA_TASKS = ["assembleBeta", "bundleBeta", "packageBeta", "packageBetaBundle"]


def _env() -> dict[str, str]:
    """This process's environment without the beta signing variables."""
    return {k: v for k, v in os.environ.items() if k not in SETTINGS.values()}


def _settings_args(**values: str) -> list[str]:
    """`-P` arguments for the three settings. A command-line property beats the owner's user-level
    gradle.properties, so these checks give the same result on a machine that has the real values."""
    return [f"-P{name}={values.get(name, 'sentinel-' + name)}" for name in SETTINGS]


@pytest.mark.minor
def test_no_keystore_path_alias_or_password_literal_in_the_android_project():
    build = read(ANDROID / "app/build.gradle.kts")
    assigned = re.findall(r'\b(?:storeFile|keyAlias|storePassword|keyPassword)\s*=\s*(?:file\()?"', build)
    assert assigned == []  # they come from the settings, never a literal
    tracked = subprocess.run(["git", "ls-files", "--", "android"], cwd=ROOT, capture_output=True, text=True, check=True)
    for name in tracked.stdout.split():
        path = ROOT / name
        if path.suffix in {".kts", ".gradle", ".properties", ".toml", ".kt", ".xml", ".md", ".ps1", ".json"}:
            text = read(path)
            assert not re.search(r"Secrets[\\/]|\.jks\b", text), name


@gradle_check
@pytest.mark.parametrize("missing", list(SETTINGS))
@pytest.mark.parametrize("how", ["blank", "padded"])
def test_guard_refuses_a_missing_or_blank_setting_and_names_it_without_printing_values(missing, how):
    blank = "" if how == "blank" else "   "
    proc = gradle_proc(GUARD, *_settings_args(**{missing: blank}), env=_env())
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert "beta signing settings are missing" in proc.stderr and missing in proc.stderr
    assert not any(f"sentinel-{name}" in out for name in SETTINGS)  # no value is ever printed
    assert all(name not in proc.stderr for name in SETTINGS if name != missing)  # only the missing one is named


@gradle_check
def test_guard_refuses_when_nothing_is_set_and_accepts_all_three():
    proc = gradle_proc(GUARD, *_settings_args(**{name: "" for name in SETTINGS}), env=_env())
    assert proc.returncode != 0 and all(name in proc.stderr for name in SETTINGS)
    ok = gradle_proc(GUARD, *_settings_args(), env=_env())
    assert ok.returncode == 0, ok.stderr[-800:]


@gradle_check
def test_guard_accepts_the_three_environment_variables():
    user_home = Path(os.environ.get("GRADLE_USER_HOME") or Path.home() / ".gradle")
    user_properties = (user_home / "gradle.properties")
    if user_properties.is_file() and any(name in read(user_properties) for name in SETTINGS):
        pytest.skip("the user-level gradle.properties holds beta settings, which beat the variables")
    env = _env() | {variable: f"env-{variable}" for variable in SETTINGS.values()}
    proc = gradle_proc(GUARD, env=env)
    assert proc.returncode == 0, proc.stderr[-800:]
    assert not any(f"env-{variable}" in proc.stdout + proc.stderr for variable in SETTINGS.values())


def _task_order(*tasks: str) -> list[str]:
    # A dry run lists tasks in execution order; the beta variant's dependencies are only resolvable
    # online, hence no configuration cache (it resolves them while storing the cache).
    out = gradle(*tasks, "--dry-run", "--no-configuration-cache")
    return re.findall(r"^(:\S+) SKIPPED", out, flags=re.MULTILINE)


@gradle_check
@pytest.mark.parametrize("task", BETA_TASKS)
def test_beta_artifact_tasks_run_the_signing_guard_first(task):
    order = _task_order(task)
    assert order[0] == GUARD, order[:5]


@gradle_check
@pytest.mark.parametrize("tasks", [["assembleDebug"], ["assembleRelease", "-PrevenueCatReleaseKey=goog_abc123"], ["test"]])
def test_other_builds_and_unit_tests_do_not_need_the_beta_signing_settings(tasks):
    order = _task_order(*tasks)
    assert GUARD not in order
    assert not any("Beta" in task for task in order), order  # beta has no unit-test variant of its own


def _build_config(variant: str) -> str:
    return read(ANDROID / f"app/build/generated/source/buildConfig/{variant}/com/rigcheck/app/BuildConfig.java")


def _revenuecat_key(variant: str) -> str:
    return re.search(r'REVENUECAT_PUBLIC_API_KEY = "([^"]*)"', _build_config(variant)).group(1)


def _beta_flag(variant: str) -> str:
    return re.search(r"boolean IS_BETA = (\w+);", _build_config(variant)).group(1)


@gradle_check
def test_test_store_key_is_allowed_only_in_debug_and_beta_and_the_beta_flag_is_beta_only():
    gradle("generateDebugBuildConfig", "generateBetaBuildConfig", "generateReleaseBuildConfig", "-PrevenueCatReleaseKey=goog_abc123")
    keys = [_revenuecat_key(variant) for variant in ("debug", "beta", "release")]
    assert keys == [TEST_STORE_KEY, TEST_STORE_KEY, "goog_abc123"]
    assert [_beta_flag(variant) for variant in ("debug", "beta", "release")] == ["false", "true", "false"]
    # No release key given: release still never falls back to the Test Store key.
    proc = gradle_proc("generateReleaseBuildConfig", env={k: v for k, v in os.environ.items() if k != "REVENUECAT_RELEASE_API_KEY"})
    assert proc.returncode == 0, proc.stderr[-800:]
    assert TEST_STORE_KEY not in _build_config("release")


def _keytool() -> str:
    java_home = os.environ.get("JAVA_HOME")
    found = shutil.which("keytool") or (java_home and shutil.which("keytool", path=str(Path(java_home) / "bin")))
    if not found:
        pytest.skip("keytool (JDK) is not installed")
    return found


def _sha1(*keytool_args: str) -> str:
    proc = subprocess.run([_keytool(), *keytool_args], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return re.search(r"SHA1:\s*([0-9A-F:]+)", proc.stdout).group(1)


@gradle_check
def test_beta_apk_is_signed_with_the_given_keystore_and_is_the_release_package_not_debuggable(tmp_path):
    password = secrets.token_hex(8)
    keystore = tmp_path / "throwaway.p12"
    made = subprocess.run(
        [_keytool(), "-genkeypair", "-keystore", str(keystore), "-storetype", "PKCS12", "-alias", "throwaway",
         "-keyalg", "RSA", "-keysize", "2048", "-validity", "2", "-storepass", password, "-dname", "CN=throwaway"],
        capture_output=True, text=True, timeout=120,
    )
    assert made.returncode == 0, made.stdout + made.stderr
    proc = gradle_proc(
        "assembleBeta", "-PappVersionCode=7",
        *_settings_args(betaKeystoreFile=str(keystore), betaKeyAlias="throwaway", betaKeystorePassword=password),
        env=_env(), timeout=900,
    )
    if proc.returncode != 0 and "No cached version" in proc.stderr:
        pytest.skip("the beta dependencies are not in the offline Gradle cache; build assembleBeta once online")
    assert proc.returncode == 0, proc.stderr[-800:]
    assert password not in proc.stdout + proc.stderr

    out = ANDROID / "app/build/outputs/apk/beta"
    # keytool -printcert -jarfile is the check the owner runs on the real APK: it reads the v1 signature.
    assert _sha1("-printcert", "-jarfile", str(out / "app-beta.apk")) == _sha1(
        "-list", "-v", "-keystore", str(keystore), "-storepass", password
    )
    element = json.loads(read(out / "output-metadata.json"))
    assert element["applicationId"] == "com.rigcheck.app"
    assert (element["elements"][0]["versionCode"], element["elements"][0]["versionName"]) == (7, "1.0-beta")
    manifests = list((ANDROID / "app/build/intermediates").glob("merged_manifest*/beta/**/AndroidManifest.xml"))
    assert manifests and not any('android:debuggable="true"' in read(m) for m in manifests)
    assert "boolean DEBUG = false" in _build_config("beta")
