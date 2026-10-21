"""Scan Proxy's dead-code check keeps exiting clean (#152).

`npm run check:dead-code` (knip) reported `uv` as an unlisted binary because the `deploy` script is
`uv run ../../scripts/scan_proxy_deploy.py` and knip cannot know `uv` is a tool the repo expects on the
PATH. The fix lives in `workers/scan-proxy/knip.json`, not in `package.json`, which pins three External
surfaces (an edit marks all three stale). If the entry is dropped, or moved to a config knip does not read,
the command exits 1 again and nothing else notices until someone runs it.

The first three tests are static and read the files knip reads. Three more back the ticket's other claims with
something that keeps running: the real `check:dead-code` command exits 0 (the one test that starts Node, so it is
`slow`), `knip.json` is not a boundary file or dependency pin of any External surface (so adding or editing it
can never mark a surface stale, which is why the fix is not in `package.json`), and the Scan Proxy testing
document says the command exits clean.
"""

from __future__ import annotations

import json
import re
import subprocess

import pytest

from tests._test_command_helpers import ROOT, PROXY, read, require_proxy_install, run, tool

pytestmark = [pytest.mark.core, pytest.mark.minor]

# knip's own search order: [.]knip.json[c], knip.(js|ts), knip.config.(js|ts) or package.json#knip.
KNIP_CONFIG_NAMES = ["knip.json", "knip.jsonc", ".knip.json", ".knip.jsonc", "knip.js", "knip.ts", "knip.config.js", "knip.config.ts"]

# `uv` as a command word: at the start of a script or after a shell separator, not `uvicorn` or `./uv`.
UV_COMMAND = re.compile(r"(?:^|[;&|(]\s*|&&\s*)uv(?:\s|$)")


def _scripts_using_uv() -> list[str]:
    scripts = json.loads(read(PROXY / "package.json"))["scripts"]
    return sorted(name for name, command in scripts.items() if UV_COMMAND.search(command))


def test_knip_config_lists_uv_while_a_script_still_uses_it():
    using = _scripts_using_uv()
    if not using:
        pytest.skip("no Scan Proxy script runs uv any more, so knip needs no ignoreBinaries entry for it")
    config = json.loads(read(PROXY / "knip.json"))
    assert "uv" in config.get("ignoreBinaries", []), (
        f"package.json scripts {using} run `uv`; without it in knip.json's ignoreBinaries, "
        "`npm run check:dead-code` exits 1 on an unlisted binary"
    )


def test_knip_reads_only_knip_json_so_the_entry_is_the_one_in_force():
    present = [name for name in KNIP_CONFIG_NAMES if (PROXY / name).exists()]
    assert present == ["knip.json"]
    assert "knip" not in json.loads(read(PROXY / "package.json")), "a knip key in package.json edits the dependency pin"


@pytest.mark.parametrize("command, uses_uv", [
    ("uv run ../../scripts/scan_proxy_deploy.py", True),
    ("npm run typecheck && uv run deploy.py", True),
    ("uvicorn app:app", False),
    ("node ./uv.js", False),
])
def test_uv_detector_matches_a_command_word_only(command, uses_uv):
    assert bool(UV_COMMAND.search(command)) is uses_uv


@pytest.mark.slow
@pytest.mark.xdist_group("node")
def test_the_real_dead_code_check_exits_clean():
    require_proxy_install()
    out = run([tool("npm"), "run", "check:dead-code", "--silent"], PROXY)
    assert "Unlisted" not in out and "Unused" not in out, out


SURFACES = ROOT / "scripts" / "external_manifest" / "surfaces"
KNIP_CONFIG = "workers/scan-proxy/knip.json"
PROXY_PINS = ("workers/scan-proxy/package.json", "workers/scan-proxy/package-lock.json")


def _surfaces() -> list[dict]:
    return [json.loads(read(path)) for path in sorted(SURFACES.glob("*.json"))]


def test_the_knip_config_is_tracked_and_is_no_external_surfaces_pin_or_boundary_file():
    # `external_freshness.py` marks a surface stale when a file matching its boundary_files or
    # dependency_pins pathspecs changed since its last pass; ask git which tracked files those match.
    def tracked(*pathspecs: str) -> set[str]:
        proc = subprocess.run(["git", "ls-files", "--", *pathspecs], cwd=ROOT, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        return set(proc.stdout.split())

    assert KNIP_CONFIG in tracked(KNIP_CONFIG), f"{KNIP_CONFIG} is not tracked by git"
    marking_stale = [
        surface["name"]
        for surface in _surfaces()
        if surface.get("status") != "planned"
        and KNIP_CONFIG in tracked(*surface.get("boundary_files", []), *surface.get("dependency_pins", []))
    ]
    assert not marking_stale, f"editing {KNIP_CONFIG} would mark these External surfaces stale: {marking_stale}"


def test_package_json_is_the_dependency_pin_the_fix_stays_out_of():
    # The testing document and the ticket say editing package.json marks these surfaces stale; keep that true.
    pinned = {s["name"] for s in _surfaces() if PROXY_PINS[0] in s.get("dependency_pins", [])}
    assert {"anthropic", "scan-proxy-worker", "worker-token-verification"} <= pinned, sorted(pinned)


def _dead_code_section(text: str) -> str:
    start = text.index("\n## Dead code")
    end = text.find("\n## ", start + 1)
    return text[start:end if end != -1 else None]


def test_the_scan_proxy_testing_document_says_dead_code_exits_clean():
    text = read(PROXY / "TESTING.md").replace("\r\n", "\n")
    assert "exits clean" in _dead_code_section(text)
    # wording from before #152, when the command failed and the document said so
    for stale in ("does not exit clean", "reports one finding"):
        assert stale not in text, f"TESTING.md still says {stale!r}"
    still_open = [line for line in text.split("## Known gaps", 1)[1].splitlines() if line.startswith("- **Open") and "check:dead-code" in line]
    assert not still_open, still_open
