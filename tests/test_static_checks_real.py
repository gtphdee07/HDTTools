"""The static checks' allow-lists against the real tree (#150).

An allow-list that excuses a finding the code no longer has is worse than none: it reads as if something were
still being tolerated, and it would quietly excuse the finding if it came back. Each test here runs the real
tool over the real files and fails when a list names something the tool does not report any more.

- Vulture: a name in `vulture_whitelist.py` (production code and scripts) or `vulture_whitelist_tests.py`
  (tests) must still be reported when vulture runs without the whitelist. Fast.
- oxlint: `scripts/static_allowlists/oxlint.json` must match what oxlint reports for Web and for Scan Proxy,
  exactly. These start Node, so they are `slow` (the planner owes them when `scripts/*` changes).
- ruff: the pinned ruff, with the repo's `ruff.toml`, fails on an unused import and passes on a clean file, so
  an emptied rule list or a changed pin that stops catching defects is noticed. Starts `uv tool run`, so `slow`.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys

import pytest

from tests._test_command_helpers import ROOT, WEB, require_proxy_install, tool

pytestmark = [pytest.mark.core, pytest.mark.minor]

_SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(_SCRIPTS))
_spec = importlib.util.spec_from_file_location("static_checks", _SCRIPTS / "static_checks.py")
sc = importlib.util.module_from_spec(_spec)
sys.modules["static_checks"] = sc
_spec.loader.exec_module(sc)

REPORTED = re.compile(r"unused [a-z ]+ '([^']+)'")


def whitelist_names(filename: str) -> set[str]:
    """The bare names of a whitelist file: one identifier alone on a line, comments and blanks aside."""
    text = (ROOT / filename).read_text(encoding="utf-8")
    return set(re.findall(r"^([A-Za-z_]\w*)\s*$", text, re.M))


def reported_without_whitelist(*paths: str) -> set[str]:
    proc = subprocess.run([sys.executable, "-m", "vulture", *paths], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode in (0, 3), f"vulture could not run: {proc.stderr[-500:]}"
    return set(REPORTED.findall(proc.stdout))


@pytest.mark.parametrize("whitelist, scanned", [
    ("vulture_whitelist.py", ["src/hdttools", "streamlit_app", "scripts"]),
    ("vulture_whitelist_tests.py", ["tests"]),
])
def test_every_vulture_whitelist_name_is_still_reported_without_the_whitelist(whitelist, scanned):
    stale = sorted(whitelist_names(whitelist) - reported_without_whitelist(*scanned))
    assert not stale, f"{whitelist} excuses names vulture no longer reports, so remove them: {stale}"


def test_the_vulture_whitelists_are_not_empty_so_the_staleness_check_reads_something():
    assert len(whitelist_names("vulture_whitelist.py")) > 10 and len(whitelist_names("vulture_whitelist_tests.py")) > 5


def test_whitelisted_names_of_production_code_are_not_hiding_in_the_tests_whitelist_too():
    # `company` is the one name both need: a field of the shared models and of a stand-in record in the tests.
    assert not whitelist_names("vulture_whitelist.py") & whitelist_names("vulture_whitelist_tests.py") - {"company"}


@pytest.mark.slow
@pytest.mark.xdist_group("node")
@pytest.mark.parametrize("context", ["web", "scan-proxy"])
def test_the_oxlint_allow_list_matches_what_oxlint_reports_for_the_context_exactly(context):
    tool("node")
    if context == "scan-proxy":
        require_proxy_install()
    if not (WEB / "node_modules" / ".bin").is_dir():
        pytest.skip("web/node_modules is not installed (oxlint comes from there)")
    step = next(s for s in sc.steps_for(context) if s.lint_context)

    messages: list[str] = []
    code = sc.run_lint_step(step, capture=sc.run_capture, out=messages.append)

    assert code == 0, "\n".join(messages)


@pytest.mark.slow
def test_the_pinned_ruff_with_the_repos_config_fails_on_an_unused_import_and_passes_a_clean_file(tmp_path):
    def ruff(source: str) -> subprocess.CompletedProcess:
        probe = tmp_path / "probe.py"
        probe.write_text(source, encoding="utf-8")
        return subprocess.run(
            [*sc.RUFF, "check", "--no-cache", "--config", str(ROOT / "ruff.toml"), str(probe)],
            capture_output=True, text=True, timeout=180,
        )

    clean = ruff("print(1)\n")
    assert clean.returncode == 0, clean.stdout + clean.stderr
    defect = ruff("import os\n")
    assert defect.returncode == 1 and "F401" in defect.stdout, defect.stdout + defect.stderr
