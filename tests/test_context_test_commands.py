"""Command checks for #52: each of Web, Scan Proxy and Android has one
documented file-level command and one context-level command, and neither
selects a live-provider test or needs a device.

Tagged `core` because `tests/TESTING.md` files the `scripts/` and tooling
checks under Core, even though these look at other contexts. Web and Scan Proxy
commands are run for real (their offline suites take seconds); Android asks
Gradle for a dry-run task graph, since compiling Kotlin is too slow for the
default run. The real Android file-command run is in
`test_android_file_command_slow.py`. The commands under test are the ones
written in each context's TESTING.md and in `scripts/test_planner_config.json`;
the checks below fail if either drifts from the constants here.
"""

from __future__ import annotations

import json
import re

import pytest

from tests._test_command_helpers import (
    ANDROID,
    ANDROID_CLASS,
    ANDROID_CONTEXT_CMD,
    ANDROID_FILE_CMD,
    PROXY,
    PROXY_CONTEXT_CMD,
    PROXY_FILE,
    PROXY_FILE_CMD,
    ROOT,
    WEB,
    WEB_CONTEXT_CMD,
    WEB_FILE,
    WEB_FILE_CMD,
    gradle,
    npm_script,
    read,
    relative,
    run,
    tool,
)

pytestmark = [pytest.mark.core, pytest.mark.minor]


# ---------------------------------------------------------------- Web


def _vitest_json(output: str) -> dict | list:
    """Vitest's CLI can print a banner before the JSON; find where the JSON actually starts."""
    brace, bracket = output.find("{"), output.find("[")
    start = min(i for i in (brace, bracket) if i >= 0)
    return json.JSONDecoder().raw_decode(output[start:])[0]


def _web_listed(*args: str) -> list[str]:
    # `--json` must come last: vitest reads a following argument as the output file and would overwrite it.
    out = run([tool("npx"), "vitest", "list", *args, "--filesOnly", "--json"], WEB)
    return sorted(relative(entry["file"], WEB) for entry in _vitest_json(out))


def test_web_file_command_selects_only_that_file():
    assert npm_script(WEB, "test") == "vitest run"
    assert _web_listed(WEB_FILE) == [WEB_FILE]


def test_web_file_command_runs_that_file_and_nothing_else():
    out = run([tool("npm"), "test", "--silent", "--", "--reporter=json", WEB_FILE], WEB)
    report = _vitest_json(out)
    assert [relative(r["name"], WEB) for r in report["testResults"]] == [WEB_FILE]
    assert report["numTotalTests"] > 0 and report["numFailedTests"] == 0


def test_web_context_command_selects_every_offline_file_and_no_live_one():
    selected = _web_listed()
    on_disk_live = sorted(p.relative_to(WEB).as_posix() for p in (WEB / "src").rglob("*.external.test.ts"))
    assert on_disk_live, "no live Web test on disk, so the exclusion below proves nothing"
    assert not set(selected) & set(on_disk_live)
    assert WEB_FILE in selected
    # Offline files that live under src/external/ on purpose (config and guard checks, no provider call).
    assert {"src/external/config.test.ts", "src/external/externalGuards.test.ts"} <= set(selected)


# ---------------------------------------------------------------- Scan Proxy


def _proxy_junit_files(output: str) -> list[str]:
    return sorted({relative(f, PROXY) for f in re.findall(r' file="([^"]+)"', output)})


def _proxy_run(*targets: str) -> list[str]:
    """Run node --test directly against explicit targets (the file-level check)."""
    out = run([tool("node"), "--test", "--test-reporter=junit", *targets], PROXY)
    return _proxy_junit_files(out)


def _node_test_summary(output: str) -> dict[str, int]:
    """Parse the default spec reporter's trailing summary counts ("tests 57", "pass 57", ...).
    Matched without the leading icon character, which doesn't always survive a Windows
    console code-page round trip through subprocess's text decoding."""
    return {k: int(v) for k, v in re.findall(r"(tests|pass|fail) (\d+)$", output, flags=re.MULTILINE)}


def test_proxy_test_script_has_no_pretest_or_posttest_hook():
    scripts = json.loads(read(PROXY / "package.json"))["scripts"]
    assert "pretest" not in scripts and "posttest" not in scripts


