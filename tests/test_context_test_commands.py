"""Command checks for #52: each of Web, Scan Proxy and Android has one
documented file-level command and one context-level command, and neither
selects a live-provider test or needs a device.

Tagged `core` because `tests/TESTING.md` files the `scripts/` and tooling
checks under Core, even though these look at other contexts. Web and Scan Proxy
commands are run for real (their offline suites take seconds); Android asks
Gradle for a dry-run task graph, since compiling Kotlin is too slow for the
default run. The real Android file-command run is in
`test_android_file_command_slow.py`. The commands under test are the ones
written in each context's TESTING.md; the docs check fails if they drift.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
PROXY = ROOT / "workers" / "scan-proxy"
ANDROID = ROOT / "android"

WEB_FILE = "src/breakdown.test.ts"
PROXY_FILE = "src/docTypes.test.ts"
ANDROID_CLASS = "com.rigcheck.app.domain.BreakdownTest"

WEB_FILE_CMD = f"npm test -- {WEB_FILE}"
WEB_CONTEXT_CMD = "npm test"
PROXY_FILE_CMD = f"node --test {PROXY_FILE}"
PROXY_CONTEXT_CMD = "npm test"
ANDROID_FILE_CMD = f"./gradlew testDebugUnitTest --tests {ANDROID_CLASS}"
ANDROID_CONTEXT_CMD = "./gradlew testDebugUnitTest"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _npm_script(package_dir: Path, name: str) -> str:
    return json.loads(_read(package_dir / "package.json"))["scripts"][name]


def _tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        pytest.skip(f"{name} (Node) is not installed")
    return path


def _run(cmd: list[str], cwd: Path, timeout: int = 180) -> str:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    assert proc.returncode == 0, f"{' '.join(cmd)} exited {proc.returncode}:\n{proc.stdout[-800:]}\n{proc.stderr[-800:]}"
    return proc.stdout


def _relative(file: str, base: Path) -> str:
    return Path(file).resolve().relative_to(base).as_posix()


# ---------------------------------------------------------------- Web


def _vitest_json(output: str) -> dict | list:
    return json.JSONDecoder().raw_decode(output[min(i for i in (output.find("{"), output.find("[")) if i >= 0):])[0]


def _web_listed(*args: str) -> list[str]:
    # `--json` must come last: vitest reads a following argument as the output file and would overwrite it.
    out = _run([_tool("npx"), "vitest", "list", *args, "--filesOnly", "--json"], WEB)
    return sorted(_relative(entry["file"], WEB) for entry in _vitest_json(out))


def test_web_file_command_selects_only_that_file():
    assert _npm_script(WEB, "test") == "vitest run"
    assert _web_listed(WEB_FILE) == [WEB_FILE]


def test_web_file_command_runs_that_file_and_nothing_else():
    out = _run([_tool("npm"), "test", "--silent", "--", "--reporter=json", WEB_FILE], WEB)
    report = _vitest_json(out)
    assert [_relative(r["name"], WEB) for r in report["testResults"]] == [WEB_FILE]
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


def _proxy_run(*targets: str) -> list[str]:
    """Run node --test with the junit reporter and return the test files that ran."""
    out = _run([_tool("node"), "--test", "--test-reporter=junit", *targets], PROXY)
    return sorted({_relative(f, PROXY) for f in re.findall(r' file="([^"]+)"', out)})


def _proxy_context_targets() -> list[str]:
    script = _npm_script(PROXY, "test")
    assert script.startswith("node --test "), script
    return script.removeprefix("node --test ").split()


def test_proxy_test_script_has_no_pretest_or_posttest_hook():
    scripts = json.loads(_read(PROXY / "package.json"))["scripts"]
    assert "pretest" not in scripts and "posttest" not in scripts


def test_proxy_context_command_runs_every_top_level_test_file_and_no_other():
    ran = _proxy_run(*_proxy_context_targets())
    top_level = sorted(p.relative_to(PROXY).as_posix() for p in (PROXY / "src").glob("*.test.ts"))
    assert ran == top_level
    # Allowlist: only direct children of src/, never a live-suite file.
    assert all(re.fullmatch(r"src/[^/]+\.test\.ts", f) and ".external." not in f for f in ran)
    for live_dir in ("external", "release", "weekly"):
        assert list((PROXY / "src" / live_dir).glob("*.ts")), f"{live_dir}/ is empty, so the exclusion proves nothing"


def test_proxy_file_command_runs_that_file_and_nothing_else():
    assert PROXY_FILE_CMD.split() == ["node", "--test", PROXY_FILE]
    assert _proxy_run(PROXY_FILE) == [PROXY_FILE]


# ---------------------------------------------------------------- Android


def _gradle(*args: str, timeout: int = 300) -> str:
    wrapper = ANDROID / ("gradlew.bat" if os.name == "nt" else "gradlew")
    has_sdk = (ANDROID / "local.properties").is_file() or os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if not wrapper.is_file() or not has_sdk:
        pytest.skip("no Gradle wrapper or Android SDK on this machine")
    return _run([str(wrapper), "--offline", *args], ANDROID, timeout)


def _gradle_tasks(*args: str) -> set[str]:
    return set(re.findall(r"^(:\S+) SKIPPED", _gradle(*args, "--dry-run"), flags=re.MULTILINE))


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
    assert re.search(rf"^package {re.escape(package)}$", _read(source), flags=re.MULTILINE)
    assert re.search(rf"\bclass {name}\b", _read(source))


# ---------------------------------------------------------------- Docs


@pytest.mark.parametrize("doc, commands", [
    (WEB / "TESTING.md", [WEB_FILE_CMD, WEB_CONTEXT_CMD]),
    (PROXY / "TESTING.md", [PROXY_FILE_CMD, PROXY_CONTEXT_CMD]),
    (ANDROID / "TESTING.md", [ANDROID_FILE_CMD, ANDROID_CONTEXT_CMD]),
])
def test_each_contexts_testing_doc_lists_its_commands(doc, commands):
    text = _read(doc)
    assert [c for c in commands if f"`{c}`" not in text] == []
