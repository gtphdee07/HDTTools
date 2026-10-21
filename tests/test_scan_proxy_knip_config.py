"""Scan Proxy's dead-code check keeps exiting clean (#152).

`npm run check:dead-code` (knip) reported `uv` as an unlisted binary because the `deploy` script is
`uv run ../../scripts/scan_proxy_deploy.py` and knip cannot know `uv` is a tool the repo expects on the
PATH. The fix lives in `workers/scan-proxy/knip.json`, not in `package.json`, which pins three External
surfaces (an edit marks all three stale). If the entry is dropped, or moved to a config knip does not read,
the command exits 1 again and nothing else notices until someone runs it.

Static, no Node: reads the files knip reads. The real `check:dead-code` run is recorded on the ticket.
"""

from __future__ import annotations

import json
import re

import pytest

from tests._test_command_helpers import PROXY, read

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
