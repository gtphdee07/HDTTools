"""#82: running the Scan Proxy's tests without `npm install` fails with the install
instruction, not a misleading 502 assertion.

A fresh git worktree has no `node_modules`; the proxy loads its Claude SDK lazily, so the
missing install used to surface as "expected 200, got 502" (a refunded `extraction_failed`).
The guard lives in the test entry points (`src/requireInstall.ts`, imported first by every
top-level `*.test.ts`), never in the shipped service. These checks run the real proxy tests
against a copy of the proxy that has no `node_modules`, so they need Node but no install.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tests._test_command_helpers import PROXY, PROXY_FILE, read, require_proxy_install, tool

pytestmark = [pytest.mark.core, pytest.mark.minor]

INSTALL_COMMAND = "npm --prefix workers/scan-proxy install"


@pytest.fixture(scope="module")
def uninstalled_proxy(tmp_path_factory) -> Path:
    """The proxy's tracked sources and package.json, without node_modules. Lives under the
    OS temp directory so Node's upward `node_modules` lookup cannot find the repo's own."""
    copy = tmp_path_factory.mktemp("proxy-no-install")
    shutil.copy(PROXY / "package.json", copy)
    shutil.copytree(PROXY / "src", copy / "src", ignore=shutil.ignore_patterns("external", "release", "weekly"))
    assert not (copy / "node_modules").exists()
    return copy


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=180)


def _assert_install_instruction(output: str) -> None:
    assert "npm install" in output
    assert INSTALL_COMMAND in output
    assert "@anthropic-ai/sdk" in output
    assert "502" not in output and "extraction_failed" not in output


def test_every_top_level_proxy_test_file_imports_the_guard_first():
    files = sorted((PROXY / "src").glob("*.test.ts"))
    assert files
    unguarded = [
        f.name
        for f in files
        if not (lines := [l for l in read(f).splitlines() if l.startswith("import ")])
        or lines[0] != 'import "./requireInstall.ts";'
    ]
    assert unguarded == []


def test_a_test_file_run_directly_without_the_install_names_the_fix(uninstalled_proxy):
    proc = _run([tool("node"), "--test", PROXY_FILE], uninstalled_proxy)
    assert proc.returncode != 0
    _assert_install_instruction(proc.stdout + proc.stderr)


def test_the_token_tests_without_the_install_name_the_fix_instead_of_a_502(uninstalled_proxy):
    proc = _run([tool("node"), "--test", "src/accountToken.test.ts"], uninstalled_proxy)
    assert proc.returncode != 0
    _assert_install_instruction(proc.stdout + proc.stderr)


def test_npm_test_without_the_install_names_the_fix_and_runs_no_test_body(uninstalled_proxy):
    proc = _run([tool("npm"), "test"], uninstalled_proxy)
    output = proc.stdout + proc.stderr
    assert proc.returncode != 0
    _assert_install_instruction(output)
    # Every file stopped at the guard; none got far enough to assert a status code.
    assert not re.search(r"expected 200|!== 200", output)
    assert re.search(r"pass 0$", output, flags=re.MULTILINE)


def test_the_wrapper_precondition_fails_with_the_install_instruction(uninstalled_proxy):
    with pytest.raises(pytest.fail.Exception) as failure:
        require_proxy_install(uninstalled_proxy)
    _assert_install_instruction(str(failure.value))


def test_the_wrapper_precondition_passes_when_the_proxy_is_installed():
    require_proxy_install(PROXY)
