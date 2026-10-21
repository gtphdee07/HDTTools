"""Scan Proxy's coverage gate passes without a test that signs in (#151).

`liveTokenCli.ts` ends with a guard that runs the sign-in helper only when the file is invoked directly as a
script (`android/test-weekly.ps1` does). Every test calls the functions; a test that ran the script would sign in
against the live Supabase project, so those two lines were the whole 99.84% against the gate's 100.00% floor.
The fix is a `node:coverage ignore next 3` comment on the guard, so the floor stays at 100% for everything else.

The two risks in that fix are that the comment stops matching the guard (someone adds a line above or inside it,
and the ignore then covers the wrong lines or too few), and that it grows past the guard and hides real code.
The first test asks Node's own coverage report, so it catches both for `liveTokenCli.ts`; the second reads the
file and pins the ignored range to exactly the guard's lines, so nothing else can be hidden under the same comment.
The third checks that the testing documents say how the gate passes.
"""

from __future__ import annotations

import re

import pytest

from tests._test_command_helpers import PROXY, ROOT, read, require_proxy_install, run, tool

pytestmark = [pytest.mark.core, pytest.mark.minor]

CLI = PROXY / "src" / "liveTokenCli.ts"
IGNORE = re.compile(r"/\*\s*node:coverage\s+ignore\s+next\s+(\d+)\s*\*/")


@pytest.mark.slow
@pytest.mark.xdist_group("node")
def test_the_sign_in_helper_is_at_100_percent_of_lines_under_nodes_own_coverage():
    require_proxy_install()
    out = run([tool("node"), "--test", "--experimental-test-coverage", "src/liveTokenCli.test.ts"], PROXY)
    row = re.search(r"^\D*liveTokenCli\.ts\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*(.*)$", out, re.M)
    assert row, f"no liveTokenCli.ts row in the coverage report:\n{out[-1500:]}"
    lines_pct, uncovered = float(row.group(1)), row.group(4).strip()
    assert lines_pct == 100.0, f"liveTokenCli.ts is at {lines_pct}% of lines, uncovered {uncovered or 'none listed'}"


def test_the_ignore_comment_covers_exactly_the_run_as_script_guard():
    lines = read(CLI).replace("\r\n", "\n").split("\n")
    marks = [(i, IGNORE.search(line)) for i, line in enumerate(lines) if IGNORE.search(line)]
    assert len(marks) == 1, f"expected one node:coverage ignore comment in liveTokenCli.ts, found {len(marks)}"
    index, mark = marks[0]
    ignored = lines[index + 1 : index + 1 + int(mark.group(1))]
    assert ignored, "the ignore comment covers no lines"
    assert ignored[0].startswith("if (process.argv[1] === fileURLToPath(import.meta.url)) {"), ignored
    assert ignored[-1] == "}", ignored
    assert sum(line.startswith("}") for line in ignored) == 1, "the ignored range spans more than the one guard block"
    assert not any(line.strip() for line in lines[index + 1 + len(ignored) :]), "code follows the guard, outside the ignore"
    assert "/* node:coverage" not in read(PROXY / "src" / "liveToken.ts"), "unrelated file excludes lines too"


def test_the_testing_documents_say_how_the_scan_proxy_gate_passes():
    proxy_doc = read(PROXY / "TESTING.md").replace("\r\n", "\n")
    root_doc = read(ROOT / "TESTING.md").replace("\r\n", "\n")
    gate = root_doc.split("## Coverage gate", 1)[1].split("\n## ", 1)[0]
    for name, text in (("workers/scan-proxy/TESTING.md", proxy_doc), ("TESTING.md Coverage gate", gate)):
        assert "node:coverage ignore" in text, f"{name} does not name the exclusion"
        assert "99.84" not in text or "before" in text, f"{name} still reports the gate as failing at 99.84%"
    assert "gate **fails**" not in proxy_doc and "FAIL, exit 1" not in gate
    still_open = [line for line in proxy_doc.split("## Known gaps", 1)[1].splitlines() if line.startswith("- **Open") and "#151" in line]
    assert not still_open, still_open
