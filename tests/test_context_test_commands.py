"""Command checks for #52: each of Web, Scan Proxy and Android has one
documented file-level command and one context-level command, and neither
selects a live-provider test or needs a device.

Nothing here runs a test body. Web uses Vitest's own `list`, Scan Proxy
expands the glob its `test` script uses, and Android asks Gradle for a dry-run
task graph. The commands under test are the ones written in each context's
TESTING.md; the docs check below fails if they drift apart.
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


def _vitest_files(*args: str) -> list[str]:
    npx = shutil.which("npx")
    if npx is None:
        pytest.skip("npx (Node) is not installed")
    out = subprocess.run(
        [npx, "vitest", "list", "--filesOnly", *args],
        cwd=WEB, capture_output=True, text=True, timeout=120, check=True,
    ).stdout
    return sorted(line.strip().replace("\\", "/").removeprefix(f"{WEB.as_posix()}/")
                  for line in out.splitlines() if line.strip().endswith((".ts", ".tsx")))


def _gradle_dry_run(*args: str) -> list[str]:
    wrapper = ANDROID / ("gradlew.bat" if os.name == "nt" else "gradlew")
    out = subprocess.run(
        [str(wrapper), "--offline", *args, "--dry-run"],
        cwd=ANDROID, capture_output=True, text=True, timeout=300,
    )
    if out.returncode != 0:
        pytest.skip(f"Gradle could not configure offline: {out.stderr[-300:]}")
    return re.findall(r"^(:\S+) SKIPPED", out.stdout, flags=re.MULTILINE)


# ---------------------------------------------------------------- Web


def test_web_file_command_selects_only_that_file():
    assert _npm_script(WEB, "test") == "vitest run"
    assert _vitest_files(WEB_FILE) == [WEB_FILE]


def test_web_context_command_selects_every_offline_file_and_no_live_one():
    selected = _vitest_files()
    on_disk_live = sorted(p.relative_to(WEB).as_posix() for p in (WEB / "src").rglob("*.external.test.ts"))
    assert on_disk_live, "no live Web test on disk, so the exclusion below proves nothing"
    assert selected, "the context command selected nothing"
    assert not set(selected) & set(on_disk_live)
    assert WEB_FILE in selected


# ---------------------------------------------------------------- Scan Proxy


def _proxy_context_files() -> list[str]:
    script = _npm_script(PROXY, "test")
    assert script.startswith("node --test "), script
    patterns = script.removeprefix("node --test ").split()
    return sorted(p.relative_to(PROXY).as_posix() for pat in patterns for p in PROXY.glob(pat))


def test_proxy_has_no_hook_that_deploys_or_goes_live_before_the_test_script():
    scripts = json.loads(_read(PROXY / "package.json"))["scripts"]
    assert "pretest" not in scripts and "posttest" not in scripts


def test_proxy_context_command_selects_top_level_tests_and_no_live_one():
    selected = _proxy_context_files()
    assert PROXY_FILE in selected
    live_dirs = ("src/external/", "src/release/", "src/weekly/")
    assert not [f for f in selected if f.startswith(live_dirs) or ".external." in f]
    # Every live suite exists on disk, so the exclusion is real.
    for live_dir in live_dirs:
        assert list((PROXY / live_dir).glob("*.test.ts")), live_dir


def test_proxy_file_command_names_an_existing_offline_test_file():
    path = PROXY_FILE_CMD.removeprefix("node --test ")
    assert (PROXY / path).is_file()
    assert path in _proxy_context_files()


# ---------------------------------------------------------------- Android


def test_android_context_command_runs_only_jvm_tasks_and_no_device_task():
    tasks = _gradle_dry_run("testDebugUnitTest")
    assert ":app:testDebugUnitTest" in tasks
    device = [t for t in tasks if re.search(r"androidtest|connected|emulator|adb", t, re.I)]
    assert device == []


def test_android_file_command_names_a_class_in_the_jvm_source_set():
    fqcn = ANDROID_FILE_CMD.rsplit(" ", 1)[1]
    jvm = ANDROID / "app/src/test/java" / (fqcn.replace(".", "/") + ".kt")
    assert jvm.is_file()


# ---------------------------------------------------------------- Docs


@pytest.mark.parametrize("doc, commands", [
    (WEB / "TESTING.md", [WEB_FILE_CMD, WEB_CONTEXT_CMD]),
    (PROXY / "TESTING.md", [PROXY_FILE_CMD, PROXY_CONTEXT_CMD]),
    (ANDROID / "TESTING.md", [ANDROID_FILE_CMD, ANDROID_CONTEXT_CMD]),
])
def test_each_contexts_testing_doc_lists_its_commands(doc, commands):
    text = _read(doc)
    assert [c for c in commands if f"`{c}`" not in text] == []