def test_proxy_context_command_runs_every_top_level_test_file_and_no_other():
    # `node --test` only accepts a reporter flag *before* the file list, so appending one to
    # npm's own script args (after `--`) never reaches it — the real `npm test` run below has
    # to be read through Node's default reporter's summary counts instead of per-file junit.
    glob = npm_script(PROXY, "test").removeprefix("node --test ")
    # Non-recursive: structurally cannot match src/external|release|weekly/*, so no live or old
    # paid suite can be selected by this script, whatever file count it reaches today.
    assert glob == "src/*.test.ts"
    for live_dir in ("external", "release", "weekly"):
        assert list((PROXY / "src" / live_dir).glob("*.ts")), f"{live_dir}/ is empty, so the exclusion proves nothing"

    top_level = sorted(p.relative_to(PROXY).as_posix() for p in (PROXY / "src").glob("*.test.ts"))
    assert top_level, "no top-level test file on disk, so the count check below proves nothing"
    per_file_counts = {f: _node_test_summary(run([tool("node"), "--test", f], PROXY))["tests"] for f in top_level}
    assert all(count > 0 for count in per_file_counts.values())

    summary = _node_test_summary(run([tool("npm"), "test"], PROXY))
    assert summary["fail"] == 0
    # The real `npm test` run selects exactly as many tests as the top-level files sum to —
    # neither fewer (a file silently dropped) nor more (an extra file silently picked up).
    assert summary["tests"] == sum(per_file_counts.values())


def test_proxy_file_command_runs_that_file_and_nothing_else():
    assert PROXY_FILE_CMD.split() == ["node", "--test", PROXY_FILE]
    assert _proxy_run(PROXY_FILE) == [PROXY_FILE]


# ---------------------------------------------------------------- Android


def _gradle_tasks(*args: str) -> set[str]:
    return set(re.findall(r"^(:\S+) SKIPPED", gradle(*args, "--dry-run"), flags=re.MULTILINE))


def test_android_context_command_graph_has_no_device_task():
    unit = _gradle_tasks("testDebugUnitTest")
    assert ":app:testDebugUnitTest" in unit
    # Device-only = what the instrumented run needs beyond merely building the app and its test APK.
    device_only = (
        _gradle_tasks("connectedDebugAndroidTest")
        - _gradle_tasks("assembleDebug")
        - _gradle_tasks("assembleDebugAndroidTest")
    )
    assert ":app:connectedDebugAndroidTest" in device_only
    assert unit & device_only == set()


def test_android_file_command_names_a_class_in_the_jvm_source_set():
    package, _, name = ANDROID_CLASS.rpartition(".")
    source = ANDROID / "app/src/test/java" / (ANDROID_CLASS.replace(".", "/") + ".kt")
    assert source.is_file()
    assert re.search(rf"^package {re.escape(package)}$", read(source), flags=re.MULTILINE)
    assert re.search(rf"\bclass {name}\b", read(source))


# ---------------------------------------------------------------- Docs


@pytest.mark.parametrize("doc, commands", [
    (WEB / "TESTING.md", [WEB_FILE_CMD, WEB_CONTEXT_CMD]),
    (PROXY / "TESTING.md", [PROXY_FILE_CMD, PROXY_CONTEXT_CMD]),
    (ANDROID / "TESTING.md", [ANDROID_FILE_CMD, ANDROID_CONTEXT_CMD]),
])
def test_each_contexts_testing_doc_lists_its_commands(doc, commands):
    text = read(doc)
    assert [c for c in commands if f"`{c}`" not in text] == []


# ---------------------------------------------------------------- Planner config drift (#52)
#
# scripts/test_planner_config.json repeats these commands for the advisory planner (#60/#61).
# These checks fail if it drifts from what's actually documented and tested above, rather than
# relying on someone noticing by hand.


def _planner_contexts() -> dict:
    return json.loads(read(ROOT / "scripts" / "test_planner_config.json"))["contexts"]


def test_planner_config_web_commands_match_the_documented_ones():
    web = _planner_contexts()["web"]
    assert web["context"] == f"npm --prefix web {WEB_CONTEXT_CMD.removeprefix('npm ')}"
    assert web["file"] == f"npm --prefix web {WEB_FILE_CMD.removeprefix('npm ').replace(WEB_FILE, '{rel}')}"


def test_planner_config_proxy_commands_match_the_documented_ones():
    proxy = _planner_contexts()["scan-proxy"]
    assert proxy["context"] == f"npm --prefix workers/scan-proxy {PROXY_CONTEXT_CMD.removeprefix('npm ')}"
    assert proxy["file"] == PROXY_FILE_CMD.replace(PROXY_FILE, "workers/scan-proxy/{rel}")


def test_planner_config_android_commands_match_the_documented_one_everywhere():
    android = _planner_contexts()["android"]
    expected_context = ANDROID_CONTEXT_CMD.replace("./gradlew", "android/gradlew -p android")
    expected_file = ANDROID_FILE_CMD.replace("./gradlew", "android/gradlew -p android").replace(ANDROID_CLASS, "{fqcn}")
    assert android["context"] == expected_context
    assert android["file"] == expected_file
    # The release-level "JVM tests" step and commands.minor/major must run the same JVM-only
    # command, not Gradle's plain `test` (which also builds and tests the release variant).
    assert android["commands"]["minor"] == expected_context
    assert android["commands"]["major"] == expected_context
    assert android["release"][0]["command"] == expected_context
