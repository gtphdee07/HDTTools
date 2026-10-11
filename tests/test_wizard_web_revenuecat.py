"""Interaction tests for scripts/wizard_web_revenuecat.sh (#86).

The wizard asks for the RevenueCat Web Billing PUBLIC key. A secret `sk_` key
pasted by mistake must be refused without ever being echoed to the screen.

The script is run with scripted stdin in a scratch directory. A terminal echoes
what is typed, a pipe does not, so a plain output check cannot see a visible
prompt. A `read` wrapper (loaded through BASH_ENV) therefore logs, for every
line read, whether it was read silently (`read -s`); the secret must be read
silently. A fake `wslview` on PATH stands in for the browser the wizard opens.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.minor]

WIZARD = Path(__file__).resolve().parent.parent / "scripts" / "wizard_web_revenuecat.sh"

SECRET_KEY = "sk_live_NOT_A_REAL_KEY_123"
PUBLIC_KEY = "rcb_sb_publickey456"

# Every line the script reads is appended to $READ_LOG as "<silent|visible> <value>".
READ_WRAPPER = r"""
read() {
  local __flags="${1:-}" __var="${!#}" __silent=visible
  [[ "$__flags" == -*s* ]] && __silent=silent
  builtin read "$@"
  local __rc=$?
  printf '%s %s\n' "$__silent" "${!__var}" >> "$READ_LOG"
  return $__rc
}
"""


def _bash() -> str:
    # On Windows a bare `bash` can be WSL's; prefer the bash that ships with Git.
    git = shutil.which("git")
    if git:
        candidate = Path(git).resolve().parent.parent / "bin" / "bash.exe"
        if candidate.exists():
            return str(candidate)
    found = shutil.which("bash")
    if not found:
        pytest.skip("bash is not available")
    return found


def _run_wizard(tmp_path: Path, answers: list[str]):
    work = tmp_path / "work"
    (work / "web").mkdir(parents=True)
    (work / "workers" / "scan-proxy").mkdir(parents=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "wslview").write_text("#!/bin/sh\nexit 0\n", newline="\n")
    wrapper = tmp_path / "read_wrapper.sh"
    wrapper.write_text(READ_WRAPPER, newline="\n")
    read_log = tmp_path / "reads.log"
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "BASH_ENV": wrapper.as_posix(),
        "READ_LOG": read_log.as_posix(),
    }
    result = subprocess.run(
        [_bash(), WIZARD.as_posix()],
        cwd=work,
        env=env,
        input="".join(f"{a}\n" for a in answers),
        capture_output=True,
        text=True,
        timeout=60,
    )
    reads = read_log.read_text(encoding="utf-8").splitlines() if read_log.exists() else []
    return result, work / "web" / ".env.local", reads


# banner and stage-1 pauses, the key (a secret one first), the offering id, two
# blank optional ids, and "no" to the live-site stage.
ANSWERS = ["", "", SECRET_KEY, PUBLIC_KEY, "default", "", "", "n"]


def test_a_secret_looking_key_is_read_without_echo_and_never_printed(tmp_path):
    result, _env_file, reads = _run_wizard(tmp_path, ANSWERS)

    assert result.returncode == 0, result.stderr
    assert f"silent {SECRET_KEY}" in reads
    assert f"visible {SECRET_KEY}" not in reads
    assert SECRET_KEY not in result.stdout
    assert SECRET_KEY not in result.stderr


def test_a_secret_looking_key_is_refused_and_the_public_key_is_saved(tmp_path):
    result, env_file, _reads = _run_wizard(tmp_path, ANSWERS)

    assert "SECRET key" in result.stdout
    saved = env_file.read_text(encoding="utf-8")
    assert f"VITE_REVENUECAT_WEB_PUBLIC_API_KEY={PUBLIC_KEY}" in saved
    assert SECRET_KEY not in saved
    assert "VITE_REVENUECAT_WEB_OFFERING_ID=default" in saved
