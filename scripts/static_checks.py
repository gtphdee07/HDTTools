"""One command per context for its static checks (#150, spec #51): the typecheck, lint, dead-code and
coverage-floor checks that used to exist but ran only when someone remembered them.

  uv run scripts/static_checks.py core [--coverage]
  uv run scripts/static_checks.py streamlit [--coverage]
  uv run scripts/static_checks.py web
  uv run scripts/static_checks.py scan-proxy

Each is the context's `session_end` in scripts/test_planner_config.json, so the planner lists it when the
context's files change, /ticket-finish runs it and records the pass against the tree hash, and
`ticket_merge.py verdicts` shows skip or rerun for it. (Android's `session_end` is
scripts/android_session_end.py, which also runs the JVM tests; the four contexts here run their normal suites
through the planner's usual session plan and add these checks.) Every step runs offline: no paid call and no
device. All steps of a context run even when one fails, so one run shows everything that is wrong; the exit
code is the first failing step's.

`--coverage` adds the Python coverage floor (the whole suite under coverage.py, about a minute); the planner
adds it when a file of `src/hdttools/`, `streamlit_app/` or `scripts/` changed (Decision 4 of #150).

Lint warnings: an error always fails. A warning fails unless scripts/static_allowlists/oxlint.json lists it for
the context (file, rule, count, reason); an entry for a warning that no longer occurs also fails, so the
list cannot go stale. See docs/agents/static-checks.md for what each context's checks cover.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_steps import default_run_command  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST = REPO_ROOT / "scripts" / "static_allowlists" / "oxlint.json"
WEB_DIR = REPO_ROOT / "web"
PROXY_DIR = REPO_ROOT / "workers" / "scan-proxy"

# Pinned here, not in pyproject.toml: pyproject.toml and uv.lock are boundary files of the anthropic-python
# External surface, so adding a dev dependency would mark that paid surface stale. Rules live in ruff.toml.
RUFF = ["uv", "tool", "run", "ruff@0.17.1"]
PYTHON_TARGETS = ["src/hdttools", "streamlit_app", "scripts", "tests"]
# Vulture needs every caller to judge a definition dead, so every Python context scans the same code. tests/
# is a pass of its own: scanned together with src/, a function only its own test calls would count as used.
VULTURE = [sys.executable, "-m", "vulture", "src/hdttools", "streamlit_app", "scripts", "vulture_whitelist.py"]
VULTURE_TESTS = [sys.executable, "-m", "vulture", "tests", "vulture_whitelist_tests.py"]
# oxlint is installed once, in web/. Scan Proxy runs that binary rather than adding a dev dependency of its
# own, because an edit to workers/scan-proxy/package.json marks the External surfaces it pins stale.
OXLINT = str(WEB_DIR / "node_modules" / ".bin" / "oxlint")


@dataclass(frozen=True)
class Step:
    name: str
    command: list[str]
    cwd: Path = REPO_ROOT
    lint_context: str | None = None  # an oxlint step whose warnings are judged against the allow-list


def _coverage_step(only: str) -> Step:
    return Step("coverage floor", [sys.executable, str(REPO_ROOT / "scripts" / "coverage_gate.py"), "--only", only, "--refresh"])


def steps_for(context: str, *, coverage: bool = False) -> list[Step]:
    """The ordered steps of a context. Raises KeyError for a context with no static-check command."""
    if context in ("core", "streamlit"):
        targets = PYTHON_TARGETS if context == "core" else ["streamlit_app"]
        steps = [
            Step("ruff", [*RUFF, "check", *targets]),
            Step("vulture (dead code)", VULTURE),
            Step("vulture (dead code in tests)", VULTURE_TESTS),
        ]
        if coverage:
            steps.append(_coverage_step("python"))
        return steps
    if context == "web":
        return [
            Step("typecheck (tsc -b)", ["npx", "--no-install", "tsc", "-b"], cwd=WEB_DIR),
            Step("oxlint", [OXLINT, "-f", "json", "."], cwd=WEB_DIR, lint_context="web"),
            Step("knip (dead code)", ["npm", "--prefix", "web", "run", "check:dead-code"]),
        ]
    if context == "scan-proxy":
        return [
            Step("typecheck (tsc --noEmit)", ["npm", "--prefix", "workers/scan-proxy", "run", "typecheck"]),
            Step("oxlint", [OXLINT, "-f", "json", "."], cwd=PROXY_DIR, lint_context="scan-proxy"),
            Step("knip (dead code)", ["npm", "--prefix", "workers/scan-proxy", "run", "check:dead-code"]),
            _coverage_step("scan-proxy"),
        ]
    raise KeyError(context)


CONTEXTS = ("core", "streamlit", "web", "scan-proxy")


# --- oxlint warnings against the checked-in allow-list ---


def load_allowlist(context: str, path: Path = ALLOWLIST) -> list[dict]:
    entries = json.loads(path.read_text(encoding="utf-8"))["entries"]
    return [e for e in entries if e["context"] == context]


def parse_oxlint(output: str) -> list[dict]:
    """Each diagnostic as {file, rule, severity, line}; the file is as oxlint prints it, relative to its cwd."""
    found = []
    for d in json.loads(output)["diagnostics"]:
        labels = d.get("labels") or [{}]
        span = labels[0].get("span", {})
        found.append({
            "file": d["filename"].replace("\\", "/"),
            "rule": d.get("code", ""),
            "severity": d.get("severity", "warning"),
            "line": span.get("line", 0),
        })
    return found


def judge_lint(findings: list[dict], allowlist: list[dict]) -> list[str]:
    """Problems after the allow-list: an error, a warning beyond what the list allows, or a list entry that
    allows more warnings than occur. Empty means the lint step passes."""
    problems = []
    counts: dict[tuple[str, str], int] = {}
    for f in findings:
        if f["severity"] == "error":
            problems.append(f"error {f['file']}:{f['line']} {f['rule']}")
        else:
            key = (f["file"], f["rule"])
            counts[key] = counts.get(key, 0) + 1
    allowed = {(e["file"], e["rule"]): e["count"] for e in allowlist}
    for (file, rule), seen in sorted(counts.items()):
        if seen > allowed.get((file, rule), 0):
            problems.append(f"new warning {file} {rule}: {seen} found, {allowed.get((file, rule), 0)} allowed")
    for (file, rule), count in sorted(allowed.items()):
        if counts.get((file, rule), 0) < count:
            problems.append(f"stale allow-list entry {file} {rule}: lists {count}, {counts.get((file, rule), 0)} found")
    return problems


def run_capture(command: list[str], cwd: Path) -> subprocess.CompletedProcess:
    exe = shutil.which(command[0]) or command[0]
    return subprocess.run([exe, *command[1:]], cwd=cwd, capture_output=True, text=True)


def run_lint_step(step: Step, *, capture, out: Callable[[str], None], oxlint_installed=None) -> int:
    if oxlint_installed is None:
        oxlint_installed = shutil.which(OXLINT) is not None
    if not oxlint_installed:
        out(f"  oxlint is not installed ({OXLINT}); it comes from Web's install: run `npm --prefix web ci`")
        return 1
    proc = capture(step.command, cwd=step.cwd)
    try:
        findings = parse_oxlint(proc.stdout)
    except (ValueError, KeyError):
        out(proc.stdout + proc.stderr)
        out(f"oxlint did not produce JSON diagnostics (exit {proc.returncode})")
        return proc.returncode or 1
    allowlist = load_allowlist(step.lint_context)
    problems = judge_lint(findings, allowlist)
    allowed = sum(e["count"] for e in allowlist)
    for problem in problems:
        out(f"  {problem}")
    out(f"  {len(findings)} finding(s), {allowed} allowed by scripts/static_allowlists/oxlint.json, {len(problems)} problem(s)")
    return 1 if problems else 0


def _print(text: str) -> None:
    print(text, flush=True)  # flushed: the steps' own output goes straight to the terminal between these lines


def run(
    argv: list[str] | None = None,
    *,
    run_command=default_run_command,
    capture=run_capture,
    out: Callable[[str], None] = _print,
    oxlint_installed=None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("context", choices=CONTEXTS)
    parser.add_argument("--coverage", action="store_true", help="also run the Python coverage floor (core and streamlit)")
    args = parser.parse_args(argv)
    if args.coverage and args.context not in ("core", "streamlit"):
        parser.error("--coverage applies to core and streamlit; web has no floor and scan-proxy always runs its own")

    steps = steps_for(args.context, coverage=args.coverage)
    failed: list[tuple[str, int]] = []
    for number, step in enumerate(steps, 1):
        out(f"Static checks ({args.context}), step {number} of {len(steps)}: {step.name}")
        if step.lint_context:
            code = run_lint_step(step, capture=capture, out=out, oxlint_installed=oxlint_installed)
        else:
            code = run_command(step.command, cwd=step.cwd).returncode
        if code != 0:
            failed.append((step.name, code))
            out(f"Static checks ({args.context}): {step.name} FAILED (exit {code})")
    if failed:
        out(f"Static checks ({args.context}) FAILED: {', '.join(name for name, _ in failed)}")
        return failed[0][1]
    out(f"Static checks ({args.context}) passed: {', '.join(s.name for s in steps)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
