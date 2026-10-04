"""Advisory test planner (#60, spec #51): which Python tests to run for a change.

Reads the changed files, the Python context config
(scripts/test_planner_config.json) and the pytest markers declared in
pyproject.toml, then prints the per-issue plan (rule 2 of
docs/test-audit/rules.md):

  1. any changed test file, first (the issue's own targeted test);
  2. the Minor suite of each touched context;
  3. the Major suite instead (it includes Minor) when a public interface
     of that context changed, or a dependency file changed (a dependency
     change covers every context);
  4. the interface tests of each changed interface.

Usage: uv run scripts/test_planner.py [--files PATH ...] [--base REF]
Without --files the changed files come from `git diff --name-only <base>`
(default HEAD). The planner is advisory: it always exits 0.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tomllib
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = Path(__file__).resolve().parent / "test_planner_config.json"
PYPROJECT = REPO_ROOT / "pyproject.toml"


class GitError(Exception):
    pass


@dataclass
class Selection:
    kind: str  # "targeted" | "minor" | "major" | "interface"
    command: str
    reason: str


@dataclass
class Plan:
    selections: list[Selection] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def load_config(path: Path = CONFIG_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_markers(pyproject: Path = PYPROJECT) -> set[str]:
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    declared = data["tool"]["pytest"]["ini_options"].get("markers", [])
    return {entry.split(":", 1)[0].strip() for entry in declared}


def _normalise(path: str) -> str:
    return path.replace("\\", "/").removeprefix("./")


def _matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch(path, p) for p in patterns)


def plan(changed_files: list[str], config: dict, markers: set[str]) -> Plan:
    files = [_normalise(f) for f in changed_files]
    contexts = config["contexts"]
    result = Plan()

    touched: set[str] = set()
    interface_changed: set[str] = set()  # contexts whose public interface changed
    interfaces: list[dict] = []
    for f in files:
        owners = {n for n, c in contexts.items() if any(f.startswith(p) for p in c["paths"])}
        hit = [i for i in config["interfaces"] if _matches(f, i["files"])]
        for iface in hit:
            if iface not in interfaces:
                interfaces.append(iface)
            if not owners and iface["context"] in contexts:
                owners.add(iface["context"])
        touched |= owners
        if hit:
            interface_changed |= owners

    dependency_changed = any(f in config["dependency_files"] for f in files)
    if dependency_changed:
        touched |= set(contexts)

    for f in files:
        if f.startswith("tests/") and f.endswith(".py"):
            result.selections.append(Selection("targeted", f"uv run pytest {f}", "changed test file, runs first"))

    for name, ctx in contexts.items():  # config order keeps the output stable
        if name not in touched:
            continue
        marker = ctx["marker"]
        major = dependency_changed or name in interface_changed
        missing = ({marker} if major else {marker, "minor"}) - markers
        if missing:
            result.notes.append(f"{name}: marker(s) {sorted(missing)} not declared in pyproject.toml; skipped")
            continue
        if major:
            why = "dependency changed" if dependency_changed else "public interface changed"
            result.selections.append(Selection("major", f"uv run pytest -m {marker}", f"{name} Major ({why}; includes Minor)"))
        else:
            result.selections.append(Selection("minor", f'uv run pytest -m "minor and {marker}"', f"{name} Minor"))

    for iface in interfaces:
        for test in iface["tests"]:
            result.selections.append(Selection("interface", f"uv run pytest {test}", f"interface {iface['name']}"))
        outside = [c for c in iface.get("shares_with", []) if c not in contexts]
        if outside:
            result.notes.append(
                f"interface {iface['name']} is shared with {', '.join(outside)}; those contexts' tests are not planned here"
            )

    if not files:
        result.notes.append("no changed files; nothing planned")
    elif not result.selections and not result.notes:
        result.notes.append("no Python context touched; no Python tests planned")
    return result


def changed_files_from_git(base: str) -> list[str]:
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", base], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GitError(str(exc)) from exc
    return [line for line in out.splitlines() if line.strip()]


def main(argv: list[str] | None = None, *, git=changed_files_from_git) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--files", nargs="*", help="changed files (default: git diff --name-only)")
    parser.add_argument("--base", default="HEAD", help="git ref to diff against (default HEAD)")
    args = parser.parse_args(argv)

    try:
        files = args.files if args.files is not None else git(args.base)
        result = plan(files, load_config(), load_markers())
    except Exception as exc:  # advisory: never block
        print(f"Planner could not plan ({exc}); no tests planned. git or config problems never block.")
        return 0

    print("Per-issue test plan (advisory)")
    for i, sel in enumerate(result.selections, 1):
        print(f"  {i}. {sel.command}    # {sel.reason}")
    for note in result.notes:
        print(f"  note: {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
