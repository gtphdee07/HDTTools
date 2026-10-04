"""Shared constants and subprocess helpers for #52's command checks.

Not collected by pytest (its name matches neither `test_*.py` nor `*_test.py`).
Shared by `test_context_test_commands.py` and `test_android_file_command_slow.py`
so the slow test does not reach into a sibling test module's private names.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

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


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def npm_script(package_dir: Path, name: str) -> str:
    return json.loads(read(package_dir / "package.json"))["scripts"][name]


def tool(name: str) -> str:
    """A Node-toolchain executable's path, or skip: these checks need Node installed,
    which isn't guaranteed on every machine that can run the Python suite."""
    path = shutil.which(name)
    if path is None:
        pytest.skip(f"{name} (Node) is not installed")
    return path


def run(cmd: list[str], cwd: Path, timeout: int = 180) -> str:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    assert proc.returncode == 0, f"{' '.join(cmd)} exited {proc.returncode}:\n{proc.stdout[-800:]}\n{proc.stderr[-800:]}"
    return proc.stdout


def relative(file: str, base: Path) -> str:
    return Path(file).resolve().relative_to(base).as_posix()


def gradle(*args: str, timeout: int = 300) -> str:
    """Run the Android Gradle wrapper offline, or skip: these checks need the Android SDK,
    which isn't guaranteed on every machine that can run the Python suite. Run with `-rs`
    to see why a check was skipped rather than mistaking a skip for a pass."""
    wrapper = ANDROID / ("gradlew.bat" if os.name == "nt" else "gradlew")
    has_sdk = (ANDROID / "local.properties").is_file() or os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if not wrapper.is_file() or not has_sdk:
        pytest.skip("no Gradle wrapper or Android SDK on this machine")
    return run([str(wrapper), "--offline", *args], ANDROID, timeout)
